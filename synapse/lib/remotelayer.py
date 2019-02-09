'''
The layer that exists locally (as a client) passing data requests to a remote layer
'''
import asyncio
import logging

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.layer as s_layer

logger = logging.getLogger(__name__)

#PASSTHROUGHFUNCS = (
    #'commit', 'getBuidProps', 'getOffset', 'setOffset', 'stat', 'initdb', 'stor', 'splicelistAppend',
#)

class RemoteLayer(s_layer.Layer):
    '''
    A layer retrieved over telepath.

    Expected behaviors during remote proxy connection failures:

        * a reconnect loop begins which will run until success or isfini
        * calls that were already sent or are iterating responses raise an error
        * new calls will pend for up to "readywait" seconds and wake on ready or timeout.

    '''
    confdefs = (  # type: ignore
        ('url', {'type': 'str', 'doc': 'Path to remote layer'}),
        ('readywait', {'type': 'int', 'defval': 30, 'doc': 'Max time to wait for layer ready.'}),
    )

    #async def __anit__(self, dirn, teleurl=None):
    async def __anit__(self, core, node):

        await s_layer.Layer.__anit__(self, core, node)

        # a remote layer may never be revd
        self.proxy = None
        self.canrev = False

        self.ready = asyncio.Event()
        await self._fireTeleTask()

    async def _fireTeleTask(self):

        if self.isfini:
            return

        self.ready.clear()
        self.schedCoro(self._teleConnLoop())

    async def _teleConnLoop(self):

        while not self.isfini:

            try:

                turl = self.conf.get('url')
                self.proxy = await s_telepath.openurl(turl)
                self.proxy.onfini(self._fireTeleTask)
                self.ready.set()
                return

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.exception('remote layer reconnect failure')
                await asyncio.sleep(1)

    async def _readyPlayerOne(self):
        timeout = self.conf.get('readywait')
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    async def stor(self, sops):
        await self._readyPlayerOne()
        return await self.proxy.stor(sops)

    # Hack to get around issue that telepath is not async-generator-transparent
    async def getBuidProps(self, buid):
        await self._readyPlayerOne()
        return await self.proxy.getBuidProps(buid)

    async def getLiftRows(self, *args, **kwargs):
        await self._readyPlayerOne()
        async for item in await self.proxy.getLiftRows(*args, **kwargs):
            yield item

    async def splices(self, *args, **kwargs):
        await self._readyPlayerOne()
        async for item in await self.proxy.splices(*args, **kwargs):
            yield item

    async def iterFormRows(self, *args, **kwargs):
        await self._readyPlayerOne()
        async for item in await self.proxy.iterFormRows(*args, **kwargs):
            yield item

    async def iterPropRows(self, *args, **kwargs):
        await self._readyPlayerOne()
        async for item in await self.proxy.iterPropRows(*args, **kwargs):
            yield item

    async def iterUnivRows(self, *args, **kwargs):
        await self._readyPlayerOne()
        async for item in await self.proxy.iterUnivRows(*args, **kwargs):
            yield item

    async def getModelVers(self):
        await self._readyPlayerOne()
        return await self.proxy.getModelVers()

    async def setModelVers(self, vers):
        await self._readyPlayerOne()
        raise s_exc.SynErr(mesg='setModelVers not allowed!')

    async def commit(self):
        await self._readyPlayerOne()
        return await self.proxy.commit()

    async def getBuidProps(self, buid):
        await self._readyPlayerOne()
        return await self.proxy.getBuidProps(buid)

    async def splices(self, offs, size):
        await self._readyPlayerOne()
        async for item in await self.proxy.splices(offs, size):
            yield item

    async def getOffset(self, iden):
        await self._readyPlayerOne()
        return await self.proxy.getOffset(iden)

    async def setOffset(self, iden, valu):
        await self._readyPlayerOne()
        return await self.proxy.setOffset(iden, valu)
