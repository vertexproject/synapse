import synapse.tests.utils as s_t_utils

import synapse.data as s_data

class DataTest(s_t_utils.SynTest):

    def test_data_iana_tlds(self):
        self.true('link' in s_data.get('iana.tlds'))
