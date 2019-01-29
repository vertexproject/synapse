import os

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
                self.true(core.layers[0].fresh)
                self.eq(s_modelrev.version, await core.layers[0].getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with await s_cells.init('cortex', dirn) as core:

                core.layers[0].canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with await s_cells.init('cortex', dirn) as core:

                self.false(core.layers[0].fresh)
                self.eq(s_modelrev.version, await core.layers[0].getModelVers())

                mrev = s_modelrev.ModelRev(core)

                core.layers[0].woot = False

                async def woot(x, layr):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(core.layers[0].woot)
                self.eq((9999, 9999, 9999), await core.layers[0].getModelVers())

    async def test_cortex_model_0_1_0(self):

        async with self.getRegrCore('0.0.0') as core:
            pass
