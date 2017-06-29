import unittest
import threading
import collections

import synapse.lib.cache as s_cache
import synapse.cortex as s_cortex

from synapse.tests.common import *

class CacheTest(SynTest):

    def test_cache_timeout(self):
        c = s_cache.Cache(maxtime=0.1)

        e = threading.Event()
        data = {}
        def onflush(event):
            data['event'] = event
            e.set()

        c.on('cache:flush', onflush)
        c.put('woot', 10)

        e.wait(timeout=2)
        self.nn(data.get('event'))

    def test_cache_set_maxtime(self):
        c = s_cache.Cache()

        c.setMaxTime(0.1)

        e = threading.Event()
        data = {}
        def onflush(event):
            data['event'] = event
            e.set()

        c.on('cache:flush', onflush)
        c.put('woot', 10)

        e.wait(timeout=2)
        self.nn(data.get('event'))

    def test_cache_miss(self):
        c = s_cache.Cache()
        def onmiss(key):
            return 10

        c.setOnMiss(onmiss)
        self.false('woot' in c)
        self.eq(c.get('woot'), 10)
        self.true('woot' in c)

    def test_cache_tufo(self):
        core = s_cortex.openurl('ram:///')
        cache = s_cache.TufoCache(core)

        tufo = core.formTufoByProp('woot', 'haha', lolol=10)

        newfo = cache.get(tufo[0])

        self.nn(newfo)
        self.eq(newfo[1].get('woot:lolol'), 10)

    def test_cache_tufo_prop(self):
        core = s_cortex.openurl('ram:///')
        cache = s_cache.TufoPropCache(core, 'woot')

        tufo = core.formTufoByProp('woot', 'haha', lolol=10)

        newfo = cache.get('haha')

        self.nn(newfo)
        self.eq(newfo[1].get('woot:lolol'), 10)

    def test_ondem_add(self):

        data = {'count': 0}
        def getfoo(x, y=0):
            data['count'] += 1
            return x + y

        od = s_cache.OnDem()
        od.add('foo', getfoo, 10, y=20)

        self.eq(od.get('foo'), 30)
        self.eq(od.get('foo'), 30)
        self.eq(data.get('count'), 1)

    def test_ondem_class(self):

        data = {'count': 0}

        class Woot(s_cache.OnDem):

            @s_cache.keymeth('foobar')
            def _getFooBar(self):
                data['count'] += 1
                return 'hi there'

        woot = Woot()

        self.eq(woot.get('foobar'), 'hi there')
        self.eq(woot.get('foobar'), 'hi there')
        self.eq(data.get('count'), 1)

    def test_keycache_lookup(self):

        foo = {10: 'asdf'}

        def getfoo(x):
            return foo.get(x)

        cache = s_cache.KeyCache(getfoo)

        self.eq(cache[10], 'asdf')
        # Ensure put/pop methods work.
        cache.put(20, 'wasd')
        self.eq(cache[20], 'wasd')
        self.eq(cache.pop(20), 'wasd')

    def test_cache_fixed(self):

        data = collections.defaultdict(int)
        def getfoo(x):
            data[x] += 1
            return x + 20

        cache = s_cache.FixedCache(maxsize=3, onmiss=getfoo)
        self.false(30 in cache)
        self.eq(cache.get(30), 50)
        self.eq(len(cache), 1)
        self.true(30 in cache)
        self.eq(cache.get(30), 50)
        self.eq(cache.get(30), 50)
        self.eq(cache.get(30), 50)

        self.eq(data[30], 1)

        self.eq(cache.get(40), 60)
        self.eq(cache.get(50), 70)
        self.eq(cache.get(60), 80)

        self.eq(data[30], 1)

        self.eq(cache.get(30), 50)

        self.eq(data[30], 2)

        cache.clear()

        self.eq(cache.get(30), 50)

        self.eq(data[30], 3)

    def test_cache_magic(self):
        c = s_cache.Cache()
        c.put(1, 'a')
        c.put(2, 'b')
        keys = set([])
        values = set([])

        self.eq(len(c), 2)

        cvs = c.values()
        cvs.sort()
        self.eq(cvs, ['a', 'b'])

        cks = c.keys()
        cks.sort()
        self.eq(cks, [1, 2])

        for k, v in c:
            keys.add(k)
            values.add(v)

        self.eq(keys, {1, 2})
        self.eq(values, {'a', 'b'})

    def test_cache_clearing(self):
        c = s_cache.Cache()

        d = {}
        def flush(event):
            key = event[1].get('key')
            d[key] = c.get(key)

        c.on('cache:flush', flush)
        c.put(1, 'a')
        c.put(2, 'b')
        self.eq(len(c), 2)

        c.flush(1)
        self.true(1 in d)
        self.eq(d, {1: 'a'})
        self.eq(len(c), 2)  # A straight flush doesn't remove the key.

        c.clear()
        self.eq(len(c), 0)

    def test_cache_fini(self):
        c = s_cache.Cache(maxtime=0.1)
        c.put(1, 'a')
        self.nn(c.schevt)
        self.nn(c.schevt[1])
        c.fini()
        self.none(c.schevt[1])
        self.eq(len(c), 0)

    def test_cache_defval(self):
        # Ensure default behaviors are covered.
        c = s_cache.Cache()
        r = c.get('foo')
        self.none(r)

        fc = s_cache.FixedCache(maxsize=10)
        fr = fc.get('foo')
        self.none(fr)

        od = s_cache.OnDem()
        with self.raises(KeyError) as cm:
            od.get('foo')
