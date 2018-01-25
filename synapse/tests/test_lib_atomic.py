import random

from synapse.tests.common import *

import synapse.glob as s_glob
import synapse.lib.atomic as s_atomic

class AtomTest(SynTest):

    def test_atomic_xchg(self):

        xchg = s_atomic.CmpSet(False)

        self.false(xchg.set(False))

        self.true(xchg.set(True))

        self.false(xchg.set(True))

    def test_atomic_counter(self):
        # Start at zero
        counter = s_atomic.Counter()
        # valu() api works
        self.eq(counter.valu(), 0)

        # Set works
        self.eq(counter.set(1234), 1234)
        self.eq(counter.valu(), 1234)
        self.eq(counter.set(), 0)
        self.eq(counter.valu(), 0)

        # update with negative numbers works
        self.eq(counter.inc(-10), -10)
        self.eq(counter.inc(-15), -25)

        # Start at -1
        counter = s_atomic.Counter(-1)
        self.eq(counter.valu(), -1)

        # Default increment is 1
        self.eq(counter.inc(), 0)
        self.eq(counter.inc(), 1)
        # can increment multiple values at once
        self.eq(counter.inc(2), 3)

        counter = s_atomic.Counter()
        maxtime = 6
        tslice = 0.01

        valus = [random.randint(0, 100) for _ in range(10)]
        esum = sum(valus)

        # Fire a bunch of increment calls into the thread pool
        for v in valus:
            s_glob.pool.call(counter.inc, v)

        while counter.valu() != esum:
            time.sleep(tslice)
            if tslice == maxtime:
                break
        self.eq(counter.valu(), esum)

    def test_atomic_ready(self):

        ready = s_atomic.Ready(size=2)
        self.false(ready.wait(timeout=0.001))

        ready.inc()
        self.false(ready.wait(timeout=0.001))

        ready.inc()
        self.true(ready.wait(timeout=0.001))

        ready.dec()
        self.false(ready.wait(timeout=0.001))

        ready = s_atomic.Ready(size=2)

        with ready:

            self.false(ready.wait(timeout=0.001))
            with ready:
                self.true(ready.wait(timeout=0.001))

            self.false(ready.wait(timeout=0.001))

        self.false(ready.wait(timeout=0.001))
