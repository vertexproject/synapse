import os
import logging

import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.nexus as s_nexus
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__file__)

class AhaApi(s_cell.CellApi):

    async def getAhaUrls(self):
        return self.cell.conf.get('aha:urls', ())

    async def getAhaSvc(self, name):
        svcname, network = name.split('.', 1)
        await self._reqUserAllowed(('aha', 'service', 'get', network))
        return await self.cell.getAhaSvc(name)

    async def getAhaSvcs(self, network):
        await self._reqUserAllowed(('aha', 'service', 'get', network))
        async for info in self.cell.getAhaSvcs(network=network):
            yield info

    async def addAhaSvc(self, name, info):

        svcname, network = name.split('.', 1)
        await self._reqUserAllowed(('aha', 'service', 'add', network, svcname))

        # dont disclose the real session...
        sess = s_common.guid(self.sess.iden)
        info['online'] = sess

        if self.link.sock is not None:
            host, port = self.link.sock.getpeername()
            urlinfo = info.get('urlinfo', {})
            urlinfo.setdefault('host', host)

        async def fini():
            await self.cell.setAhaSvcDown(name, sess)

        self.onfini(fini)

        return await self.cell.addAhaSvc(name, info)

    async def getCaCert(self, network):

        await self._reqUserAllowed(('aha', 'ca', 'get'))
        path = self.cell.certdir.getCaCertPath(network)
        if path is None:
            return None

        with open(path, 'rb') as fd:
            return fd.read().decode()

    async def genCaCert(self, network):

        await self._reqUserAllowed(('aha', 'ca', 'gen'))

        path = self.cell.certdir.getCaCertPath(network)
        if path is not None:
            with open(path, 'rb') as fd:
                return fd.read().decode()

        return await self.cell.genCaCert(network)

    async def signHostCsr(self, csrtext, signas=None):

        xcsr = self.cell.certdir._loadCsrByts(csrtext.encode())

        hostname = xcsr.get_subject().CN

        hostpath = s_common.genpath(self.cell.dirn, 'certs', 'hosts', f'{hostname}.crt')
        if os.path.isfile(hostpath):
            os.unlink(hostpath)

        if signas is None:
            signas = hostname.split('.', 1)[1]

        pkey, cert = self.cell.certdir.signHostCsr(xcsr, signas=signas)

        return self.cell.certdir._certToByts(cert).decode()

    async def signUserCsr(self, csrtext, signas=None):

        xcsr = self.cell.certdir._loadCsrByts(csrtext.encode())

        username = xcsr.get_subject().CN

        userpath = s_common.genpath(self.cell.dirn, 'certs', 'users', f'{username}.crt')
        if os.path.isfile(userpath):
            os.unlink(userpath)

        if signas is None:
            signas = username.split('@', 1)[1]

        pkey, cert = self.cell.certdir.signUserCsr(xcsr, signas=signas)

        return self.cell.certdir._certToByts(cert).decode()

class AhaCell(s_cell.Cell):

    cellapi = AhaApi
    confdefs = {
        'aha:urls': {
            'description': 'A list of all available AHA server URLs.',
            'type': ['string', 'array'],
            'items': {'type': 'string'},
        },
    }

    async def initServiceStorage(self):

        # TODO plumb using a remote jsonstor?
        dirn = s_common.gendir(self.dirn, 'slabs', 'jsonstor')

        slab = await s_lmdbslab.Slab.anit(dirn)
        self.jsonstor = await s_jsonstor.JsonStor.anit(slab, 'aha')

        async def fini():
            await self.jsonstor.fini()
            await slab.fini()

        self.onfini(fini)

    async def getAhaSvcs(self, network):
        path = ('aha', 'services', network)
        async for path, item in self.jsonstor.getPathObjs(path):
            yield item

    @s_nexus.Pusher.onPushAuto('aha:svc:add')
    async def addAhaSvc(self, name, info):

        logger.info('addAhaSvc %r %r' % (name, info))

        svcname, network = name.split('.', 1)
        path = ('aha', 'services', network, svcname)

        svcinfo = {
            'name': name,
            'svcinfo': info,
        }

        await self.jsonstor.setPathObj(path, svcinfo)

        # mostly for testing...
        await self.fire('aha:svcadd', svcinfo=svcinfo)

    @s_nexus.Pusher.onPushAuto('aha:svc:down')
    async def setAhaSvcDown(self, name, linkiden):
        svcname, network = name.split('.', 1)
        path = ('aha', 'services', network, svcname)
        await self.jsonstor.cmpDelPathObjProp(path, 'svcinfo/online', linkiden)

    async def getAhaSvc(self, name):
        svcname, network = name.split('.', 1)
        path = ('aha', 'services', network, svcname)
        return await self.jsonstor.getPathObj(path)

    async def genCaCert(self, network):

        # TODO executor threads for cert gen
        pkey, cert = self.certdir.genCaCert(network, save=False)

        cakey = self.certdir._pkeyToByts(pkey).decode()
        cacert = self.certdir._certToByts(cert).decode()

        # nexusify storage..
        await self.saveCaCert(network, cakey, cacert)

        return cacert

    @s_nexus.Pusher.onPushAuto('aha:ca:save')
    async def saveCaCert(self, name, cakey, cacert):
        # manually save the files to a certpath compatible location
        with s_common.genfile(self.dirn, 'certs', 'cas', f'{name}.key') as fd:
            fd.write(cakey.encode())
        with s_common.genfile(self.dirn, 'certs', 'cas', f'{name}.crt') as fd:
            fd.write(cacert.encode())
