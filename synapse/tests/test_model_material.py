import synapse.lib.hashset as s_hashset

from synapse.common import guid
from synapse.tests.common import SynTest

class MatTest(SynTest):

    def test_model_mat_spec_item(self):
        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                n0_guid = guid()
                node0 = xact.addNode('mat:spec', n0_guid, props={'name': 'F16 Fighter Jet'})
                n1_guid = guid()
                node1 = xact.addNode('mat:item', n1_guid, props={'name': "Visi's F16 Fighter Jet"})

                hset = s_hashset.HashSet()
                hset.update(b'blahblah')

                valu, props = hset.guid()
                f0_hash = props['sha256']
                f0 = xact.addNode('file:bytes', f0_hash)

                self.eq(node0.props.get('name'), 'f16 fighter jet')
                self.eq(node1.props.get('name'), "visi's f16 fighter jet")

                node2 = xact.addNode('mat:specimage', (n0_guid, f0_hash), {})
                node3 = xact.addNode('mat:itemimage', (n1_guid, f0_hash), {})

                self.eq(node2.props.get('spec'), n0_guid)
                self.eq(node2.props.get('file'), f0_hash)

                self.eq(node3.props.get('item'), n1_guid)
                self.eq(node3.props.get('file'), f0_hash)
