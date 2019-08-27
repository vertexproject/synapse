import asyncio
import logging

import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

class StormService(s_base.Base, s_stormtypes.StormType):
    '''
    A StormService is a wrapper for a telepath proxy to a service
    accessible from the storm runtime.
    '''
    async def __anit__(self, sdef):

        await s_base.Base.__anit__(self)
        s_stormtypes.StormType.__init__(self)

        self.sdef = sdef
        self.iden = sdef.get('iden')
        self.name = sdef.get('name')

        self.proxy = None
        self.ready = asyncio.Event()

        self.schedCoro(self._initSvcProxy())

    async def deref(self, name):
        await self.ready.wait()
        return getattr(self.proxy, name)

    async def _initSvcProxy(self):

        url = self.sdef.get('url')

        while not self.isfini:

            self.ready.clear()

            try:
                self.proxy = await s_telepath.openurl(url)

                async def fini():
                    self.proxy = None
                    self.ready.clear()
                    await self.fire('storm:svc:fini')
                    self.schedCoro(self._initSvcProxy())

                self.proxy.onfini(fini)

                self.ready.set()
                await self.fire('storm:svc:init')

                return

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.warning(f'StormService ({self.iden}) proxy failure: {e}')
                await asyncio.sleep(1)
