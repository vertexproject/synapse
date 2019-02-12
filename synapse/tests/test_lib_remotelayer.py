import os
import contextlib

import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.common as s_common

import synapse.tests.test_cortex as t_cortex

import synapse.lib.remotelayer as s_remotelayer

class RemoteLayerTest(t_cortex.CortexTest):

    @contextlib.asynccontextmanager
    async def getTestCore(self):
        async with self.getRemoteCores() as (core0, core1):
            yield core1

    @contextlib.asynccontextmanager
    async def getRemoteCores(self):
        async with t_cortex.CortexTest.getTestCore(self) as core0:
            async with t_cortex.CortexTest.getTestCore(self) as core1:
                conf = {'url': core0.getLocalUrl('*/layer')}
                layr = await core1.addLayer(type='remote', config=conf)
                await core1.view.addLayer(layr, indx=0)
                yield core0, core1

    async def test_cortex_remote_layer(self):

        async with self.getTestCore() as core:

            await s_common.aspin(core.eval('[ teststr=woot :tick=2015 ]'))

            layr = core.view.layers[0]
            self.true(isinstance(layr, s_remotelayer.RemoteLayer))

            self.len(1, [x async for x in layr.iterFormRows('teststr')])
            self.len(1, [x async for x in layr.iterPropRows('teststr', 'tick')])

            iden = s_common.guid()

            buid = s_common.buid(('teststr', 'woot'))
            props = await layr.getBuidProps(buid)

            self.eq('woot', props.get('*teststr'))

            await layr.setOffset(iden, 200)
            self.eq(200, await layr.getOffset(iden))

            self.ne((), tuple([x async for x in layr.splices(0, 200)]))

            self.eq((0, 0, 0), await layr.getModelVers())
            await self.asyncraises(s_exc.SynErr, layr.setModelVers((9, 9, 9)))

    async def test_splice_generation(self):
        self.skip('test_splice_generation directly uses layers')

    async def test_cortex_remote_reconn(self):

        async with self.getRemoteCores() as (core0, core1):

            await core0.eval('[teststr=woot]').list()
            self.len(1, await core1.eval('teststr=woot').list())

            # hulk smash the proxy
            await core1.view.layers[0].proxy.fini()

            # cause a reconnect...
            self.len(1, await core1.eval('teststr=woot').list())
