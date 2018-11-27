'''
The layer that exists locally (as a client) passing data requests to a remote layer
'''
import logging
import functools

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.layer as s_layer

logger = logging.getLogger(__name__)

PASSTHROUGHFUNCS = (
    'commit', 'getBuidProps',
    'getOffset', 'setOffset',
    'stat', 'initdb', 'stor', 'splicelist_append',
)

ASYNCGENFUNCS = (
    'splices'
)

class RemoteLayer(s_layer.Layer):
    '''
    A layer retrieved over telepath.
    '''
    confdefs = (  # type: ignore
        ('remote:telepath', {'type': 'str', 'doc': 'Path to remote layer'}),
    )

    async def __anit__(self, dirn, readonly=False):

        await s_layer.Layer.__anit__(self, dirn, readonly=readonly)

        self.path = self.conf.get('remote:telepath')
        if self.path is None:
            raise s_exc.BadConfValu('Missing remote layer path')

        self.remote = await s_telepath.openurl(self.path)
        self.onfini(self.remote.fini)

        for funcname in PASSTHROUGHFUNCS:
            setattr(self, funcname, getattr(self.remote, funcname))

        # for funcname in ASYNCGENFUNCS:
        #     async def f(func, *args, **kwargs):
        #         async for item in await f(*args, **kwargs):
        #             breakpoint()
        #             yield item
        #     breakpoint()
        #     newmeth = functools.partial(f, getattr(self.remote, funcname))
        #     setattr(self, funcname, newmeth)

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
