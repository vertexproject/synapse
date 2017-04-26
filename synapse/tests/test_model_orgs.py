import synapse.cortex as s_cortex

from synapse.tests.common import *

class OrgTest(SynTest):

    def test_model_orgs_seed_alias(self):
        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce',1)

            node0 = core.formTufoByProp('ou:org:alias','wewtcorp',name='The Woot Corp')

            self.eq(node0[1].get('ou:org:alias'), 'wewtcorp')
            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            node1 = core.formTufoByProp('ou:org:alias','wewtcorp')

            self.eq(node0[0],node1[0])

    def test_model_orgs_seed_name(self):
        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce',1)

            node0 = core.formTufoByProp('ou:org:name','The Woot Corp')
            node1 = core.formTufoByProp('ou:org:name','the woot corp')

            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            self.eq(node0[0],node1[0])
