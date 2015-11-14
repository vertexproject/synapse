import time
import unittest
import threading

import synapse.sched as s_sched

class SchedTest(unittest.TestCase):

    def test_sched_base(self):

        evt = threading.Event()
        data = {'woot':[]}
        def woot1(x):
            data['woot'].append(x)

        def woot2(x):
            data['woot'].append(x)
            evt.set()

        sched = s_sched.Sched()

        sched.insec( 0.02, woot2, 20 )
        sched.insec( 0.01, woot1, 10 )

        evt.wait(timeout=2)

        self.assertTrue( evt.is_set() )

        self.assertListEqual( data['woot'], [10,20] )

        sched.fini()

    def test_sched_cancel(self):
        sched = s_sched.Sched()

        def woot2(x):
            pass

        eid = sched.insec( 20, woot2, 20 )
        sched.cancel(eid)

        sched.fini()

    def test_sched_persec(self):
        sched = s_sched.Sched()

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

    def test_sched_glob(self):
        sched = s_sched.getGlobSched()

        evt = threading.Event()
        data = {}

        def woot():
            data['woot'] = 'woot'
            evt.set()

        sched.insec( 0.01, woot )

        evt.wait(timeout=3)
        self.assertEqual( data.get('woot'), 'woot' )

