import copy

import synapse.tests.utils as s_test
from pprint import pprint

import synapse.lib.stormlib.stix as s_stix

class StormlibModelTest(s_test.SynTest):

    async def test_stormlib_stix_uuid_covert(self):
        buid = b'\xa5\x5a' * 16
        uuid = s_stix._buid_to_uuid4(buid)
        self.len(36, uuid)
        buidpre = s_stix._uuid4_to_buidpre(uuid)
        self.true(buid.startswith(buidpre))

    async def test_stormlib_libstix(self):

        async with self.getTestCore() as core:
            q = '[ps:contact=* :name=visi :loc=us ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '''
            ps:contact
            $bund = $lib.stix.bundle()
            $s = $bund.addNode($node)
            return($s)'''
            retn = await core.callStorm(q)
            self.eq(retn.get('type'), 'identity')
