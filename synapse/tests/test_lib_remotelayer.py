import os
import contextlib

import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common

import synapse.tests.test_cortex as t_cortex
import synapse.tests.test_lib_snap as t_snap
import synapse.tests.test_lib_layer as t_layer

#class RemoteLayerTest(t_cortex.CortexTest):

    #@contextlib.asynccontextmanager
    #async def getTestCore(self):

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
