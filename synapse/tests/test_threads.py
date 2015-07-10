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
        boss.on('thread:init',threadinit)
        boss.on('thread:fini',threadfini)

        def woot(x,y):
            data['woot'] = x + y

        boss.worker( woot, 20, 30 )

        evt.wait()
        boss.fini()

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

        sched.fini()

    def test_threads_perthread(self):

        data = dict(count=0)
        def woot(x,y=None):
            data['count'] += 1
            return (x,y)

        w1 = s_threads.getPerThread('woot',woot,10,y=20)
        w2 = s_threads.getPerThread('woot',woot,10,y=30)

        self.assertEqual( w1, (10,20) )
        self.assertEqual( w2, (10,20) )
        self.assertEqual( data['count'], 1 )
