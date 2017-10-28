
from synapse.tests.common import *

import synapse.lib.atomic as s_atomic

class AtomTest(SynTest):

    def test_atomic_xchg(self):

        xchg = s_atomic.CmpSet(False)

        self.false(xchg.set(False))

        self.true(xchg.set(True))

        self.false(xchg.set(True))
