import os
import sys
import contextlib

# Insert the root path of the repository to sys.path
synroot = os.path.abspath('../../../')
sys.path.insert(0, synroot)

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.lib.base as s_base
import synapse.lib.cmdr as s_cmdr
import synapse.lib.node as s_node


@contextlib.asynccontextmanager
async def genTempCmdrCore():
    with s_common.getTempDir() as dirn:
        async with await s_cortex.Cortex.anit(dirn) as core:
            async with core.getLocalProxy() as prox:
                async with await CmdrCore.anit(prox) as cmdrcore:
                    yield cmdrcore

@contextlib.asynccontextmanager
async def genTempCoreProxy():
    with s_common.getTempDir() as dirn:
        async with await s_cortex.Cortex.anit(dirn) as core:
            async with core.getLocalProxy() as prox:
                yield prox

async def getCoreCmdr(core):
    cmdr = await s_cmdr.getItemCmdr(core)
    cmdr.echoline = True
    # Hide unknown cmdr events (ie. splices)
    cmdr.locs['storm:hide-unknown'] = True
    return cmdr

class CmdrCore(s_base.Base):
    '''
    A helper for jupyter/storm CLI interaction
    '''
    async def __anit__(self, core):
        await s_base.Base.__anit__(self)
        self.prefix = 'storm'  # Eventually we may remove or change this
        self.core = core
        self.cmdr = await getCoreCmdr(self.core)
        self.onfini(self.cmdr.fini)
        self.onfini(self._onCmdrCoreFini)
        self.acm = None  # A placeholder for the context manager

    async def _runStorm(self, text, opts=None, cmdr=False):
        mesgs = []

        if cmdr:

            if self.prefix:
                text = ' '.join((self.prefix, text))

            def onEvent(event):
                mesg = event[1].get('mesg')
                mesgs.append(mesg)

            with self.cmdr.onWith('storm:mesg', onEvent):
                await self.cmdr.runCmdLine(text)

        else:
            async for mesg in await self.core.storm(text, opts=opts):
                mesgs.append(mesg)

        return mesgs

    async def storm(self, text, opts=None, num=None, cmdr=False):
        mesgs = await self._runStorm(text, opts, cmdr)
        if num is not None:
            nodes = [m for m in mesgs if m[0] == 'node']
            assert len(nodes) == num

        return mesgs

    async def eval(self, text, opts=None, num=None, cmdr=False):
        mesgs = await self._runStorm(text, opts, cmdr)

        nodes = [m for m in mesgs if m[0] == 'node']

        if num is not None:
            assert len(nodes) == num

        return nodes

    async def _onCmdrCoreFini(self):
        if self.acm:
            await self.acm.__aexit__(None, None, None)


async def getTempCoreProxy():
    acm = genTempCoreProxy()
    proxy = await acm.__aenter__()
    object.__setattr__(proxy, 'acm', acm)
    async def onfini():
        await proxy.acm.__aexit__(None, None, None)
    proxy.onfini(onfini)
    return proxy

async def getTempCmdrCore():
    acm = genTempCmdrCore()
    cmdrcore = await acm.__aenter__()
    cmdrcore.acm = acm
    return cmdrcore
