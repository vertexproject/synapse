import synapse.tests.utils as s_test

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
            q = '[ ps:contact=* :name=visi :loc=us :title=hax0r ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '''
            ps:contact
            $bund = $lib.stix.bundle()
            $s = $bund.addNode($node)
            return($s)'''
            retn = await core.callStorm(q)
            self.eq(retn.get('type'), 'identity')
            expect = ('type', 'created', 'modified', 'id', 'extensions', 'contact_information',
                      'identity_class', 'name', 'roles', 'spec_version')
            self.sorteq(retn.keys(), expect)

            q = '''
            ps:contact
            $bund = $lib.stix.bundle()
            $s = $bund.addNode($node)
            return($bund.json())'''
            retn = await core.callStorm(q)
            expect = ('type', 'id', 'objects')
            self.sorteq(retn.keys(), expect)

            idobjs = [obj for obj in retn['objects'] if obj['type'] == 'identity']
            relobjs = [obj for obj in retn['objects'] if obj['type'] == 'relationship']
            locobjs = [obj for obj in retn['objects'] if obj['type'] == 'location']
            self.len(3, retn['objects'])
            self.len(1, idobjs)
            self.len(1, relobjs)
            self.len(1, locobjs)

            expect = ('type', 'created', 'modified', 'id', 'extensions', 'contact_information',
                      'identity_class', 'name', 'roles', 'spec_version')
            self.sorteq(idobjs[0].keys(), expect)

            expect = ('id', 'type', 'relationship_type', 'source_ref', 'target_ref', 'spec_version')
            self.sorteq(relobjs[0].keys(), expect)
            self.eq(relobjs[0]['source_ref'], idobjs[0]['id'])
            self.eq(relobjs[0]['target_ref'], locobjs[0]['id'])

            expect = ('id', 'type', 'spec_version', 'country', 'created', 'modified', 'extensions')
            self.sorteq(locobjs[0].keys(), expect)
