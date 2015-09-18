import time
import threading
import traceback

from synapse.compat import queue

import synapse.async as s_async
import synapse.threads as s_threads

from synapse.common import *
from synapse.eventbus import EventBus

class NoSuchJob(Exception):pass
class NoSuchGetBy(Exception):pass

class Cortex(EventBus):
    '''
    Top level Cortex key/valu storage object.

    ( use getCortex() to instantiate )

    Link Options:

        ropool=<num>    # how many async read threads?

    '''
    def __init__(self, link):
        EventBus.__init__(self)
        self.link = link

        size = int( link[1].get('threads', 3) )

        self.lock = threading.Lock()

        self.sizebymeths = {}
        self.rowsbymeths = {}

        # used to facilitate pooled async readers
        self.boss = s_async.AsyncBoss(size)
        self.bgboss = s_async.AsyncBoss(1)      # for sync bg calls

        self.jobcache = {}

        self._initCortex()

        self.isok = True
        self.onfini( self.boss.fini )
        self.onfini( self.bgboss.fini )

    def isOk(self):
        '''
        An API allowing MetaCortex to test for internal error states.
        '''
        return self.isok

    def addRows(self, rows):
        '''
        Add (ident,prop,valu,time) rows to the Cortex.

        Example:

            import time
            now = int(time.time())

            rows = [
                (id1,'baz',30,now),
                (id1,'foo','bar',now),
            ]

            core.addRows(rows)

        '''
        self._addRows(rows)

    def fireBgCall(self, api, *args, **kwargs):
        '''
        Call a cortex API in the "background" with no result.

        All requested calls will be run *sequentually* by a single
        pool thread, allowing "delete and check back" behavior.

        Example:

            jid = core.fireBgCall('delRowsByProp', 'foo', valu=10)

        Notes:

            The single-worker nature of this API allows stacking
            up a bunch of "delete by id" and subsequent add-rows
            APIs.

        '''
        meth = getattr(self,api)
        task = (meth,args,kwargs)

        jid = s_async.jobid()
        self.bgboss.initAsyncJob(jid, task=task)
        return jid

    def waitBgCall(self, jid, timeout=None):
        '''
        Wait for completion of a previous call to fireBgCall().

        Example:

            jid = core.fireBgCall('delRowsById', ident)
            # .. do other stuff ..

            core.waitBgJob(jid)
            # delRowsById is complete...

        '''
        return self.bgboss.waitAsyncJob(jid, timeout=timeout)

    def fireAsyncCall(self, api, *args, **kwargs):
        '''
        Call a cortex API asynchronously to return for results later.

        Example:

            jid = core.fireAsyncCall('getRowsByProp','foo',valu=10)
            # do stuff....
            job = core.waitAsyncCall(jid)

            ret = s_async.jobret(job)

        Notes:

            * callers are required to retrieve results using
              getAsyncResult(), this API is *not* fire and
              forget.

        '''

        jid = s_async.jobid()

        meth = getattr(self,api)
        task = (meth,args,kwargs)

        job = self.boss.initAsyncJob(jid, task=task)
        self.jobcache[jid] = job

        return jid

    def waitAsyncCall(self, jid):
        '''
        Wait for a previous call to fireAsyncCall to complete.

        Example:

            job = core.waitAsyncJob(jid)

        '''
        job = self.jobcache.pop(jid,None)
        self.boss.waitAsyncJob(jid)
        return job

    def getRowsById(self, ident):
        '''
        Return all the rows for a given ident.

        Example:

            for row in core.getRowsById(ident):
                stuff()

        '''
        return self._getRowsById(ident)

    def getRowsByIds(self, idents):
        '''
        Return all the rows for a given list of idents.

        Example:

            rows = core.getRowsByIds( (id1, id2, id3) )

        '''
        return self._getRowsByIds(idents)

    def delRowsById(self, ident):
        '''
        Delete all the rows for a given ident.

        Example:

            core.delRowsById(ident)

        '''
        self._delRowsById(ident)

    def getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Return a tuple of (ident,prop,valu,time) rows by prop[=valu].

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)

        Notes:

            * Specify limit=<count> to limit return size
            * Specify mintime=<time> in epoch to filter rows
            * Specify maxtime=<time> in epoch to filter rows

        '''
        return tuple(self._getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        '''
        Similar to getRowsByProp but also lifts all other rows for ident.

        Example:

            for row in core.getRowsByProp('foo',valu=20):
                stuff(row)
        Notes:

            * See getRowsByProp for options

        '''
        return tuple(self._getJoinByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit))

    def getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Return the count of matching rows by prop[=valu]

        Example:

            if core.getSizeByProp('foo',valu=10) > 30:
                stuff()

        '''
        return self._getSizeByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def getRowsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve rows by a specialized index within the cortex.

        Example:

            rows = core.getRowsBy('range','foo',(20,30))

        Notes:
            * most commonly used to facilitate range searches

        '''
        meth = self._reqRowsByMeth(name)
        return meth(prop,valu,limit=limit)

    def getSizeBy(self, name, prop, valu, limit=None):
        '''
        Retrieve row count by a specialized index within the cortex.

        Example:

            size = core.getSizeBy('range','foo',(20,30))
            print('there are %d rows where 20 <= foo < 30 ' % (size,))

        '''
        meth = self._reqSizeByMeth(name)
        return meth(prop,valu,limit=limit)

    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Cortex.

        Example:

            def getbywoot(prop,valu,limit=None):
                return stuff() # list of rows

            core.initRowsBy('woot',getbywoot)

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        '''
        Initialize a "size by" handler for the Cortex.

        Example:

            def sizebywoot(prop,valu,limit=None):
                return stuff() # size of rows

            core.initSizeBy('woot',meth)

        '''
        self.sizebymeths[name] = meth

    def getTufoByProp(self, prop, valu=None):
        '''
        Return an (ident,info) tuple by joining rows based on a property.

        Example:

            tufo = core.getTufoByProp('fqdn','woot.com')

        Notes:

            * This must be used only for rows added with addTufoByProp!

        '''
        rows = self.getJoinByProp(prop, valu=valu, limit=1)
        if not rows:
            return None

        tufo = ( rows[0][0], {} )
        for ident,prop,valu,stamp in rows:
            tufo[1][prop] = valu

        return tufo

    def formTufoByProp(self, prop, valu):
        '''
        Form an (ident,info) tuple by atomically deconflicting
        the existance of prop=valu and creating it if not present.

        Example:

            tufo = core.formTufoByProp('fqdn','woot.com')

        Notes:

            * this will trigger an 'cortex:tufo:add' event if the
              tufo does not yet exist and is being construted.

        '''
        with self.lock:
            tufo = self.getTufoByProp(prop,valu=valu)
            if tufo != None:
                return tufo

            ident = guidstr()
            stamp = int(time.time())

            self.addRows( [(ident,prop,valu,stamp)] )

            tufo = (ident,{prop:valu})
            self.fire('cortex:tufo:add', tufo=tufo, prop=prop, valu=valu, stamp=stamp)
            self.fire('cortex:tufo:add:%s' % prop, tufo=tufo, prop=prop, valu=valu, stamp=stamp)
            return tufo

    def addTufoProps(self, tufo, **props):
        '''
        Add ( without checking for existance ) a set of tufo props.

        Example:

            core.addTufoProps(tufo, woot='hehe', blah=10)

        Notes:

            * Mostly for use with cortex:tufo:add:<prop> callbacks.

        '''
        ident = tufo[0]
        stamp = int(time.time())

        rows = []
        for prop,valu in props.items():
            tufo[1][prop] = valu
            rows.append( (ident,prop,valu,stamp) )

        self.addRows(rows)
        return tufo

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)

        '''
        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete a group of rows by selecting for property and joining on ident.

        Example:

            core.delJoinByProp('foo',valu=10)

        '''
        return self._delJoinByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsById(irow[0]):
                yield jrow

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)
        done = set()
        for row in rows:
            ident = row[0]
            if ident in done:
                continue

            self.delRowsById(ident)
            done.add(ident)

    def _reqSizeByMeth(self, name):
        meth = self.sizebymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth

    def _reqRowsByMeth(self, name):
        meth = self.rowsbymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth
