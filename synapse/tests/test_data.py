import json

import synapse.exc as s_exc
import synapse.data as s_data

import synapse.lib.httpapi as s_httpapi

import synapse.tests.utils as s_t_utils

schema = s_data.getJSON('attack-flow-schema-2.0.0')

class HttpJsonSchema(s_httpapi.Handler):
    async def get(self):
        self.write(json.dumps(schema))

class DataTest(s_t_utils.SynTest):

    def test_data_iana_tlds(self):
        self.true('link' in s_data.get('iana.tlds'))
