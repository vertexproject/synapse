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

    async def test_splice_generation(self):
        self.skip('test_splice_generation directly uses layers')

    #async def test_cortex_telepath_layer(self):

        #async with t_cortex.CortexTest.getTestCore(self) as core0:

            #url = core0.getLocalUrl('*/layer')
#
            #async with t_cortex.CortexTest.getTestCore(self) as core1:

                #config={'url': core0.getLocalUrl(share='*/layer')}
                #layr = await core1.addLayer(type='remote', config=config)

                # make the remote layer the "top" layer
                #await core1.view.addLayer(layr, indx=0)

                #yield core1
