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
        c.put('woot',10)

        e.wait(timeout=2)
        self.assertIsNotNone( data.get('event') )

    def test_cache_set_maxtime(self):
        c = s_cache.Cache()

        c.setMaxTime(0.1)

        e = threading.Event()
        data = {}
        def onflush(event):
            data['event'] = event
            e.set()

        c.on('cache:flush', onflush)
        c.put('woot',10)

        e.wait(timeout=2)
        self.assertIsNotNone( data.get('event') )

    def test_cache_miss(self):
        c = s_cache.Cache()
        def onmiss(key):
            return 10

        c.setOnMiss( onmiss )
        self.assertEqual( c.get('woot'), 10 )

    def test_cache_tufo(self):
        core = s_cortex.openurl('ram:///')
        cache = s_cache.TufoCache(core)

        tufo = core.formTufoByProp('woot','haha', lolol=10)

        newfo = cache.get(tufo[0])

        self.assertIsNotNone(newfo)
        self.assertEqual(newfo[1].get('woot:lolol'), 10)

    def test_cache_tufo_prop(self):
        core = s_cortex.openurl('ram:///')
        cache = s_cache.TufoPropCache(core,'woot')

        tufo = core.formTufoByProp('woot','haha', lolol=10)

        newfo = cache.get('haha')

        self.assertIsNotNone(newfo)
        self.assertEqual(newfo[1].get('woot:lolol'), 10)

    def test_ondem_add(self):

        data = {'count':0}
        def getfoo(x,y=0):
            data['count'] += 1
            return x + y

        od = s_cache.OnDem()
        od.add('foo', getfoo, 10, y=20 )

        self.assertEqual( od.get('foo'), 30 )
        self.assertEqual( od.get('foo'), 30 )
        self.assertEqual( data.get('count'), 1 )

    def test_ondem_class(self):

        data = {'count':0}

        class Woot(s_cache.OnDem):

            @s_cache.keymeth('foobar')
            def _getFooBar(self):
                data['count'] += 1
                return 'hi there'

        woot = Woot()

        self.assertEqual( woot.get('foobar'), 'hi there' )
        self.assertEqual( woot.get('foobar'), 'hi there' )
        self.assertEqual( data.get('count'), 1 )

    def test_keycache_lookup(self):

        foo = {10:'asdf'}

        def getfoo(x):
            return foo.get(x)

        cache = s_cache.KeyCache(getfoo)

        self.assertEqual( cache[10], 'asdf' )

    def test_cache_fixed(self):

        data = collections.defaultdict(int)
        def getfoo(x):
            data[x] += 1
            return x + 20

        cache = s_cache.FixedCache(maxsize=3, onmiss=getfoo)
        self.eq( cache.get(30), 50 )
        self.eq( cache.get(30), 50 )
        self.eq( cache.get(30), 50 )
        self.eq( cache.get(30), 50 )

        self.eq( data[30], 1 )

        self.eq( cache.get(40), 60 )
        self.eq( cache.get(50), 70 )
        self.eq( cache.get(60), 80 )

        self.eq( data[30], 1 )

        self.eq( cache.get(30), 50 )

        self.eq( data[30], 2 )

        cache.clear()

        self.eq( cache.get(30), 50 )

        self.eq( data[30], 3 )
