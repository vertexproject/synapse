from synapse.tests.common import *

import synapse.data as s_data

class DataTest(SynTest):

    def test_data_iana_tlds(self):
        self.assertTrue( 'link' in s_data.get('iana.tlds') )

