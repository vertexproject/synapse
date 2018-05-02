from synapse.tests.common import *

class SynModelTest(SynTest):

    def test_model_syn_alias(self):

        with s_cortex.openurl('ram:///') as core:

            self.eq(core.getTypeNorm('syn:alias', '$foo')[0], '$foo')
            self.raises(BadTypeValu, core.getTypeNorm, 'syn:alias', 'asdf')
            self.raises(BadTypeValu, core.getTypeNorm, 'syn:alias', '$foo bar')

            orgn = core.formTufoByProp('ou:org', '*')

            iden = orgn[1].get('ou:org')
            node = core.formTufoByProp('syn:alias', '$foo', iden=iden)

            orgp = core.getTufoByProp('ou:org', '$foo')
            self.eq(orgn[1].get('ou:org'), orgp[1].get('ou:org'))
