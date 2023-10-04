import synapse.exc as s_exc
import synapse.data as s_data

import synapse.tests.utils as s_utils

import synapse.utils.getrefs as s_getrefs

class TestUtilsGetrefs(s_utils.SynTest):
    async def test_basics(self):

        with self.getLoggerStream('synapse.utils.getrefs') as stream:
            s_getrefs.download_refs(s_data.getJSON('attack-flow-schema-2.0.0'))

        stream.seek(0)
        mesgs = stream.read()
        mesg = 'Schema '
        mesg += 'http://raw.githubusercontent.com/oasis-open/cti-stix2-json-schemas/stix2.1/schemas/common/core.json '
        mesg += 'already exists in local cache, skipping.'
        self.isin(mesg, mesgs)
        self.notin('Downloading schema from', mesgs)

        with self.raises(s_exc.BadUrl):
            s_getrefs.download_refs_handler('http://[/newp')

        with self.raises(s_exc.BadArg):
            s_getrefs.download_refs_handler('http://raw.githubusercontent.com/../../attack-flow-schema-2.0.0.json')
