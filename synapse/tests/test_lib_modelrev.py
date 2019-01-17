import synapse.cells as s_cells
import synapse.tests.utils as s_tests
import synapse.lib.modelrev as s_modelrev

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with await s_cells.init('cortex', dirn) as core:
                self.true(core.layers[0].fresh)
                self.eq((0, 0, 0), await core.layers[0].getModelVers())

            # no longer "fresh"
            async with await s_cells.init('cortex', dirn) as core:

                self.false(core.layers[0].fresh)
                self.eq((0, 0, 0), await core.layers[0].getModelVers())

                mrev = s_modelrev.ModelRev(core)

                core.layers[0].woot = False

                async def woot(x, layr):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(core.layers[0].woot)
                self.eq((9999, 9999, 9999), await core.layers[0].getModelVers())
