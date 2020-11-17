import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.nexus as s_nexus
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab

class AhaApi(s_cell.CellApi):

    async def getAhaSvc(self, name, network='global'):
        await self._reqUserAllowed(('aha', 'service', 'get', network))
        return await self.cell.getAhaSvc(name, network=network)

    async def getAhaSvcs(self, network='global'):
        await self._reqUserAllowed(('aha', 'service', 'get', network))
        async for info in self.cell.getAhaSvcs(network=network):
            yield info

    async def addAhaSvc(self, name, info, network='global'):
        await self._reqUserAllowed(('aha', 'service', 'add', network, name))

        if self.link.sock is not None:
            host, port = self.link.sock.getpeername()
            info.setdefault('host', host)

        return await self.cell.addAhaSvc(name, info, network=network)

class AhaCell(s_cell.Cell):

    cellapi = AhaApi

    async def initServiceStorage(self):

        # TODO plumb using a remote jsonstor?
        dirn = s_common.gendir(self.dirn, 'slabs', 'jsonstor')

        slab = await s_lmdbslab.Slab.anit(dirn)
        self.jsonstor = await s_jsonstor.JsonStor.anit(slab, 'aha')

        async def fini():
            await self.jsonstor.fini()
            await slab.fini()

        self.onfini(fini)

    async def getAhaSvcs(self, network='global'):
        path = ('aha', 'services', network)
        async for path, item in self.jsonstor.getPathObjs(path):
            yield item

    @s_nexus.Pusher.onPushAuto('aha:svc:add')
    async def addAhaSvc(self, name, info, network='global'):
        path = ('aha', 'services', network, name)

        svcinfo = {
            'name': name,
            'urlinfo': info,
        }

        await self.jsonstor.setPathObj(path, svcinfo)

        # mostly for testing...
        await self.fire('aha:svcadd', svcinfo=svcinfo)

    async def getAhaSvc(self, name, network='global'):
        path = ('aha', 'services', network, name)
        return await self.jsonstor.getPathObj(path)
