import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon

import synapse.lib.node as s_node
import synapse.lib.remotelayer as s_remotelayer

import synapse.tests.test_cortex as t_cortex

from synapse.tests.utils import alist

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

    async def test_cortex_remote_dmon(self):
        # Full telepath / auth stack
        pconf = {'user': 'root', 'passwd': 'root'}
        async with self.getTestDmon('dmoncoreauth') as dmon0:
            # Setup a remote user that has view into the layer for core0
            async with await self.getTestProxy(dmon0, 'core', user='root', passwd='root') as core0:
                coreiden = await core0.getCellIden()
                await core0.addAuthUser('remuser1')
                await core0.setUserPasswd('remuser1', 'beep')
                await core0.addAuthRule('remuser1', (True, ('layer:lift', coreiden)))

                # Make a node
                nodes = await alist(await core0.eval('[teststr=core0]'))
                self.len(1, nodes)
                created = s_node.prop(nodes[0], '.created')

            addr, port = dmon0.addr
            # Default path is /layer - could be /layer/iden for a specific layer
            remote_layer_url = f'tcp://remuser1:beep@{addr}:{port}/core/layer'

            await asyncio.sleep(0.002)

            with self.getTestDir(mirror='dmoncoreauth') as dirn:
                async with await s_daemon.Daemon.anit(dirn) as dmon1:
                    self.len(1, dmon1.shared['core'].layers)

                    async with await self.getTestProxy(dmon1, 'core', **pconf) as core1:
                        # Remote layer does not exist, so this node does not exist
                        nodes = await alist(await core1.eval('teststr=core0'))
                        self.len(0, nodes)

                        # Add the remote layer via Telepath
                        ret = await core1.joinTeleLayer(remote_layer_url)
                        print(ret)

                    self.len(2, dmon1.shared['core'].layers)

                    async with await self.getTestProxy(dmon1, 'core', **pconf) as core1:
                        # Lift the node from the remote layer
                        nodes = await alist(await core1.eval('teststr=core0'))
                        self.len(1, nodes)
                        self.eq(created, s_node.prop(nodes[0], '.created'))
                        # Lift the node and set a prop in our layer
                        nodes = await alist(await core1.eval('teststr=core0 [:tick=2018]'))
                        self.len(1, nodes)
                        self.eq(1514764800000, s_node.prop(nodes[0], 'tick'))

                        # Make a node for our layer
                        nodes = await alist(await core1.eval('[teststr=core1]'))
                        self.len(1, nodes)

                        # Lift all teststr nodes
                        nodes = await alist(await core1.eval('teststr'))
                        self.len(2, nodes)

                # Turn the dmon back on and sure the layer configuration persists
                async with await s_daemon.Daemon.anit(dirn) as dmon1:
                    self.len(2, dmon1.shared['core'].layers)
                    async with await self.getTestProxy(dmon1, 'core', **pconf) as core1:
                        # Lift the node from the remote layer
                        nodes = await alist(await core1.eval('teststr=core0'))
                        self.eq(created, s_node.prop(nodes[0], '.created'))

                        # Lift all teststr nodes
                        nodes = await alist(await core1.eval('teststr'))
                        self.len(2, nodes)
