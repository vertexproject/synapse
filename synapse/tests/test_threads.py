import unittest
import threading

import synapse.threads as s_threads

class ThreadsTest(unittest.TestCase):

    def test_threads_boss(self):

        evt = threading.Event()

        data = {}
        def threadinit(thr):
            data['init'] = True

        def threadfini(thr):
            data['fini'] = True
            evt.set()

        boss = s_threads.ThreadBoss()
        boss.synOn('thread:init',threadinit)
        boss.synOn('thread:fini',threadfini)

        def woot(x,y):
            data['woot'] = x + y

        boss.worker( woot, 20, 30 )

        evt.wait()
        boss.synFireFini()

        self.assertTrue( data.get('init') )
        self.assertTrue( data.get('fini') )
        self.assertEqual( data.get('woot'), 50 )
