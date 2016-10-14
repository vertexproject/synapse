
import synapse.compat as s_compat

from synapse.tests.common import SynTest


class CompatTest(SynTest):

    def test_isint(self):
        self.assertFalse(s_compat.isint(True))
