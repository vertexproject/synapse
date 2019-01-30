import os

import synapse.exc as s_exc
import synapse.common as s_common

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

            nodes = await core.eval('.created').list()
            self.len(7, nodes)

            for node in nodes:
                self.eq(node.buid, s_common.buid(node.ndef))

            # check that we updated the univ index
            self.len(2, await core.eval('.created +file:bytes').list())
            self.len(2, await core.eval('file:bytes.created').list())

            # check that we updated the tag index
            self.len(1, await core.eval('file:bytes#foo').list())
            self.len(1, await core.eval('#foo +file:bytes').list())

            # check that we updated the secondary prop buids
            self.len(1, await core.eval('file:bytes +:size=200').list())
            self.len(1, await core.eval('file:bytes:size=200').list())

            # check that *other* secondary props got updated
            self.len(1, await core.eval('inet:flow=3e6659a92d18cab2f20bfc1adecc3284 :src:exe -> file:bytes').list())

            # check that we updated the ndefs for edge types...
            self.len(1, await core.eval('file:bytes=ecb4789e1c9588964dbaefc4c2380e83 -> refs -> ps:person').list())

            nodes = await core.eval('refs').list()
            for node in nodes:
                self.eq(node.buid, s_common.buid(node.ndef))

                n1def = node.get('n1')
                n2def = node.get('n2')

                self.eq(node.ndef[1], (n1def, n2def))

            nodes = await core.eval('file:bytes#foo').list()
            self.len(1, nodes)
            self.eq(200, nodes[0].get('size'))
            self.eq(('file:bytes', '96bad5aea02c4757e971d61faf988390'), nodes[0].ndef)

            nodes = await core.eval('#foo').list()
            self.len(1, nodes)
            self.eq(200, nodes[0].get('size'))
            self.eq(('file:bytes', '96bad5aea02c4757e971d61faf988390'), nodes[0].ndef)
