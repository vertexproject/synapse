import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class MatTest(s_t_utils.SynTest):

    async def test_model_phys_volume(self):

        async with self.getTestCore() as core:
            volu = core.model.type('phys:volume')
            self.eq('1', (await volu.norm(1))[0])
            self.eq('1', (await volu.norm('1ml'))[0])
            self.eq('1000', (await volu.norm('1l'))[0])
            self.eq('1000000', (await volu.norm('1m^3'))[0])
            self.eq('1', (await volu.norm('1cm^3'))[0])
            self.eq('3785.41', (await volu.norm('1 gal'))[0])
            self.eq('158987', (await volu.norm('1 bbl'))[0])

            with self.raises(s_exc.BadTypeValu):
                await volu.norm('1 newps')

            with self.raises(s_exc.BadTypeValu):
                await volu.norm('newps')

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
                :place=$p.place as geo:place
                :place:loc=$p."place:loc"
                :place:latlong=$p."place:latlong"
                :spec=$p.spec as mat:spec
                :period=(2010, 2020)
            ]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node1 = nodes[0]

            self.propeq(node0, 'name', 'F16 Fighter Jet')
            self.none(node0.get('place:latlong'))
            self.propeq(node1, 'name', "Visi's F16 Fighter Jet")
            self.propeq(node1, 'place', place)
            self.propeq(node1, 'place:loc', 'us.hehe.haha')
            self.propeq(node1, 'place:latlong', (0.0, 0.0))

            # phys:object provides a phys:lifespan :period ( created / retired ) and the entity:destroyable interface
            self.true(core.model.form('mat:item').implements('entity:destroyable'))
            self.eq(1262304000000000, node1.get('period.created'))
            self.eq(1577836800000000, node1.get('period.retired'))
            self.len(1, await core.nodes('mat:item +:period.created>=2009'))
            self.len(1, await core.nodes('mat:item +:period.retired<2099'))

            self.len(1, await core.nodes('mat:spec:name="f16 fighter jet" -> mat:item'))

    async def test_model_material(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                phys:contained=*
                    :period=(2024, ?)
                    :type=component
                    :object={[ mat:item=* :phys:volume=9000l :place:loc=us.ny ]}
                    :container={[ mat:item=* :phys:volume=10000l :place:loc=us.ny ]}
            ]''')

            self.nn(nodes[0].get('object'))
            self.nn(nodes[0].get('container'))
            self.propeq(nodes[0], 'type', 'component.')
            self.propeq(nodes[0], 'period', (1704067200000000, 9223372036854775807, 0xffffffffffffffff))
            self.len(1, await core.nodes('phys:contained -> phys:contained:type:taxonomy'))
