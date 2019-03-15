import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.remotelayer as s_remotelayer

import synapse.tests.utils as s_test
import synapse.tests.test_cortex as t_cortex

class RemoteLayerTest(t_cortex.CortexTest):

    @contextlib.asynccontextmanager
    async def getTestCore(self, conf=None, dirn=None):

        # make remote core from provided dirn for repeatability
        dirn0 = None
        if dirn is not None:
            dirn0 = s_common.gendir(dirn, 'remotecore')

        async with self.getRemoteCores(dirn0=dirn0, conf1=conf, dirn1=dirn) as (core0, core1):
            yield core1

    @contextlib.asynccontextmanager
    async def getRemoteCores(self, conf0=None, conf1=None, dirn0=None, dirn1=None):
        async with t_cortex.CortexTest.getTestCore(self, conf=conf0, dirn=dirn0) as core0:
            async with t_cortex.CortexTest.getTestCore(self, conf=conf1, dirn=dirn1) as core1:
                conf = {'url': core0.getLocalUrl('*/layer')}
                layr = await core1.addLayer(type='remote', config=conf)
                await core1.view.addLayer(layr, indx=0)
                yield core0, core1

    async def test_cortex_remote_layer(self):

        async with self.getTestCore() as core:

            await s_common.aspin(core.eval('[ test:str=woot :tick=2015 ]'))

            layr = core.view.layers[0]
            self.true(isinstance(layr, s_remotelayer.RemoteLayer))

            self.len(1, [x async for x in layr.iterFormRows('test:str')])
            self.len(1, [x async for x in layr.iterPropRows('test:str', 'tick')])

            iden = s_common.guid()

            buid = s_common.buid(('test:str', 'woot'))
            props = await layr.getBuidProps(buid)

            self.eq('woot', props.get('*test:str'))

            await layr.setOffset(iden, 200)
            self.eq(200, await layr.getOffset(iden))

            self.ne((), tuple([x async for x in layr.splices(0, 200)]))

            self.eq((0, 0, 0), await layr.getModelVers())
            await self.asyncraises(s_exc.SynErr, layr.setModelVers((9, 9, 9)))

    async def test_splice_generation(self):
        self.skip('test_splice_generation directly uses layers')

    async def test_splice_cryo(self):
        self.skip('test_splice_generation directly uses layers')

    async def test_splice_sync(self):
        self.skip('test_splice_sync directly uses events')

    async def test_cortex_remote_reconn(self):

        async with self.getRemoteCores() as (core0, core1):

            await core0.eval('[test:str=woot]').list()
            self.len(1, await core1.eval('test:str=woot').list())

            # hulk smash the proxy
            await core1.view.layers[0].proxy.fini()

            # cause a reconnect...
            self.len(1, await core1.eval('test:str=woot').list())

class RemoteLayerConfigTest(s_test.SynTest):

    async def test_cortex_remote_config(self):
        # Full telepath / auth stack
        pconf = {'user': 'root', 'passwd': 'root'}

        # use the original API so we dont do yodawg layers remote layers
        async with self.getTestCoreAndProxy() as (core0, prox0):

            rem1 = await core0.auth.addUser('remuser1')

            await rem1.setPasswd('beep')
            await rem1.addRule((True, ('layer:lift', core0.iden)))

            # make a test:str node
            nodes = await core0.eval('[test:str=woot]').list()
            self.len(1, nodes)

            created = nodes[0].get('.created')

            addr, port = await core0.dmon.listen('tcp://127.0.0.1:0/')

            layerurl = f'tcp://remuser1:beep@127.0.0.1:{port}/cortex/layer'

            await asyncio.sleep(0.002)

            with self.getTestDir() as dirn:

                async with self.getTestCore(dirn=dirn) as core1:

                    self.len(0, await core1.eval('test:str=woot').list())
                    self.len(1, core1.view.layers)

                    # Add the remote layer via Telepath
                    self.nn(await core1.joinTeleLayer(layerurl))
                    self.len(2, core1.view.layers)

                    self.len(1, await core1.eval('test:str=woot').list())

                    # Lift the node and set a prop in our layer
                    nodes = await core1.eval('test:str=woot [:tick=2018]').list()
                    self.len(1, nodes)
                    self.eq(created, nodes[0].get('.created'))
                    self.eq(1514764800000, nodes[0].get('tick'))

                async with self.getTestCore(dirn=dirn) as core1:

                    self.len(2, core1.view.layers)

                    nodes = await core1.eval('test:str=woot').list()
                    self.len(1, nodes)
                    self.eq(created, nodes[0].get('.created'))
                    self.eq(1514764800000, nodes[0].get('tick'))
