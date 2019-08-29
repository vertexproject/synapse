import asyncio
import logging

import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

class StormSvc:

    _storm_svc_name = 'noname'
    _storm_svc_vers = (0, 0, 1)
    _storm_svc_cmds = ()

    async def getStormSvcInfo(self):
        return {
            'name': self._storm_svc_name,
            'vers': self._storm_svc_vers,
            'cmds': await self.getStormSvcCmds(),
        }

    async def getStormSvcCmds(self):
        return self._storm_svc_cmds

class StormSvcClient(s_base.Base, s_stormtypes.StormType):
    '''
    A StormService is a wrapper for a telepath proxy to a service
    accessible from the storm runtime.
    '''
    async def __anit__(self, core, sdef):

        await s_base.Base.__anit__(self)
        s_stormtypes.StormType.__init__(self)

        self.core = core
        self.sdef = sdef

        self.iden = sdef.get('iden')
        self.name = sdef.get('name')

        self.proxy = None
        self.ready = asyncio.Event()

        # service info from the server...
        self.info = None

        self.schedCoro(self._initSvcProxy())

    async def _initStormCmds(self):

        clss = self.proxy.sharinfo.get('classes', ())

        names = [c.rsplit('.', 1)[-1] for c in clss]
        if 'StormSvc' not in names:
            return

        self.info = await self.proxy.getStormSvcInfo()

        for cdef in self.info.get('cmds', ()):

            cdef.setdefault('cmdconf', {})

            try:
                cdef['cmdconf']['svc'] = self
                await self.core.setStormCmd(cdef)

            except asyncio.CancelledError:
                raise

            except Exception as e:
                name = cdef.get('name')
                logger.warning(f'setStormCmd ({name}) failed for service {self.name} ({self.iden})')

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

                await self._initStormCmds()

                self.ready.set()

                await self.fire('storm:svc:init')

                return

            except asyncio.CancelledError:
                raise

            except Exception as e:
                logger.warning(f'StormService ({self.iden}) proxy failure: {e}')
                await asyncio.sleep(1)
