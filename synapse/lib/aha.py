import os
import copy
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

class AhaApi(s_cell.CellApi):

    async def getAhaUrls(self):
        return self.cell.conf.get('aha:urls', ())

    async def getAhaSvc(self, name):
        '''
        Return an AHA service description dictionary for a fully qualified service name.
        '''
        svcinfo = await self.cell.getAhaSvc(name)
        if svcinfo is None:
            return None

        svcnetw = svcinfo.get('svcnetw')
        await self._reqUserAllowed(('aha', 'service', 'get', svcnetw))
        return svcinfo

    async def getAhaSvcs(self, network=None):
        '''
        Yield AHA svcinfo dictionaries.

        Args:
            network (str): Optionally specify a network to filter on.
        '''
        if network is None:
            await self._reqUserAllowed(('aha', 'service', 'get'))
        else:
            await self._reqUserAllowed(('aha', 'service', 'get', network))

        async for info in self.cell.getAhaSvcs(network=network):
            yield info

    async def addAhaSvc(self, name, info, network=None):
        '''
        Register a service with the AHA discovery server.

        NOTE: In order for the service to remain marked "up" a caller
              must maintain the telepath link.
        '''
        svcname, svcnetw, svcfull = self.cell._nameAndNetwork(name, network)

        await self._reqUserAllowed(('aha', 'service', 'add', svcnetw, svcname))

        # dont disclose the real session...
        sess = s_common.guid(self.sess.iden)
        info['online'] = sess

        if self.link.sock is not None:
            host, port = self.link.sock.getpeername()
            urlinfo = info.get('urlinfo', {})
            urlinfo.setdefault('host', host)

        async def fini():
            if self.cell.isfini:  # pragma: no cover
                mesg = f'{self.cell.__class__.__name__} is fini. Unable to set {name}@{network} as down.'
                logger.warning(mesg)
                return

            logger.debug(f'AhaCellApi fini, tearing down [{name}]')
            coro = self.cell.setAhaSvcDown(name, sess, network=network)
            self.cell.schedCoro(coro)  # this will eventually execute or get cancelled.

        self.onfini(fini)

        return await self.cell.addAhaSvc(name, info, network=network)

    async def delAhaSvc(self, name, network=None):
        '''
        Remove an AHA service entry.
        '''
        svcname, svcnetw, svcfull = self.cell._nameAndNetwork(name, network)
        await self._reqUserAllowed(('aha', 'service', 'del', svcnetw, svcname))
        return await self.cell.delAhaSvc(name, network=network)

    async def getCaCert(self, network):

        await self._reqUserAllowed(('aha', 'ca', 'get'))
        return await self.cell.getCaCert(network)

    async def genCaCert(self, network):

        await self._reqUserAllowed(('aha', 'ca', 'gen'))
        return await self.cell.genCaCert(network)

    async def signHostCsr(self, csrtext, signas=None, sans=None):

        await self._reqUserAllowed(('aha', 'csr', 'host'))
        return await self.cell.signHostCsr(csrtext, signas=signas, sans=sans)

    async def signUserCsr(self, csrtext, signas=None):

        await self._reqUserAllowed(('aha', 'csr', 'user'))
        return await self.cell.signUserCsr(csrtext, signas=signas)

class AhaCell(s_cell.Cell):

    cellapi = AhaApi
    confbase = copy.deepcopy(s_cell.Cell.confbase)
    confbase['mirror']['hidedocs'] = False  # type: ignore
    confbase['mirror']['hidecmdl'] = False  # type: ignore
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
        self.jsonstor = await s_jsonstor.JsonStor.anit(slab, 'aha')  # type: s_jsonstor.JsonStor

        async def fini():
            await self.jsonstor.fini()
            await slab.fini()

        self.onfini(fini)

    async def initServiceRuntime(self):
        self.addActiveCoro(self._clearInactiveSessions)

        if self.isactive:
            # bootstrap a CA for our aha:network
            netw = self.conf.get('aha:network')
            if netw is not None:

                await self.genCaCert(netw)

                host = self.conf.get('aha:name')
                if host is not None:
                    await self._genHostCert(host, signas=netw)

                user = self.conf.get('aha:admin')
                if user is not None:
                    await self._genUserCert(user, signas=netw)

    async def _clearInactiveSessions(self):

        async for svc in self.getAhaSvcs():
            if svc.get('svcinfo', {}).get('online') is None:
                continue
            current_sessions = {s_common.guid(iden) for iden in self.dmon.sessions.keys()}
            svcname = svc.get('svcname')
            network = svc.get('svcnetw')
            linkiden = svc.get('svcinfo').get('online')
            if linkiden not in current_sessions:
                logger.debug(f'AhaCell activecoro tearing down [{svcname}.{network}]')
                await self.setAhaSvcDown(svcname, linkiden, network=network)

        # Wait until we are cancelled or the cell is fini.
        await self.waitfini()

    async def getAhaSvcs(self, network=None):
        path = ('aha', 'services')
        if network is not None:
            path = path + (network,)

        async for path, item in self.jsonstor.getPathObjs(path):
            yield item

    def _nameAndNetwork(self, name, network):

        if network is None:
            svcfull = name
            try:
                svcname, svcnetw = name.split('.', 1)
            except ValueError:
                raise s_exc.BadArg(name=name, arg='name',
                                   mesg='Name must contain at least one "."') from None
        else:
            svcname = name
            svcnetw = network
            svcfull = f'{name}.{network}'

        return svcname, svcnetw, svcfull

    @s_nexus.Pusher.onPushAuto('aha:svc:add')
    async def addAhaSvc(self, name, info, network=None):

        svcname, svcnetw, svcfull = self._nameAndNetwork(name, network)

        full = ('aha', 'svcfull', svcfull)
        path = ('aha', 'services', svcnetw, svcname)

        unfo = info.get('urlinfo')
        logger.debug(f'Adding service [{svcfull}] from [{unfo.get("scheme")}://{unfo.get("host")}:{unfo.get("port")}]')

        svcinfo = {
            'name': svcfull,
            'svcname': svcname,
            'svcnetw': svcnetw,
            'svcinfo': info,
        }

        await self.jsonstor.setPathObj(path, svcinfo)
        await self.jsonstor.setPathLink(full, path)

        # mostly for testing...
        await self.fire('aha:svcadd', svcinfo=svcinfo)

    @s_nexus.Pusher.onPushAuto('aha:svc:del')
    async def delAhaSvc(self, name, network=None):

        svcname, svcnetw, svcfull = self._nameAndNetwork(name, network)

        full = ('aha', 'svcfull', svcfull)
        path = ('aha', 'services', svcnetw, svcname)

        await self.jsonstor.delPathObj(path)
        await self.jsonstor.delPathObj(full)

        # mostly for testing...
        await self.fire('aha:svcdel', svcname=svcname, svcnetw=svcnetw)

    async def setAhaSvcDown(self, name, linkiden, network=None):
        svcname, svcnetw, svcfull = self._nameAndNetwork(name, network)
        path = ('aha', 'services', svcnetw, svcname)

        svcinfo = await self.jsonstor.getPathObjProp(path, 'svcinfo')
        if svcinfo.get('online') is None:
            return

        await self._push('aha:svc:down', name, linkiden, network=network)

    @s_nexus.Pusher.onPush('aha:svc:down')
    async def _setAhaSvcDown(self, name, linkiden, network=None):
        svcname, svcnetw, svcfull = self._nameAndNetwork(name, network)
        path = ('aha', 'services', svcnetw, svcname)
        await self.jsonstor.cmpDelPathObjProp(path, 'svcinfo/online', linkiden)

        # Check if we have any links which may need to be removed
        current_sessions = {s_common.guid(iden): sess for iden, sess in self.dmon.sessions.items()}
        sess = current_sessions.get(linkiden)
        if sess is not None:
            for link in [lnk for lnk in self.dmon.links if lnk.get('sess') is sess]:
                await link.fini()

        await self.fire('aha:svcdown', svcname=svcname, svcnetw=svcnetw)

        logger.debug(f'Set [{svcfull}] offline.')

    async def getAhaSvc(self, name):
        path = ('aha', 'svcfull', name)
        svcinfo = await self.jsonstor.getPathObj(path)
        if svcinfo is not None:
            return svcinfo

    async def genCaCert(self, network):

        path = self.certdir.getCaCertPath(network)
        if path is not None:
            with open(path, 'rb') as fd:
                return fd.read().decode()

        logger.info(f'Generating CA certificate for {network}')
        fut = s_coro.executor(self.certdir.genCaCert, network, save=False)
        pkey, cert = await fut

        cakey = self.certdir._pkeyToByts(pkey).decode()
        cacert = self.certdir._certToByts(cert).decode()

        # nexusify storage..
        await self.saveCaCert(network, cakey, cacert)

        return cacert

    async def _genHostCert(self, hostname, signas=None):

        if os.path.isfile(os.path.join(self.dirn, 'certs', 'hosts', '{hostname}.crt')):
            return

        pkey, cert = await s_coro.executor(self.certdir.genHostCert, hostname, signas=signas, save=False)
        pkey = self.certdir._pkeyToByts(pkey).decode()
        cert = self.certdir._certToByts(cert).decode()
        await self.saveHostCert(hostname, pkey, cert)

    async def _genUserCert(self, username, signas=None):
        if os.path.isfile(os.path.join(self.dirn, 'certs', 'users', '{username}.crt')):
            return
        pkey, cert = await s_coro.executor(self.certdir.genUserCert, username, signas=signas, save=False)
        pkey = self.certdir._pkeyToByts(pkey).decode()
        cert = self.certdir._certToByts(cert).decode()
        await self.saveUserCert(username, pkey, cert)

    async def getCaCert(self, network):

        path = self.certdir.getCaCertPath(network)
        if path is None:
            return None

        with open(path, 'rb') as fd:
            return fd.read().decode()

    @s_nexus.Pusher.onPushAuto('aha:ca:save')
    async def saveCaCert(self, name, cakey, cacert):
        with s_common.genfile(self.dirn, 'certs', 'cas', f'{name}.key') as fd:
            fd.write(cakey.encode())
        with s_common.genfile(self.dirn, 'certs', 'cas', f'{name}.crt') as fd:
            fd.write(cacert.encode())

    @s_nexus.Pusher.onPushAuto('aha:host:save')
    async def saveHostCert(self, name, hostkey, hostcert):
        with s_common.genfile(self.dirn, 'certs', 'hosts', f'{name}.key') as fd:
            fd.write(hostkey.encode())

        with s_common.genfile(self.dirn, 'certs', 'hosts', f'{name}.crt') as fd:
            fd.write(hostcert.encode())

    @s_nexus.Pusher.onPushAuto('aha:user:save')
    async def saveUserCert(self, name, userkey, usercert):
        with s_common.genfile(self.dirn, 'certs', 'users', f'{name}.key') as fd:
            fd.write(userkey.encode())

        with s_common.genfile(self.dirn, 'certs', 'users', f'{name}.crt') as fd:
            fd.write(usercert.encode())

    async def signHostCsr(self, csrtext, signas=None, sans=None):
        xcsr = self.certdir._loadCsrByts(csrtext.encode())

        hostname = xcsr.get_subject().CN

        hostpath = s_common.genpath(self.dirn, 'certs', 'hosts', f'{hostname}.crt')
        if os.path.isfile(hostpath):
            os.unlink(hostpath)

        if signas is None:
            signas = hostname.split('.', 1)[1]

        logger.info(f'Signing host CSR for [{hostname}], signas={signas}, sans={sans}')

        pkey, cert = self.certdir.signHostCsr(xcsr, signas=signas, sans=sans)

        return self.certdir._certToByts(cert).decode()

    async def signUserCsr(self, csrtext, signas=None):
        xcsr = self.certdir._loadCsrByts(csrtext.encode())

        username = xcsr.get_subject().CN

        userpath = s_common.genpath(self.dirn, 'certs', 'users', f'{username}.crt')
        if os.path.isfile(userpath):
            os.unlink(userpath)

        if signas is None:
            signas = username.split('@', 1)[1]

        logger.info(f'Signing user CSR for [{username}], signas={signas}')

        pkey, cert = self.certdir.signUserCsr(xcsr, signas=signas)

        return self.certdir._certToByts(cert).decode()
