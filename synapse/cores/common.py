import queue
import threading
import traceback

import synapse.async as s_async

from synapse.eventbus import EventBus

class NoSuchGetBy(Exception):pass
class DupCortexName(Exception):pass

class Cortex(EventBus):
    '''
    Top level Cortex key/valu storage object.

    ( use getCortex() to instantiate )
    '''
    def __init__(self, link):
        EventBus.__init__(self)
        self.link = link

        self.lock = threading.Lock()

        self.sizebymeths = {}
        self.rowsbymeths = {}

        self._initCortex()

        self.boss = s_async.AsyncBoss(pool=1)
        self.async = s_async.AsyncApi(self.boss, self)

        self.onfini( self.boss.fini )

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

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        self.sizebymeths[name] = meth

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

class Corplex:
    '''
    A corplex is a multi-plexor for multiple Cortex instances by name or type.

    Example:

        plex = Corplex()
        plex.addCortex('foo','bar','

    '''
    def __init__(self):
        self.byname = {}
        self.bytype = collections.defaultdict(list)

    def addCortex(self, name, type, url):
        '''
        Add a cortex URL to the corplex.

        Example:

            # two different cortex instances
            url1 = 'sqlite:///:memory:'
            url2 = 'tcp://1.2.3.4:443/foocore'

            plex.addCortex('bar','baz',url1)
            plex.addCortex('foo','baz',url2)

        '''
        core = self.byname.get(name)
        if core != None:
            raise DupCortexName(name)

        # types may not collide with names!
        core = self.byname.get(type)
        if core != None:
            raise DupCortexName(type)

        core = cortex.open(url)
        self.byname[name] = core
        self.bytype[name].append(core)

