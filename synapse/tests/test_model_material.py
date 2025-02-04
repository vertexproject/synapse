import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class MatTest(s_t_utils.SynTest):

    async def test_model_mat_spec_item(self):
        async with self.getTestCore() as core:
            place = s_common.guid()
            n0_guid = s_common.guid()
            n1_guid = s_common.guid()
            f0_valu = f'guid:{s_common.guid()}'
            nodes = await core.nodes('[mat:spec=$valu :name="F16 Fighter Jet"]', opts={'vars': {'valu': n0_guid}})
            self.len(1, nodes)
            node0 = nodes[0]

            props = {'name': "Visi's F16 Fighter Jet", 'spec': n0_guid,
                     'latlong': '0,0', 'place': place, 'loc': 'us.hehe.haha'}
            opts = {'vars': {'valu': n0_guid, 'p': props}}
            q = '[(mat:item=$valu :name=$p.name :latlong=$p.latlong :spec=$p.spec :place=$p.place :loc=$p.loc)]'
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node1 = nodes[0]

            self.eq(node0.props.get('name'), 'f16 fighter jet')
            self.none(node0.props.get('latlong'))
            self.eq(node1.props.get('name'), "visi's f16 fighter jet")
            self.eq(node1.props.get('latlong'), (0.0, 0.0))
            self.eq(node1.props.get('place'), place)
            self.eq(node1.props.get('loc'), 'us.hehe.haha')

            nodes = await core.nodes('[mat:specimage=$valu]', opts={'vars': {'valu': (n0_guid, f0_valu)}})
            self.len(1, nodes)
            node2 = nodes[0]

            nodes = await core.nodes('[mat:itemimage=$valu]', opts={'vars': {'valu': (n1_guid, f0_valu)}})
            self.len(1, nodes)
            node3 = nodes[0]

            self.eq(node2.props.get('spec'), n0_guid)
            self.eq(node2.props.get('file'), f0_valu)

            self.eq(node3.props.get('item'), n1_guid)
            self.eq(node3.props.get('file'), f0_valu)

            self.len(1, await core.nodes('mat:spec:name="f16 fighter jet" -> mat:item'))

    async def test_model_material(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                phys:contained=*
                    :period=(2024, ?)
                    :type=component
                    :object={[ mat:item=* :phys:volume=9000cm :place:loc=us.ny ]}
                    :container={[ mat:item=* :phys:volume=10000cm :place:loc=us.ny ]}
            ]''')

            self.nn(nodes[0].get('object'))
            self.nn(nodes[0].get('container'))
            self.eq('component.', nodes[0].get('type'))
            self.eq((1704067200000, 9223372036854775807), nodes[0].get('period'))
            self.len(1, await core.nodes('phys:contained -> phys:contained:type:taxonomy'))
