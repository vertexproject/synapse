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
                     'place:latlong': '0,0', 'place': place, 'place:loc': 'us.hehe.haha'}
            opts = {'vars': {'valu': n0_guid, 'p': props}}
            q = '''
            [ mat:item=$valu
                :name=$p.name
                :place=$p.place
                :place:loc=$p."place:loc"
                :place:latlong=$p."place:latlong"
                :spec=$p.spec
            ]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node1 = nodes[0]

            self.eq(node0.get('name'), 'f16 fighter jet')
            self.none(node0.get('place:latlong'))
            self.eq(node1.get('name'), "visi's f16 fighter jet")
            self.eq(node1.get('place'), place)
            self.eq(node1.get('place:loc'), 'us.hehe.haha')
            self.eq(node1.get('place:latlong'), (0.0, 0.0))

            nodes = await core.nodes('[mat:specimage=$valu]', opts={'vars': {'valu': (n0_guid, f0_valu)}})
            self.len(1, nodes)
            node2 = nodes[0]

            nodes = await core.nodes('[mat:itemimage=$valu]', opts={'vars': {'valu': (n1_guid, f0_valu)}})
            self.len(1, nodes)
            node3 = nodes[0]

            self.eq(node2.get('spec'), n0_guid)
            self.eq(node2.get('file'), f0_valu)

            self.eq(node3.get('item'), n1_guid)
            self.eq(node3.get('file'), f0_valu)

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
