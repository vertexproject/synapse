import queue
import threading
import traceback

import synapse.threads as s_threads

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

