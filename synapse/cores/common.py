import queue
import threading
import traceback

import synapse.threads as s_threads

from synapse.eventbus import EventBus

class NoSuchGetBy(Exception):pass

class Cortex(EventBus):
    '''
    Top level Cortex key/valu storage object.

    ( use getCortex() to instantiate )
    '''
    def __init__(self, **corinfo):
        EventBus.__init__(self)

        self.lock = threading.Lock()

        self.corinfo = corinfo
        self.rowsbymeths = {}
        self.liftbymeths = {}

        self._initCortex()

        self.asyncq = queue.Queue()
        self.asyncthr = s_threads.worker( self._runAsyncQueue )

        self.onfini( self._finiCortex )

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
            return self._addAsyncTodo(self.addRows, rows)

        self._addRows(rows)
        self.fire('cortex:add:rows',rows=rows)

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
            return self._addAsyncTodo(self.delRowsById, ident)

        self._delRowsById(ident)
        self.fire('cortex:del:id',id=ident)

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

    def getRowsBy(self, name, prop, valu):
        return self._getRowsBy(name,prop,valu)

    def getJoinBy(self, name, prop, valu):
        return self._getJoinBy(name,prop,valu)

    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Cortex.

        Example:

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initJoinBy(self, name, meth):
        '''
        Initialize a "lift by" handler for the Cortex.

        Example:

        Notes:

            * Used by Cortex implementors to facilitate
              getJoinBy(...)

        '''
        self.liftbymeths[name] = meth

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].

        Example:

            core.delRowsByProp('foo',valu=10)
        '''
        return self._delRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        '''
        return self._delJoinByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime)

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(prop,valu=valu,mintime=mintime,maxtime=maxtime,limit=limit):
            for jrow in self._getRowsById(irow[0]):
                yield jrow

    def _reqJoinByMeth(self, name):
        meth = self.liftbymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth

    def _reqRowsByMeth(self, name):
        meth = self.rowsbymeths.get(name)
        if meth == None:
            raise NoSuchGetBy(name)
        return meth

    def _runAsyncQueue(self):
        while True:
            todo = self.asyncq.get()
            if todo == None:
                return

            meth,args,kwargs = todo
            try:
                meth(*args,**kwargs)
            except Exception as e:
                traceback.print_exc()

    def _finiCortex(self):
        self.asyncq.put(None)
        self.asyncthr.join()

    def _addAsyncTodo(self, meth, *args, **kwargs):
        self.asyncq.append( (meth,args,kwargs) )

