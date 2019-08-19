import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.tests.utils as s_tests
import synapse.lib.modelrev as s_modelrev

def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                self.false(layr.fresh)

                self.eq(s_modelrev.maxvers, await layr.getModelVers())

                mrev = s_modelrev.ModelRev(core)

                layr.woot = False

                async def woot(layers):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(layr.woot)
                self.eq((9999, 9999, 9999), await layr.getModelVers())

    async def test_modelrev_pre010(self):

        sorc = 'a6246e97d7b02e2dcc90dd117611a981'
        plac = '36c0959d703b9d16e7566a858234bece'
        pers = '83fc390015c0c0ed054d09e87aa31853'
        evnt = '7156b48f84de79d3a375baa3c7904387'
        clus = 'fae28e60d8af681f12109d6da0c48555'

        async with self.getRegrCore('pre-010') as core:

            self.len(1, await core.nodes(f'meta:source={sorc} +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'meta:seen=({sorc}, (inet:dns:a, (vertex.link, 1.2.3.4))) +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'graph:event={evnt} +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'graph:cluster={clus} +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'edge:has=((ps:person, {pers}), (geo:place, {plac})) +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'edge:refs=((ps:person, {pers}), (geo:place, {plac})) +#hehe +.seen=2019'))
            self.len(1, await core.nodes(f'edge:wentto=((ps:person, {pers}), (geo:place, {plac}), 2019) +#hehe +.seen=2019'))

            self.len(1, await core.nodes('meta:source#hehe'))
            self.len(1, await core.nodes('meta:source.seen=2019'))
            self.len(1, await core.nodes('meta:source +#hehe +.seen=2019'))

            self.len(1, await core.nodes('meta:seen#hehe'))
            self.len(1, await core.nodes('meta:seen.seen=2019'))
            self.len(1, await core.nodes('meta:seen +#hehe +.seen=2019'))

            self.len(1, await core.nodes('edge:has#hehe'))
            self.len(1, await core.nodes('edge:has.seen=2019'))
            self.len(1, await core.nodes('edge:has +#hehe +.seen=2019'))

            self.len(2, await core.nodes('edge:refs#hehe'))
            self.len(2, await core.nodes('edge:refs.seen=2019'))
            self.len(2, await core.nodes('edge:refs +#hehe +.seen=2019'))

            self.len(1, await core.nodes('edge:wentto#hehe'))
            self.len(1, await core.nodes('edge:wentto.seen=2019'))
            self.len(1, await core.nodes('edge:wentto +#hehe +.seen=2019'))

            self.len(1, await core.nodes('graph:cluster#hehe'))
            self.len(1, await core.nodes('graph:cluster.seen=2019'))
            self.len(1, await core.nodes('graph:cluster +#hehe +.seen=2019'))

            self.len(1, await core.nodes('graph:edge#hehe'))
            self.len(1, await core.nodes('graph:edge.seen=2019'))
            self.len(1, await core.nodes('graph:edge +#hehe +.seen=2019'))

            self.len(1, await core.nodes('graph:timeedge#hehe'))
            self.len(1, await core.nodes('graph:timeedge.seen=2019'))
            self.len(1, await core.nodes('graph:timeedge +#hehe +.seen=2019'))

            self.len(1, await core.nodes('meta:source -> meta:seen :node -> * +inet:dns:a'))

            self.len(1, await core.nodes('ps:person -> edge:has +:n1:form=ps:person +:n2:form=geo:place -> geo:place'))
            self.len(1, await core.nodes('ps:person -> edge:refs +:n1:form=ps:person +:n2:form=geo:place -> geo:place'))
            self.len(1, await core.nodes('ps:person -> edge:wentto +:n1:form=ps:person +:n2:form=geo:place +:time=2019 -> geo:place'))

            # check secondary ndef property index
            self.len(1, await core.nodes('graph:cluster -> edge:refs -> inet:fqdn'))

            # check secondary compound property index
            sorc = (await core.nodes('meta:source'))[0].ndef[1]
            self.len(1, await core.nodes(f'meta:seen:source={sorc}'))

    async def test_modelrev_0_1_1(self):

        cont0 = '7b3bbf19a8e4d3f5204da8c7f6395494'
        cont1 = 'dd0c914ec06bd7851009d5bad7430ff1'

        async with self.getRegrCore('0.1.0') as core:

            opts = {'vars': {'cont0': cont0, 'cont1': cont1}}

            node0 = (await core.nodes('ps:contact=$cont0', opts=opts))[0]
            node1 = (await core.nodes('ps:contact=$cont1', opts=opts))[0]

            self.eq('this is not changed', node0.get('address'))
            self.eq('this has one space', node1.get('address'))
