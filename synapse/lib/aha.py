import os
import copy
import random
import logging

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

class AhaApi(s_cell.CellApi):

    async def getAhaUrls(self):
        ahaurls = self.cell._getAhaUrls()
        if ahaurls is not None:
            return ahaurls
        return()

    async def getAhaSvc(self, name, filters=None):
        '''
        Return an AHA service description dictionary for a service name.
        '''
        svcinfo = await self.cell.getAhaSvc(name, filters=filters)
        if svcinfo is None:
            return None

        svcnetw = svcinfo.get('svcnetw')
        await self._reqUserAllowed(('aha', 'service', 'get', svcnetw))

        svcinfo = s_msgpack.deepcopy(svcinfo)

        # suggest that the user of the remote service is the same
        username = self.user.name.split('@')[0]

        svcinfo['svcinfo']['urlinfo']['user'] = username

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
        info.setdefault('ready', True)

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

    async def modAhaSvcInfo(self, name, svcinfo):

        for key in svcinfo.keys():
            if key not in ('ready',):
                mesg = f'Editing AHA service info property ({key}) is not supported!'
                raise s_exc.BadArg(mesg=mesg)

        svcentry = await self.cell.getAhaSvc(name)
        if svcentry is None:
            return False

        svcnetw = svcentry.get('svcnetw')
        svcname = svcentry.get('svcname')

        await self._reqUserAllowed(('aha', 'service', 'add', svcnetw, svcname))

        return await self.cell.modAhaSvcInfo(name, svcinfo)

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

    @s_cell.adminapi()
    async def addAhaSvcProv(self, name, provinfo=None):
        '''
        Provision the given relative service name within the configured network name.
        '''
        return await self.cell.addAhaSvcProv(name, provinfo=provinfo)

    @s_cell.adminapi()
    async def delAhaSvcProv(self, iden):
        '''
        Remove a previously added provisioning entry by iden.
        '''
        return await self.cell.delAhaSvcProv(iden)

    @s_cell.adminapi()
    async def addAhaUserEnroll(self, name, userinfo=None, again=False):
        '''
        Create and return a one-time user enroll key.
        '''
        return await self.cell.addAhaUserEnroll(name, userinfo=userinfo, again=again)

    @s_cell.adminapi()
    async def delAhaUserEnroll(self, iden):
        '''
        Remove a previously added enrollment entry by iden.
        '''
        return await self.cell.delAhaUserEnroll(iden)

class ProvDmon(s_daemon.Daemon):

    async def __anit__(self, aha):
        self.aha = aha
        await s_daemon.Daemon.__anit__(self)

    async def _getSharedItem(self, name):
        provinfo = await self.aha.getAhaSvcProv(name)
        if provinfo is not None:
            await self.aha.delAhaSvcProv(name)
            return ProvApi(self.aha, provinfo)

        userinfo = await self.aha.getAhaUserEnroll(name)
        if userinfo is not None:
            await self.aha.delAhaUserEnroll(name)
            return EnrollApi(self.aha, userinfo)

class EnrollApi:

    def __init__(self, aha, userinfo):
        self.aha = aha
        self.userinfo = userinfo

    async def getUserInfo(self):
        return {
            'aha:urls': self.aha._getAhaUrls(),
            'aha:user': self.userinfo.get('name'),
            'aha:network': self.aha.conf.get('aha:network'),
        }

    async def getCaCert(self):
        ahanetw = self.aha.conf.get('aha:network')
        return self.aha.certdir.getCaCertBytes(ahanetw)

    async def signUserCsr(self, byts):

        ahauser = self.userinfo.get('name')
        ahanetw = self.aha.conf.get('aha:network')

        username = f'{ahauser}@{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        if xcsr.get_subject().CN != username:
            mesg = f'Invalid user CSR CN={xcsr.get_subject().CN}.'
            raise s_exc.BadArg(mesg=mesg)

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

class ProvApi:

    def __init__(self, aha, provinfo):
        self.aha = aha
        self.provinfo = provinfo

    async def getProvInfo(self):
        return self.provinfo

    async def getCaCert(self):
        ahanetw = self.aha.conf.get('aha:network')
        return self.aha.certdir.getCaCertBytes(ahanetw)

    async def signHostCsr(self, byts):

        ahaname = self.provinfo['conf'].get('aha:name')
        ahanetw = self.provinfo['conf'].get('aha:network')

        hostname = f'{ahaname}.{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        if xcsr.get_subject().CN != hostname:
            mesg = f'Invalid host CSR CN={xcsr.get_subject().CN}.'
            raise s_exc.BadArg(mesg=mesg)

        pkey, cert = self.aha.certdir.signHostCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

    async def signUserCsr(self, byts):

        ahauser = self.provinfo['conf'].get('aha:user')
        ahanetw = self.provinfo['conf'].get('aha:network')

        username = f'{ahauser}@{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        if xcsr.get_subject().CN != username:
            mesg = f'Invalid user CSR CN={xcsr.get_subject().CN}.'
            raise s_exc.BadArg(mesg=mesg)

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

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
        'provision:listen': {
            'description': 'A telepath URL for the AHA provisioning listener.',
            'type': ['string', 'null'],
        },
    }

    # Rename the class and remove these two overrides in 3.0.0
    @classmethod
    def getEnvPrefix(cls):
        return (f'SYN_AHA', f'SYN_{cls.__name__.upper()}', )

    async def initServiceStorage(self):

        # TODO plumb using a remote jsonstor?
        dirn = s_common.gendir(self.dirn, 'slabs', 'jsonstor')

        slab = await s_lmdbslab.Slab.anit(dirn)
        self.jsonstor = await s_jsonstor.JsonStor.anit(slab, 'aha')  # type: s_jsonstor.JsonStor

        async def fini():
            await self.jsonstor.fini()
            await slab.fini()

        self.onfini(fini)

        self.slab.initdb('aha:provs')
        self.slab.initdb('aha:enrolls')

    async def initServiceRuntime(self):
        self.addActiveCoro(self._clearInactiveSessions)

        if self.isactive:
            # bootstrap a CA for our aha:network
            netw = self.conf.get('aha:network')
            if netw is not None:

                if self.certdir.getCaCertPath(netw) is None:
                    await self.genCaCert(netw)

                name = self.conf.get('aha:name')

                host = f'{name}.{netw}'
                if self.certdir.getHostCertPath(host) is None:
                    await self._genHostCert(host, signas=netw)

                user = self._getAhaAdmin()
                if user is not None:
                    if self.certdir.getUserCertPath(user) is None:
                        await self._genUserCert(user, signas=netw)

    async def initServiceNetwork(self):

        await s_cell.Cell.initServiceNetwork(self)

        self.provdmon = None

        provurl = self.conf.get('provision:listen')
        if provurl is not None:
            self.provdmon = await ProvDmon.anit(self)
            self.onfini(self.provdmon)
            await self.provdmon.listen(provurl)

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

    @s_nexus.Pusher.onPushAuto('aha:svc:mod')
    async def modAhaSvcInfo(self, name, svcinfo):

        svcentry = await self.getAhaSvc(name)
        if svcentry is None:
            return False

        svcnetw = svcentry.get('svcnetw')
        svcname = svcentry.get('svcname')

        path = ('aha', 'services', svcnetw, svcname)

        for prop, valu in svcinfo.items():
            await self.jsonstor.setPathObjProp(path, ('svcinfo', prop), valu)
        return True

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

    async def getAhaSvc(self, name, filters=None):

        if name.endswith('...'):
            ahanetw = self.conf.get('aha:network')
            if ahanetw is None:
                mesg = f'Relative service name ({name}) can not be resolved without aha:network set.'
                raise s_exc.BadArg(mesg=mesg)

            name = f'{name[:-2]}{ahanetw}'

        path = ('aha', 'svcfull', name)
        svcentry = await self.jsonstor.getPathObj(path)
        if svcentry is None:
            return None

        # if they requested a mirror, try to locate one
        if filters is not None and filters.get('mirror'):
            ahanetw = svcentry.get('ahanetw')
            svcinfo = svcentry.get('svcinfo')
            if svcinfo is None: # pragma: no cover
                return svcentry

            celliden = svcinfo.get('iden')
            mirrors = await self.getAhaSvcMirrors(celliden, network=ahanetw)

            if mirrors:
                return random.choice(mirrors)

        return svcentry

    async def getAhaSvcMirrors(self, iden, network=None):

        retn = {}
        skip = None

        async for svcentry in self.getAhaSvcs(network=network):

            svcinfo = svcentry.get('svcinfo')
            if svcinfo is None: # pragma: no cover
                continue

            if svcinfo.get('iden') != iden: # pragma: no cover
                continue

            if svcinfo.get('online') is None: # pragma: no cover
                continue

            if not svcinfo.get('ready'):
                continue

            # if we run across the leader, skip ( and mark his run )
            if svcentry.get('svcname') == svcinfo.get('leader'):
                skip = svcinfo.get('run')
                continue

            retn[svcinfo.get('run')] = svcentry

        if skip is not None:
            retn.pop(skip, None)

        return list(retn.values())

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

    def _getAhaUrls(self):
        urls = self.conf.get('aha:urls')
        if urls is not None:
            return urls

        ahaname = self.conf.get('aha:name')
        if ahaname is None:
            return None

        ahanetw = self.conf.get('aha:network')
        if ahanetw is None:
            return None

        # TODO this could eventually enumerate others via itself
        return f'ssl://{ahaname}.{ahanetw}'

    async def addAhaSvcProv(self, name, provinfo=None):

        ahaurls = self._getAhaUrls()
        if ahaurls is None:
            mesg = 'AHA server has no configured aha:urls.'
            raise s_exc.NeedConfValu(mesg=mesg)

        if self.conf.get('provision:listen') is None:
            mesg = 'The AHA server does not have a provision:listen URL!'
            raise s_exc.NeedConfValu(mesg=mesg)

        if provinfo is None:
            provinfo = {}

        iden = s_common.guid()

        provinfo['iden'] = iden

        conf = provinfo.setdefault('conf', {})

        mynetw = self.conf.get('aha:network')

        ahaadmin = self.conf.get('aha:admin')
        if ahaadmin is not None: # pragma: no cover
            conf.setdefault('aha:admin', ahaadmin)

        conf.setdefault('aha:user', 'root')
        conf.setdefault('aha:network', mynetw)

        netw = conf.get('aha:network')
        if netw is None:
            mesg = 'AHA server has no configured aha:network.'
            raise s_exc.NeedConfValu(mesg=mesg)

        hostname = f'{name}.{netw}'

        conf.setdefault('aha:name', name)
        conf.setdefault('dmon:listen', f'ssl://0.0.0.0:0?hostname={hostname}&ca={netw}')

        # if the relative name contains a dot, we are a mirror peer.
        peer = name.find('.') != -1
        leader = name.rsplit('.', 1)[-1]

        if peer:
            conf.setdefault('aha:leader', leader)

        if isinstance(ahaurls, str):
            ahaurls = (ahaurls,)

        # allow user to win over leader
        ahauser = conf.get('aha:user')
        ahaurls = s_telepath.modurl(ahaurls, user=ahauser)

        conf.setdefault('aha:registry', ahaurls)

        mirname = provinfo.get('mirror')
        if mirname is not None:
            conf['mirror'] = f'aha://{ahauser}@{mirname}.{netw}'

        username = f'{ahauser}@{netw}'
        user = await self.auth.getUserByName(username)
        if user is None:
            user = await self.auth.addUser(username)

        await user.allow(('aha', 'service', 'get', netw))
        await user.allow(('aha', 'service', 'add', netw, name))
        if peer:
            await user.allow(('aha', 'service', 'add', netw, leader))

        iden = await self._push('aha:svc:prov:add', provinfo)

        logger.debug(f'Created provisioning for {name}.{netw}')

        return self._getProvClientUrl(iden)

    def _getProvClientUrl(self, iden):

        provlisn = self.conf.get('provision:listen')

        urlinfo = s_telepath.chopurl(provlisn)

        host = urlinfo.get('hostname')
        scheme = urlinfo.get('scheme')

        if host is None:
            host = urlinfo.get('host')

        newinfo = {
            'host': host,
            'port': urlinfo.get('port'),
            'scheme': scheme,
            'path': '/' + iden,
        }

        if scheme == 'ssl':
            certhash = self.certdir.getHostCertHash(host)
            if certhash is not None:
                newinfo['certhash'] = certhash

        return s_telepath.zipurl(newinfo)

    async def getAhaSvcProv(self, iden):
        byts = self.slab.get(iden.encode(), db='aha:provs')
        if byts is not None:
            return s_msgpack.un(byts)

    @s_nexus.Pusher.onPush('aha:svc:prov:add')
    async def _addAhaSvcProv(self, provinfo):
        iden = provinfo.get('iden')
        self.slab.put(iden.encode(), s_msgpack.en(provinfo), db='aha:provs')
        return iden

    @s_nexus.Pusher.onPushAuto('aha:svc:prov:del')
    async def delAhaSvcProv(self, iden):
        self.slab.delete(iden.encode(), db='aha:provs')

    async def addAhaUserEnroll(self, name, userinfo=None, again=False):

        provurl = self.conf.get('provision:listen')
        if provurl is None:
            mesg = 'The AHA server does not have a provision:listen URL!'
            raise s_exc.NeedConfValu(mesg=mesg)

        ahanetw = self.conf.get('aha:network')
        if ahanetw is None:
            mesg = 'AHA server requires aha:network configuration.'
            raise s_exc.NeedConfValu(mesg=mesg)

        username = f'{name}@{ahanetw}'

        user = await self.auth.getUserByName(username)

        if user is not None:
            if not again:
                mesg = f'User name ({name}) already exists.  Need --again?'
                raise s_exc.DupUserName(mesg=mesg)

        if user is None:
            user = await self.auth.addUser(username)

        await user.allow(('aha', 'service', 'get', ahanetw))

        userinfo = {
            'name': name,
            'iden': s_common.guid(),
        }

        iden = await self._push('aha:enroll:add', userinfo)
        return self._getProvClientUrl(iden)

    async def getAhaUserEnroll(self, iden):
        byts = self.slab.get(iden.encode(), db='aha:enrolls')
        if byts is not None:
            return s_msgpack.un(byts)

    @s_nexus.Pusher.onPush('aha:enroll:add')
    async def _addAhaUserEnroll(self, userinfo):
        iden = userinfo.get('iden')
        self.slab.put(iden.encode(), s_msgpack.en(userinfo), db='aha:enrolls')
        return iden

    @s_nexus.Pusher.onPushAuto('aha:enroll:del')
    async def delAhaUserEnroll(self, iden):
        self.slab.delete(iden.encode(), db='aha:enrolls')
