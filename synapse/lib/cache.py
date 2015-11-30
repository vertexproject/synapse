import time
import threading

import synapse.lib.sched as s_sched

from synapse.eventbus import EventBus

miss = ()
class Cache(EventBus):
    '''
    A callback driven cache with options for timeout / maxsize.

    Example:

        cache = Cache(maxtime=60)
        cache.put(iden,thing)

        # ... some time later
        valu = cache.get(iden)

    Notes:

        The maxtime option is used to specify cache time based
        flushing.  Cache accesses continue to bump a timestamp
        forward to facilite flushing the cache entries which
        were least recently requested.

    '''

    def __init__(self, maxtime=None):
        EventBus.__init__(self)

        self.sched = s_sched.getGlobSched()
        self.onmiss = None

        self.cache = {}
        self.lasthit = {}
        self.cachelock = threading.Lock()

        self.onfini( self._onCacheFini )

        self.schevt = None
        self.maxtime = maxtime

        if self.maxtime != None:
            self._checkCacheTimes()

    def setOnMiss(self, onmiss):
        '''
        Set a callback function to use on cache miss.

        Example:

            def onmiss(key):
                return stuff.get(key)

            cache.setOnMiss( onmiss )

        '''
        self.onmiss = onmiss

    def _checkCacheTimes(self):
        mintime = time.time() - self.maxtime
        try:
            hits = [ k for (k,t) in self.lasthit.items() if t < mintime ]
            [ self.pop(k) for k in hits ]
        finally:
            if not self.isfini and self.maxtime != None:
                ival = self.maxtime / 10.0
                self.sched.insec(ival, self._checkCacheTimes )

    def clear(self):
        '''
        Flush and clear the entire cache.
        '''
        [ self.flush(key) for key in self.keys() ]
        self.cache.clear()
        self.lasthit.clear()

    def get(self, key):
        '''
        Return a val from the cache.

        Example:

            val = cache.get(key)

        '''
        val = self.cache.get(key,miss)
        if val is not miss:
            self.lasthit[key] = time.time()
            return val

        if self.onmiss == None:
            return None

        with self.cachelock:
            val = self.cache.get(key,miss)
            if val is miss:
                val = self.onmiss(key)

            self.cache[key] = val
            self.lasthit[key] = time.time()
            return val

    def put(self, key, val):
        '''
        Put a key:val into the cache.

        Example:

            cache.put('woot',10)

        '''
        self.cache[key] = val
        self.lasthit[key] = time.time()
        self.fire('cache:put', key=key, val=val)

    def pop(self, key):
        '''
        Remove and return a val from the cache.

        Example:

            cache.pop('woot')

        '''
        val = self.cache.pop(key,None)

        self.lasthit.pop(key,None)

        self.fire('cache:flush', key=key, val=val)
        self.fire('cache:pop', key=key, val=val)
        return val

    def flush(self, key):
        '''
        Flush a key:val within the cache.

        Example:

            cache.flush('woot')

        Notes:

            * Mostly used to trigger "cache:flush" events
        '''
        val = self.cache.get(key)
        self.fire('cache:flush', key=key, val=val)
        return val

    def keys(self):
        '''
        Return a list of the keys in the cache.

        Example:

            for key in cache.keys():
                stuff(key)

        '''
        return list(self.cache.keys())

    def values(self):
        return list(self.cache.values())

    def __len__(self):
        return len(self.cache)

    def __iter__(self):
        return list( self.cache.items() )

    def _onCacheFini(self):
        for key in self.keys():
            self.pop(key)

        if self.schevt != None:
            self.sched.cancel(self.schevt)

class TufoCache(Cache):

    def __init__(self, core, maxtime=None):
        Cache.__init__(self, maxtime=maxtime)

        self.core = core
        self.setOnMiss( core.getTufoById )

    def _onTufoFlush(self, event):
        iden = event[1].get('key')
        tufo0 = event[1].get('val')

        tufo1 = self.core.getTufoById(iden)
        if tufo1 == None:
            return

        self.core.setTufoProps(tufo1, **tufo0[1])

class TufoPropCache(TufoCache):

    def __init__(self, core, prop, maxtime=None):
        TufoCache.__init__(self, core, maxtime=maxtime)
        self.prop = prop
        self.setOnMiss( self.getTufoByValu )

    def getTufoByValu(self, valu):
        return self.core.getTufoByProp(self.prop,valu)
