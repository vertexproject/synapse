from synapse.common import guid
import synapse.tests.utils as s_t_utils

class MatTest(s_t_utils.SynTest):

    async def test_model_mat_spec_item(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                place = guid()
                n0_guid = guid()
                node0 = await snap.addNode('mat:spec', n0_guid, props={'name': 'F16 Fighter Jet'})
                n1_guid = guid()
                node1 = await snap.addNode('mat:item', n1_guid,
                                           props={'name': "Visi's F16 Fighter Jet",
                                                  'latlong': '0,0', 'spec': n0_guid,
                                                  'place': place,
                                                  'loc': 'us.hehe.haha'})

                f0 = await snap.addNode('file:bytes', '*')
                f0_valu = f0.ndef[1]

                self.eq(node0.props.get('name'), 'f16 fighter jet')
                self.none(node0.props.get('latlong'))
                self.eq(node1.props.get('name'), "visi's f16 fighter jet")
                self.eq(node1.props.get('latlong'), (0.0, 0.0))
                self.eq(node1.props.get('place'), place)
                self.eq(node1.props.get('loc'), 'us.hehe.haha')

                node2 = await snap.addNode('mat:specimage', (n0_guid, f0_valu), {})
                node3 = await snap.addNode('mat:itemimage', (n1_guid, f0_valu), {})

                self.eq(node2.props.get('spec'), n0_guid)
                self.eq(node2.props.get('file'), f0_valu)

                self.eq(node3.props.get('item'), n1_guid)
                self.eq(node3.props.get('file'), f0_valu)

                self.len(1, await core.nodes('mat:spec:name="f16 fighter jet" -> mat:item'))
