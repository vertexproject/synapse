import unittest
import threading

import synapse.threads as s_threads

class ThreadsTest(unittest.TestCase):

    def test_threads_boss(self):

        evt = threading.Event()

        data = {}
        def threadinit(event):
            data['init'] = True

        def threadfini(event):
            data['fini'] = True
            evt.set()

        boss = s_threads.ThreadBoss()
        boss.synOn('thread:init',threadinit)
        boss.synOn('thread:fini',threadfini)

        def woot(x,y):
            data['woot'] = x + y

        boss.worker( woot, 20, 30 )

        evt.wait()
        boss.synFini()

        self.assertTrue( data.get('init') )
        self.assertTrue( data.get('fini') )
        self.assertEqual( data.get('woot'), 50 )

    def test_threads_sched(self):

        evt = threading.Event()
        data = {'woot':[]}
        def woot1(x):
            data['woot'].append(x)

        def woot2(x):
            data['woot'].append(x)
            evt.set()

        sched = s_threads.Sched()

        sched.synIn( 0.02, woot2, 20 )
        sched.synIn( 0.01, woot1, 10 )

        evt.wait()

        self.assertListEqual( data['woot'], [10,20] )

        sched.synFini()
