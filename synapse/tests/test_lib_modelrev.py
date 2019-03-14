import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.tests.utils as s_tests
import synapse.lib.modelrev as s_modelrev

def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with await s_cells.init('cortex', dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with await s_cells.init('cortex', dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with await s_cells.init('cortex', dirn) as core:

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

        async with self.getRegrCore('pre-010') as core:

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
