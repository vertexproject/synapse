import unittest
import threading

import synapse.cache as s_cache
import synapse.cortex as s_cortex

from synapse.common import *

class CacheTest(unittest.TestCase):

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
        self.assertEqual(newfo[1].get('lolol'), 10)

    def test_cache_tufo_prop(self):
        core = s_cortex.openurl('ram:///')
        cache = s_cache.TufoPropCache(core,'woot')

        tufo = core.formTufoByProp('woot','haha', lolol=10)

        newfo = cache.get('haha')

        self.assertIsNotNone(newfo)
        self.assertEqual(newfo[1].get('lolol'), 10)

