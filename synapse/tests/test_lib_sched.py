import time
import unittest
import threading

import synapse.lib.sched as s_sched

from synapse.tests.common import *

class SchedTest(SynTest):

    def test_sched_base(self):

        evt = threading.Event()
        data = {'woot': []}
        def woot1(x):
            data['woot'].append(x)

        def woot2(x):
            data['woot'].append(x)
            evt.set()

        sched = s_sched.Sched()

        sched.insec(0.02, woot2, 20)
        sched.insec(0.01, woot1, 10)

        evt.wait(timeout=2)

        self.true(evt.is_set())

        self.eq(data['woot'], [10, 20])

        sched.fini()

    def test_sched_cancel(self):
        sched = s_sched.Sched()

        def woot2(x):
            pass

        eid = sched.insec(20, woot2, 20)
        sched.cancel(eid)

        sched.fini()

    def test_sched_persec(self):
        sched = s_sched.Sched()

        evt = threading.Event()

        data = {'count': 0}
        def woot(x, y=None):
            data['x'] = x
            data['y'] = y
            data['count'] += 1
            if data['count'] >= 3:
                evt.set()
                return False

        s = time.time()

        sched.persec(10, woot, 10, y='hehe')
        evt.wait(timeout=0.5)

        self.true(evt.is_set())

        elapsed = time.time() - s
        self.true(elapsed > 0.2 and elapsed < 0.3)

        self.eq(data['x'], 10)
        self.eq(data['y'], 'hehe')
        self.eq(data['count'], 3)

        sched.fini()

    def test_sched_loop(self):

        data = {'count': 0}

        def foo():
            data['count'] += 1
            if data['count'] > 3:
                return False

        ran = threading.Event()
        def bar():
            data['count'] += 1
            if data['count'] > 3:
                ran.set()

        with s_sched.Sched() as sched:

            loop = sched.loop(0.001, foo)
            self.true(loop.waitfini(timeout=0.1))

            data['count'] = 0
            loop = sched.loop(0.001, bar)
            self.true(ran.wait(timeout=1))

            loop.fini()

            ran.clear()
            self.false(ran.wait(timeout=0.2))
