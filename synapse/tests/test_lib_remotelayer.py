import os
import contextlib

import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common

import synapse.tests.test_cortex as t_cortex
import synapse.tests.test_lib_snap as t_snap
import synapse.tests.test_lib_layer as t_layer

class RemoteLayerTest(t_cortex.CortexTest):

    @contextlib.asynccontextmanager
    async def getTestCore(self):

        async with self.getTestDmon('dmoncore') as dmon:

            core0 = dmon.shared.get('core')
            layer = core0.layers[0]
            dmon.share('layer', layer)

            async with t_cortex.CortexTest.getTestCore(self) as core:
                url = self.getTestUrl(dmon, 'layer')
                dirn = os.path.join(core.dirn, 'layers', s_common.guid())
                layr = await s_cells.init('layer-remote', dirn, teleurl=url)

                await core.layer.fini()

                core.layer = layr
                core.layers[0] = layr

                yield core
