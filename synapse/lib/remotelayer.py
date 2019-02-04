'''
The layer that exists locally (as a client) passing data requests to a remote layer
'''
import logging

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.layer as s_layer

logger = logging.getLogger(__name__)

PASSTHROUGHFUNCS = (
    'commit', 'getBuidProps', 'getOffset', 'setOffset', 'stat', 'initdb', 'stor', 'splicelistAppend',
)

class RemoteLayer(s_layer.Layer):
    '''
    A layer retrieved over telepath.
    '''
    confdefs = (  # type: ignore
        ('remote:telepath', {'type': 'str', 'doc': 'Path to remote layer'}),
    )

    async def __anit__(self, dirn, readonly=False, teleurl=None):

        await s_layer.Layer.__anit__(self, dirn, readonly=readonly)

        # a remote layer may never be revd
        self.canrev = False

        if teleurl is None:
            teleurl = self.conf.get('remote:telepath')

        self.teleurl = teleurl

        #self.path = self.conf.get('remote:telepath')
        if self.teleurl is None:
            raise s_exc.BadConfValu(mesg='remote:telepath must be url for remote layer')

        self.remote = await s_telepath.openurl(self.teleurl)
        self.onfini(self.remote.fini)

        for funcname in PASSTHROUGHFUNCS:
            setattr(self, funcname, getattr(self.remote, funcname))

    # Hack to get around issue that telepath is not async-generator-transparent

    async def getLiftRows(self, *args, **kwargs):
        async for item in await self.remote.getLiftRows(*args, **kwargs):
            yield item

    async def splices(self, *args, **kwargs):
        async for item in await self.remote.splices(*args, **kwargs):
            yield item

    async def iterFormRows(self, *args, **kwargs):
        async for item in await self.remote.iterFormRows(*args, **kwargs):
            yield item

    async def iterPropRows(self, *args, **kwargs):
        async for item in await self.remote.iterPropRows(*args, **kwargs):
            yield item

    async def iterUnivRows(self, *args, **kwargs):
        async for item in await self.remote.iterUnivRows(*args, **kwargs):
            yield item

    async def getModelVers(self):
        return await self.remote.getModelVers()

    async def setModelVers(self, vers):
        raise s_exc.SynErr(mesg='setModelVers not allowed!')
