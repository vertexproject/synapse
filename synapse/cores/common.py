import queue
import threading
import traceback

import synapse.async as s_async

from synapse.eventbus import EventBus

class NoSuchJob(Exception):pass
class NoSuchGetBy(Exception):pass
class DupCortexName(Exception):pass

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

        ropool = int( link[1].get('ropool', 3) )

        self.lock = threading.Lock()

        self.sizebymeths = {}
        self.rowsbymeths = {}

        self.jobboss = s_async.AsyncBoss(pool=ropool)
        self.jobcache = {}

        self._initCortex()

        self.boss = s_async.AsyncBoss(pool=1)
        self.async = s_async.AsyncApi(self.boss, self)

        self.onfini( self.boss.fini )

    def getAsyncReturn(self, jid, timeout=None):
        '''
        Retrieve return value for a previous async read request.

        Example:

            jid = core.getRowsByProp('foo',10,async=True)

            # do other stuff...

            rows = core.getAsyncReturn(jid)

        Notes:

            * For use with all async gets (rows/joins/etc)

        '''
        job = self.jobcache.pop(jid,None)
        if job == None:
            raise NoSuchJob(jid)

        return job.sync()

    def waitForJob(self, jid, timeout=None):
        '''
        Wait for completion of a previous async call.

        Example:

            j1 = core.addRows( rows1 )
            j2 = core.addRows( rows2 )
            j3 = core.addRows( rows3 )

            core.waitForJob( j3 )

        '''
        return self.boss.waitForJob(jid, timeout=timeout)

    def addRows(self, rows, async=False):
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
        if async:
            return self.async.addRows(rows).jid

        self._addRows(rows)

    def callAsyncApi(self, api, *args, **kwargs):
        '''
        Call a cortex API asynchronously to return for results later.

        Example:

            jid = core.callAsyncApi('getRowsByProp','foo',valu=10)
            # do stuff....
            res = core.getAsyncResult(jid)

        Notes:

            * callers are required to retrieve results using
              getAsyncResult(), this API is *not* fire and
              forget.

        '''

        job = self.jobboss.initAsyncJob()
        job.setJobTask( getattr(self,api), *args, **kwargs)

        self.jobcache[job.jid] = job
        job.runInPool()

        return job.jid

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
        '''
        return self._getRowsByIds(idents)

    def delRowsById(self, ident, async=False):
        '''
        Delete all the rows for a given ident.

        Example:

            core.delRowsById(ident)

        '''
        if async:
            return self.async.delRowsById(ident).jid

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

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, async=False):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)
        '''
        if async:
            return self.async.delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime).jid

        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, async=False):
        '''
        Delete a group of rows by selecting for property and joining on ident.

        Example:

        '''
        if async:
            return self.async.delJoinByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime).jid

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
