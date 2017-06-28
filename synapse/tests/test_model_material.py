from synapse.tests.common import *

class MatTest(SynTest):

    def test_model_mat_spec_item(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            node0 = core.formTufoByProp('mat:spec', guid(), name='F16 Fighter Jet')
            node1 = core.formTufoByProp('mat:item', guid(), name="Visi's F16 Fighter Jet")

            self.eq(node0[1].get('mat:spec:name'), 'f16 fighter jet')
            self.eq(node1[1].get('mat:item:name'), "visi's f16 fighter jet")
