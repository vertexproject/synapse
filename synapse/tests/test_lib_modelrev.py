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
                self.eq((0, 0, 0), await layr.getModelVers())

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

                self.eq((0, 0, 0), await layr.getModelVers())

                mrev = s_modelrev.ModelRev(core)

                layr.woot = False

                async def woot(x, layr):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(layr.woot)
                self.eq((9999, 9999, 9999), await layr.getModelVers())
