import synapse.cortex as s_cortex

from synapse.tests.common import *

class OrgTest(SynTest):

    def test_model_orgs_seed_alias(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:alias', 'wewtcorp', name='The Woot Corp')

            self.eq(node0[1].get('ou:org:alias'), 'wewtcorp')
            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            node1 = core.formTufoByProp('ou:org:alias', 'wewtcorp')

            self.eq(node0[0], node1[0])

    def test_model_orgs_seed_name(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:name', 'The Woot Corp')
            node1 = core.formTufoByProp('ou:org:name', 'the woot corp')

            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            self.eq(node0[0], node1[0])

    def test_model_org_has_webacct(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('ou:haswebacct', (iden, 'ROOTKIT.com/visi'))

            self.eq(node[1].get('ou:haswebacct:web:acct'), 'rootkit.com/visi')
            self.eq(node[1].get('ou:haswebacct:org'), iden)

            self.nn(core.getTufoByProp('ou:org', iden))
            self.nn(core.getTufoByProp('inet:user', 'visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'rootkit.com/visi'))
