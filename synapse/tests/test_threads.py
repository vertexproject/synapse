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

