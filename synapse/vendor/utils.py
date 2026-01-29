import unittest

import synapse.common as s_common

class VendorTest(unittest.TestCase):

    def setUp(self) -> None:
        if not s_common.envbool('SYN_VENDOR_TEST'):  # pragma: no cover
            raise unittest.SkipTest('Skipping vendored test.')
