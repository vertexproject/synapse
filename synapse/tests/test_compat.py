
import synapse.compat as s_compat

from synapse.tests.common import SynTest


class CompatTest(SynTest):

    def test_canstor(self):
        self.assertFalse(s_compat.canstor(True))

    def test_isint(self):
        self.assertTrue(s_compat.isint(True))
