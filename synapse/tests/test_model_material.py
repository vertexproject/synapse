import synapse.lib.hashset as s_hashset

from synapse.common import guid
from synapse.tests.common import SynTest

class MatTest(s_t_utils.SynTest):

    def test_model_mat_spec_item(self):
        with self.getTestCore() as core:
            with core.snap() as snap:
                n0_guid = guid()
                node0 = snap.addNode('mat:spec', n0_guid, props={'name': 'F16 Fighter Jet'})
                n1_guid = guid()
                node1 = snap.addNode('mat:item', n1_guid, props={'name': "Visi's F16 Fighter Jet", 'latlong': '0,0'})

                f0 = snap.addNode('file:bytes', '*')
                f0_valu = f0.ndef[1]

                self.eq(node0.props.get('name'), 'f16 fighter jet')
                self.none(node0.props.get('latlong'))
                self.eq(node1.props.get('name'), "visi's f16 fighter jet")
                self.eq(node1.props.get('latlong'), (0.0, 0.0))

                node2 = snap.addNode('mat:specimage', (n0_guid, f0_valu), {})
                node3 = snap.addNode('mat:itemimage', (n1_guid, f0_valu), {})

                self.eq(node2.props.get('spec'), n0_guid)
                self.eq(node2.props.get('file'), f0_valu)

                self.eq(node3.props.get('item'), n1_guid)
                self.eq(node3.props.get('file'), f0_valu)
