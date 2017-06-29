from synapse.tests.common import *

import synapse.data as s_data

class DataTest(SynTest):

    def test_data_iana_tlds(self):
        self.true('link' in s_data.get('iana.tlds'))
