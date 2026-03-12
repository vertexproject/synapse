import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class MatTest(s_t_utils.SynTest):

    async def test_model_mat_spec_item(self):
        async with self.getTestCore() as core:

            place = s_common.guid()
            n0_guid = s_common.guid()
            n1_guid = s_common.guid()
            f0_valu = s_common.guid()
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

            self.propeq(node0, 'name', 'f16 fighter jet')
            self.none(node0.get('place:latlong'))
            self.propeq(node1, 'name', "visi's f16 fighter jet")
            self.propeq(node1, 'place', place)
            self.propeq(node1, 'place:loc', 'us.hehe.haha')
            self.propeq(node1, 'place:latlong', (0.0, 0.0))

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
            self.propeq(nodes[0], 'type', 'component.')
            self.eq((1704067200000000, 9223372036854775807, 0xffffffffffffffff), nodes[0].get('period'))
            self.len(1, await core.nodes('phys:contained -> phys:contained:type:taxonomy'))
