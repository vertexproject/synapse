import synapse.tests.utils as s_t_utils

import synapse.data as s_data

class DataTest(s_t_utils.SynTest):

    def test_data_iana_tlds(self):
        self.true('link' in s_data.get('iana.tlds'))

    def test_data_localSchemaRefHandler(self):
        # Don't test the wrapper here, just the error handling in the function
        func = s_data.localSchemaRefHandler.__wrapped__

        self.none(func('http://[/newp'))
        self.none(func('http://foo.com/newp.json'))
        self.none(func('http://foo.com/../attack-flow-schema-2.0.0.json'))
