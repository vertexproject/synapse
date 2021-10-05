import os

import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class VendorTest(s_t_utils.SynTest):

    def setUp(self) -> None:
        if not s_common.envbool('SYN_VENDOR_TEST'):  # pragma: no cover
            self.skip('Skipping vendored test.')
