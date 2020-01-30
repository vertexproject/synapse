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

    async def test_modelrev_0_1_1(self):

        cont0 = '7b3bbf19a8e4d3f5204da8c7f6395494'
        cont1 = 'dd0c914ec06bd7851009d5bad7430ff1'

        async with self.getRegrCore('0.1.0') as core:

            opts = {'vars': {'cont0': cont0, 'cont1': cont1}}

            node0 = (await core.nodes('ps:contact=$cont0', opts=opts))[0]
            node1 = (await core.nodes('ps:contact=$cont1', opts=opts))[0]

            self.eq('this is not changed', node0.get('address'))
            self.eq('this has one space', node1.get('address'))
