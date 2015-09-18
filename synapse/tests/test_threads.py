import time
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

        sched.insec( 0.02, woot2, 20 )
        sched.insec( 0.01, woot1, 10 )

        evt.wait()

        self.assertListEqual( data['woot'], [10,20] )

        sched.fini()

    def test_threads_sched_cancel(self):
        sched = s_threads.Sched()

        def woot2(x):
            pass

        eid = sched.insec( 20, woot2, 20 )
        sched.cancel(eid)

        sched.fini()

    def test_threads_sched_persec(self):
        sched = s_threads.Sched()

        evt = threading.Event()

        data = {'count':0}
        def woot(x,y=None):
            data['x'] = x
            data['y'] = y
            data['count'] += 1
            if data['count'] >= 3:
                evt.set()
                return False

        s = time.time()

        sched.persec(10, woot, 10, y='hehe')
        evt.wait(timeout=0.5)

        elapsed = time.time() - s
        self.assertTrue( elapsed > 0.2 and elapsed < 0.3 )

        self.assertEqual( data['x'], 10 )
        self.assertEqual( data['y'], 'hehe' )
        self.assertEqual( data['count'], 3 )

        sched.fini()

    def test_threads_perthread(self):

        data = dict(count=0)
        def woot(x,y=None):
            data['count'] += 1
            return (x,y)

        per = s_threads.PerThread()
        per.setPerCtor('woot',woot,10,y=20)

        def makeone():
            data['make'] = per.woot

        w1 = per.woot
        w2 = per.woot

        self.assertEqual( w1, (10,20) )
        self.assertEqual( id(w1), id(w2) )
        self.assertEqual( data['count'], 1 )

        thr = threading.Thread(target=makeone)
        thr.start()
        thr.join()

        w3 = data.get('make')
        self.assertEqual( w3, (10,20) )
        self.assertNotEqual( id(w1), id(w3) )
