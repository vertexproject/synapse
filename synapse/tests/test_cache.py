import unittest
import threading

import synapse.cache as s_cache

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
        def onmiss(event):
            key = event[1].get('key')
            c.put(key,10)

        c.on('cache:miss', onmiss)
        self.assertEqual( c.get('woot'), 10 )
