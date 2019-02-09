import os
import contextlib

import synapse.cells as s_cells
import synapse.common as s_common

import synapse.tests.test_cortex as t_cortex

class RemoteLayerTest(t_cortex.CortexTest):

    @contextlib.asynccontextmanager
    async def getTestCore(self):
        async with t_cortex.CortexTest.getTestCore(self) as core0:
            async with t_cortex.CortexTest.getTestCore(self) as core1:
                conf = {'url': core0.getLocalUrl('*/layer')}
                layr = await core1.addLayer(type='remote', config=conf)
                await core1.view.addLayer(layr, indx=0)
                yield core1

    async def test_cortex_remote_layer(self):

        async with self.getTestCore() as core:
            await s_common.aspin(core.eval('[ teststr=woot :tick=2015 ]'))

            layr = core.view.layers[0]
            self.len(1, [x async for x in layr.iterFormRows('teststr')])
            self.len(1, [x async for x in layr.iterPropRows('teststr', 'tick')])

            iden = s_common.guid()
            await layr.setOffset(iden, 200)
            self.eq(200, await layr.getOffset(iden))

    async def test_splice_generation(self):
        self.skip('test_splice_generation directly uses layers')
