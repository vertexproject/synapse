import os
import copy
import random
import asyncio
import logging
import collections

import cryptography.x509 as c_x509

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.nexus as s_nexus
import synapse.lib.queue as s_queue
import synapse.lib.config as s_config
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

_provSvcSchema = {
    'type': 'object',
    'properties': {
        'name': {
            'type': 'string',
            'minLength': 1,
        },
        'provinfo': {
            'type': 'object',
            'properties': {
                'conf': {
                    'type': 'object',
                },
                'dmon:port': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 65535,
                },
                'https:port': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 65535,
                },
                'mirror': {
                    'type': 'string',
                    'minLength': 1,
                },
            }
        }
    },
    'additionalProperties': False,
    'required': ['name'],
}
provSvcSchema = s_config.getJsValidator(_provSvcSchema)


class AhaProvisionServiceV1(s_httpapi.Handler):

    async def post(self):
        if not await self.reqAuthAdmin():
            return

        body = self.getJsonBody(validator=provSvcSchema)
        if body is None:
            return

        name = body.get('name')
        provinfo = body.get('provinfo')

        try:
            url = await self.cell.addAhaSvcProv(name, provinfo=provinfo)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            logger.exception(f'Error provisioning {name}')
            return self.sendRestExc(e, status_code=s_httpapi.HTTPStatus.BAD_REQUEST)
        return self.sendRestRetn({'url': url})

_getAhaSvcSchema = {
    'type': 'object',
    'properties': {
        'network': {
            'type': 'string',
            'minLength': 1,
            'default': None,
        },
    },
    'additionalProperties': False,
}
getAhaScvSchema = s_config.getJsValidator(_getAhaSvcSchema)

class AhaServicesV1(s_httpapi.Handler):
    async def get(self):
        if not await self.reqAuthAdmin():
            return

        network = None
        if self.request.body:
            body = self.getJsonBody(validator=getAhaScvSchema)
            if body is None:
                return
            network = body.get('network')

        ret = []

        try:
            async for info in self.cell.getAhaSvcs(network=network):
                ret.append(info)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:  # pragma: no cover
            logger.exception(f'Error getting Aha services.')
            return self.sendRestErr(e.__class__.__name__, str(e))
        return self.sendRestRetn(ret)

class AhaApi(s_cell.CellApi):

    @s_cell.adminapi()
    async def addAhaClone(self, host, port=27492, conf=None):
        return await self.cell.addAhaClone(host, port=port, conf=conf)

    async def getAhaUrls(self, user='root'):
        ahaurls = await self.cell.getAhaUrls(user=user)
        return ahaurls

    @s_cell.adminapi()
    async def callAhaPeerApi(self, iden, todo, timeout=None, skiprun=None):
        async for item in self.cell.callAhaPeerApi(iden, todo, timeout=timeout, skiprun=skiprun):
            yield item

    @s_cell.adminapi()
    async def callAhaPeerGenr(self, iden, todo, timeout=None, skiprun=None):
        async for item in self.cell.callAhaPeerGenr(iden, todo, timeout=timeout, skiprun=skiprun):
            yield item

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

        if svcinfo.get('svcinfo'):
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
            s_common.deprecated('getAhaSvcs() network argument', curv='v2.206.0')
            await self._reqUserAllowed(('aha', 'service', 'get', network))

        async for info in self.cell.getAhaSvcs(network=network):
            yield info

    async def addAhaSvc(self, name, info, network=None):
        '''
        Register a service with the AHA discovery server.

        NOTE: In order for the service to remain marked "up" a caller
              must maintain the telepath link.
        '''
        if network is not None:
            s_common.deprecated('addAhaSvc() network argument', curv='v2.206.0')
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
                logger.warning(mesg, await self.cell.getLogExtra(name=svcname, netw=svcnetw))
                return

            logger.info(f'AhaCellApi fini, setting service offline [{name}]',
                         extra=await self.cell.getLogExtra(name=svcname, netw=svcnetw))
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

    async def getAhaSvcMirrors(self, name):
        '''
        Return list of AHA svcinfo dictionaries for mirrors of a service.
        '''
        svcinfo = await self.cell.getAhaSvc(name)
        if svcinfo is None:
            return None

        svcnetw = svcinfo.get('svcnetw')
        await self._reqUserAllowed(('aha', 'service', 'get', svcnetw))

        svciden = svcinfo['svcinfo']['iden']

        return await self.cell.getAhaSvcMirrors(svciden)

    async def delAhaSvc(self, name, network=None):
        '''
        Remove an AHA service entry.
        '''
        if network is not None:
            s_common.deprecated('delAhaSvc() network argument', curv='v2.206.0')
        svcname, svcnetw, svcfull = self.cell._nameAndNetwork(name, network)
        await self._reqUserAllowed(('aha', 'service', 'del', svcnetw, svcname))
        return await self.cell.delAhaSvc(name, network=network)

    async def getCaCert(self, network):
        s_common.deprecated('getCaCert() will no longer accept a network argument', curv='v2.206.0')
        await self._reqUserAllowed(('aha', 'ca', 'get'))
        return await self.cell.getCaCert(network)

    async def genCaCert(self, network):
        s_common.deprecated('genCaCert()', curv='v2.206.0')
        await self._reqUserAllowed(('aha', 'ca', 'gen'))
        return await self.cell.genCaCert(network)

    async def signHostCsr(self, csrtext, signas=None, sans=None):
        if signas is not None:
            s_common.deprecated('signHostCsr() signas argument', curv='v2.206.0')
        await self._reqUserAllowed(('aha', 'csr', 'host'))
        return await self.cell.signHostCsr(csrtext, signas=signas, sans=sans)

    async def signUserCsr(self, csrtext, signas=None):
        if signas is not None:
            s_common.deprecated('signUserCsr() signas argument', curv='v2.206.0')
        await self._reqUserAllowed(('aha', 'csr', 'user'))
        return await self.cell.signUserCsr(csrtext, signas=signas)

    @s_cell.adminapi()
    async def addAhaPool(self, name, info):
        return await self.cell.addAhaPool(name, info)

    @s_cell.adminapi()
    async def delAhaPool(self, name):
        return await self.cell.delAhaPool(name)

    @s_cell.adminapi()
    async def addAhaPoolSvc(self, poolname, svcname, info):
        return await self.cell.addAhaPoolSvc(poolname, svcname, info)

    @s_cell.adminapi()
    async def delAhaPoolSvc(self, poolname, svcname):
        return await self.cell.delAhaPoolSvc(poolname, svcname)

    async def iterPoolTopo(self, name):

        username = self.user.name.split('@')[0]

        async for item in self.cell.iterPoolTopo(name):

            # default to using the same username as we do for aha
            if item[0] == 'svc:add':
                item[1]['svcinfo']['urlinfo']['user'] = username

            yield item

    async def getAhaPool(self, name):
        return await self.cell.getAhaPool(name)

    async def getAhaPools(self):
        async for item in self.cell.getAhaPools():
            yield item

    async def getAhaServers(self):
        return await self.cell.getAhaServers()

    async def getAhaServer(self, host, port):
        return await self.cell.getAhaServer(host, port)

    @s_cell.adminapi()
    async def addAhaServer(self, server):
        return await self.cell.addAhaServer(server)

    @s_cell.adminapi()
    async def delAhaServer(self, host, port):
        return await self.cell.delAhaServer(host, port)

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

    @s_cell.adminapi()
    async def clearAhaSvcProvs(self):
        '''
        Remove all unused service provisioning values.
        '''
        return await self.cell.clearAhaSvcProvs()

    @s_cell.adminapi()
    async def clearAhaUserEnrolls(self):
        '''
        Remove all unused user enrollment provisioning values.
        '''
        return await self.cell.clearAhaUserEnrolls()

    @s_cell.adminapi()
    async def clearAhaClones(self):
        '''
        Remove all unused AHA clone provisioning values.
        '''
        return await self.cell.clearAhaClones()

class ProvDmon(s_daemon.Daemon):

    async def __anit__(self, aha):
        self.aha = aha
        await s_daemon.Daemon.__anit__(self)

    async def _getSharedItem(self, name):
        provinfo = await self.aha.getAhaSvcProv(name)
        if provinfo is not None:
            await self.aha.delAhaSvcProv(name)
            conf = provinfo.get('conf', {})
            anam = conf.get('aha:name')
            anet = conf.get('aha:network')
            mesg = f'Retrieved service provisioning info for {anam}.{anet} iden {name}'
            logger.info(mesg, extra=await self.aha.getLogExtra(iden=name, name=anam, netw=anet))
            return ProvApi(self.aha, provinfo)

        userinfo = await self.aha.getAhaUserEnroll(name)
        if userinfo is not None:
            unam = userinfo.get('name')
            mesg = f'Retrieved user provisioning info for {unam} iden {name}'
            logger.info(mesg, extra=await self.aha.getLogExtra(iden=name, name=unam))
            await self.aha.delAhaUserEnroll(name)
            return EnrollApi(self.aha, userinfo)

        clone = await self.aha.getAhaClone(name)
        if clone is not None:
            host = clone.get('host')
            mesg = f'Retrieved AHA clone info for {host} iden {name}'
            logger.info(mesg, extra=await self.aha.getLogExtra(iden=name, host=host))
            return CloneApi(self.aha, clone)

        mesg = f'Invalid provisioning identifier name={name}. This could be' \
               f' caused by the re-use of a provisioning URL.'
        raise s_exc.NoSuchName(mesg=mesg, name=name)

class CloneApi:

    def __init__(self, aha, clone):
        self.aha = aha
        self.clone = clone

    async def getCloneDef(self):
        return self.clone

    async def readyToMirror(self):
        return await self.aha.readyToMirror()

    async def iterNewBackupArchive(self, name=None, remove=False):
        async with self.aha.getLocalProxy() as proxy:
            async for byts in proxy.iterNewBackupArchive(name=name, remove=remove):
                yield byts

class EnrollApi:

    def __init__(self, aha, userinfo):
        self.aha = aha
        self.userinfo = userinfo

    async def getUserInfo(self):
        user = self.userinfo.get('name')
        return {
            'aha:urls': await self.aha.getAhaUrls(user=user),
            'aha:user': user,
            'aha:network': self.aha.conf.req('aha:network'),
        }

    async def getCaCert(self):
        ahanetw = self.aha.conf.req('aha:network')
        return self.aha.certdir.getCaCertBytes(ahanetw)

    async def signUserCsr(self, byts):

        ahauser = self.userinfo.get('name')
        ahanetw = self.aha.conf.req('aha:network')

        username = f'{ahauser}@{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != username:
            mesg = f'Invalid user CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing user CSR for [{username}], signas={ahanetw}',
                   extra=await self.aha.getLogExtra(name=username, signas=ahanetw))

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

class ProvApi:

    def __init__(self, aha, provinfo):
        self.aha = aha
        self.provinfo = provinfo

    async def getProvInfo(self):
        return self.provinfo

    async def getCaCert(self):
        ahanetw = self.aha.conf.req('aha:network')
        return self.aha.certdir.getCaCertBytes(ahanetw)

    async def signHostCsr(self, byts):

        ahaname = self.provinfo['conf'].get('aha:name')
        ahanetw = self.provinfo['conf'].get('aha:network')

        hostname = f'{ahaname}.{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != hostname:
            mesg = f'Invalid host CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing host CSR for [{hostname}], signas={ahanetw}',
                    extra=await self.aha.getLogExtra(name=hostname, signas=ahanetw))

        pkey, cert = self.aha.certdir.signHostCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

    async def signUserCsr(self, byts):

        ahauser = self.provinfo['conf'].get('aha:user')
        ahanetw = self.provinfo['conf'].get('aha:network')

        username = f'{ahauser}@{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != username:
            mesg = f'Invalid user CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing user CSR for [{username}], signas={ahanetw}',
                    extra=await self.aha.getLogExtra(name=username, signas=ahanetw))

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

class AhaCell(s_cell.Cell):

    cellapi = AhaApi
    confbase = copy.deepcopy(s_cell.Cell.confbase)
    confbase['mirror']['hidedocs'] = False  # type: ignore
    confbase['mirror']['hidecmdl'] = False  # type: ignore
    confdefs = {
        'clone': {
            'hidecmdl': True,
            'description': 'Bootstrap a clone from the AHA clone URL.',
            'type': ['string', 'null'],
        },
        'dns:name': {
            'description': 'The registered DNS name used to reach the AHA service.',
            'type': ['string', 'null'],
        },
        'aha:urls': {
            'description': 'Deprecated. AHA servers can now manage this automatically.',
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

    async def _initCellBoot(self):

        curl = self.conf.get('clone')
        if curl is None:
            return

        path = s_common.genpath(self.dirn, 'cell.guid')
        if os.path.isfile(path):
            logger.info('Cloning AHA: cell.guid detected. Skipping.')
            return

        logger.warning(f'Cloning AHA: {curl}')

        async with await s_telepath.openurl(curl) as proxy:
            clone = await proxy.getCloneDef()
            await self._initCloneCell(proxy)

        logger.warning('Cloning AHA: done!')

        conf = s_common.yamlload(self.dirn, 'cell.yaml')
        if conf is None:
            conf = {}

        conf.update(clone.get('conf', {}))

        s_common.yamlsave(conf, self.dirn, 'cell.yaml')

        self.conf.update(conf)

    async def initServiceStorage(self):

        self.features['callpeers'] = 1

        dirn = s_common.gendir(self.dirn, 'slabs', 'jsonstor')

        slab = await s_lmdbslab.Slab.anit(dirn)
        slab.addResizeCallback(self.checkFreeSpace)

        self.jsonstor = await s_jsonstor.JsonStor.anit(slab, 'aha')  # type: s_jsonstor.JsonStor

        async def fini():
            await self.jsonstor.fini()
            await slab.fini()

        self.onfini(fini)

        self.slab.initdb('aha:provs')
        self.slab.initdb('aha:enrolls')

        self.slab.initdb('aha:clones')
        self.slab.initdb('aha:servers')

        self.slab.initdb('aha:pools')

        self.poolwindows = collections.defaultdict(list)

    async def getAhaServer(self, host, port):
        lkey = s_msgpack.en((host, port))
        byts = self.slab.get(lkey, db='aha:servers')
        if byts is not None:
            return s_msgpack.un(byts)

    async def addAhaServer(self, server):

        host = server.get('host')
        port = server.setdefault('port', 27492)

        # avoid a noop nexus change...
        oldv = await self.getAhaServer(host, port)
        if s_common.flatten(server) == s_common.flatten(oldv):
            return False

        return await self._push('aha:server:add', server)

    @s_nexus.Pusher.onPush('aha:server:add')
    async def _addAhaServer(self, server):
        # TODO schema
        host = server.get('host')
        port = server.get('port')

        lkey = s_msgpack.en((host, port))

        byts = self.slab.get(lkey, db='aha:servers')
        if byts is not None:
            oldv = s_msgpack.un(byts)
            if s_common.flatten(server) == s_common.flatten(oldv):
                return False

        self.slab.put(lkey, s_msgpack.en(server), db='aha:servers')

        return True

    @s_nexus.Pusher.onPushAuto('aha:server:del')
    async def delAhaServer(self, host, port):

        lkey = s_msgpack.en((host, port))

        byts = self.slab.pop(lkey, db='aha:servers')
        if byts is None:
            return None

        return s_msgpack.un(byts)

    async def getAhaServers(self):
        servers = []
        for _, byts in self.slab.scanByFull(db='aha:servers'):
            servers.append(s_msgpack.un(byts))
        return servers

    async def iterPoolTopo(self, name):

        name = self._getAhaName(name)

        async with await s_queue.Window.anit(maxsize=1000) as wind:

            poolinfo = self._reqPoolInfo(name)

            # pre-load the current state
            for svcname in poolinfo.get('services'):

                svcitem = await self.jsonstor.getPathObj(('aha', 'svcfull', svcname))
                if not svcitem:
                    logger.warning(f'Pool ({name}) includes service ({svcname}) which does not exist.')
                    continue

                await wind.put(('svc:add', svcitem))

            # subscribe to changes
            self.poolwindows[name].append(wind)
            async def onfini():
                self.poolwindows[name].remove(wind)

            wind.onfini(onfini)

            # iterate events...
            async for mesg in wind:
                yield mesg

    def _initCellHttpApis(self):
        s_cell.Cell._initCellHttpApis(self)
        self.addHttpApi('/api/v1/aha/services', AhaServicesV1, {'cell': self})
        self.addHttpApi('/api/v1/aha/provision/service', AhaProvisionServiceV1, {'cell': self})

    async def callAhaSvcApi(self, name, todo, timeout=None):
        name = self._getAhaName(name)
        svcdef = await self._getAhaSvc(name)
        return self._callAhaSvcApi(svcdef, todo, timeout=timeout)

    async def _callAhaSvcApi(self, svcdef, todo, timeout=None):
        try:
            proxy = await self.getAhaSvcProxy(svcdef, timeout=timeout)
            meth = getattr(proxy, todo[0])
            return await s_common.waitretn(meth(*todo[1], **todo[2]), timeout=timeout)
        except Exception as e:
            # in case proxy construction fails
            return (False, s_common.excinfo(e))

    async def _callAhaSvcGenr(self, svcdef, todo, timeout=None):
        try:
            proxy = await self.getAhaSvcProxy(svcdef, timeout=timeout)
            meth = getattr(proxy, todo[0])
            async for item in s_common.waitgenr(meth(*todo[1], **todo[2]), timeout=timeout):
                yield item
        except Exception as e:
            # in case proxy construction fails
            yield (False, s_common.excinfo(e))

    async def getAhaSvcsByIden(self, iden, online=True, skiprun=None):

        runs = set()
        async for svcdef in self.getAhaSvcs():
            await asyncio.sleep(0)

            # TODO services by iden indexes (SYN-8467)
            if svcdef['svcinfo'].get('iden') != iden:
                continue

            if online and svcdef['svcinfo'].get('online') is None:
                continue

            svcrun = svcdef['svcinfo'].get('run')
            if svcrun in runs:
                continue

            if skiprun == svcrun:
                continue

            runs.add(svcrun)
            yield svcdef

    def getAhaSvcUrl(self, svcdef, user='root'):
        svcfull = svcdef.get('name')
        svcnetw = svcdef.get('svcnetw')
        host = svcdef['svcinfo']['urlinfo']['host']
        port = svcdef['svcinfo']['urlinfo']['port']
        return f'ssl://{host}:{port}?hostname={svcfull}&certname={user}@{svcnetw}'

    async def callAhaPeerApi(self, iden, todo, timeout=None, skiprun=None):

        if not self.isactive:
            proxy = await self.nexsroot.client.proxy(timeout=timeout)
            async for item in proxy.callAhaPeerApi(iden, todo, timeout=timeout, skiprun=skiprun):
                yield item

        queue = asyncio.Queue()
        async with await s_base.Base.anit() as base:

            async def call(svcdef):
                svcfull = svcdef.get('name')
                await queue.put((svcfull, await self._callAhaSvcApi(svcdef, todo, timeout=timeout)))

            count = 0
            async for svcdef in self.getAhaSvcsByIden(iden, skiprun=skiprun):
                count += 1
                base.schedCoro(call(svcdef))

            for i in range(count):
                yield await queue.get()

    async def callAhaPeerGenr(self, iden, todo, timeout=None, skiprun=None):

        if not self.isactive:
            proxy = await self.nexsroot.client.proxy(timeout=timeout)
            async for item in proxy.callAhaPeerGenr(iden, todo, timeout=timeout, skiprun=skiprun):
                yield item

        queue = asyncio.Queue()
        async with await s_base.Base.anit() as base:

            async def call(svcdef):
                svcfull = svcdef.get('name')
                try:
                    async for item in self._callAhaSvcGenr(svcdef, todo, timeout=timeout):
                        await queue.put((svcfull, item))
                finally:
                    await queue.put(None)

            count = 0
            async for svcdef in self.getAhaSvcsByIden(iden, skiprun=skiprun):
                count += 1
                base.schedCoro(call(svcdef))

            while count > 0:

                item = await queue.get()
                if item is None:
                    count -= 1
                    continue

                yield item

    async def _finiSvcClients(self):
        for client in list(self.clients.values()):
            await client.fini()

    async def initServicePassive(self):
        await self._finiSvcClients()

    async def initServiceRuntime(self):

        self.clients = {}
        self.onfini(self._finiSvcClients)

        self.addActiveCoro(self._clearInactiveSessions)

        if self.isactive:

            # bootstrap a CA for our aha:network
            netw = self.conf.req('aha:network')

            if self.certdir.getCaCertPath(netw) is None:
                logger.info(f'Adding CA certificate for {netw}')
                await self.genCaCert(netw)

            name = self.conf.get('aha:name')
            if name is not None:
                host = f'{name}.{netw}'
                if self.certdir.getHostCertPath(host) is None:
                    logger.info(f'Adding server certificate for {host}')
                    await self._genHostCert(host, signas=netw)

            root = f'root@{netw}'
            await self._genUserCert(root, signas=netw)

            user = self.conf.get('aha:admin')
            if user is not None:
                await self._genUserCert(user, signas=netw)

    def _getDnsName(self):
        # emulate the old aha name.network behavior if the
        # explicit option is not set.

        hostname = self.conf.get('dns:name')
        if hostname is not None:
            return hostname

        ahaname = self.conf.get('aha:name')
        ahanetw = self.conf.get('aha:network')
        if ahaname is not None and ahanetw is not None:
            return f'{ahaname}.{ahanetw}'

    def _getProvListen(self):

        lisn = self.conf.get('provision:listen')
        if lisn is not None:
            return lisn

        # this may not use _getDnsName() in order to maintain
        # backward compatibilty with aha name.network configs
        # that do not intend to listen for provisioning.
        hostname = self.conf.get('dns:name')
        if hostname is not None:
            return f'ssl://0.0.0.0:27272?hostname={hostname}'

    def _getDmonListen(self):

        lisn = self.conf.get('dmon:listen', s_common.novalu)
        if lisn is not s_common.novalu:
            return lisn

        network = self.conf.req('aha:network')
        dnsname = self._getDnsName()
        if dnsname is not None:
            return f'ssl://0.0.0.0?hostname={dnsname}&ca={network}'

    def _reqProvListen(self):
        lisn = self._getProvListen()
        if lisn is not None:
            return lisn

        mesg = 'The AHA server is not configured for provisioning.'
        raise s_exc.NeedConfValu(mesg=mesg)

    async def initServiceNetwork(self):

        # bootstrap CA/host certs first
        network = self.conf.req('aha:network')

        hostname = self._getDnsName()
        if hostname is not None and network is not None:
            await self._genHostCert(hostname, signas=network)

        await s_cell.Cell.initServiceNetwork(self)

        # all AHA mirrors are registered
        if hostname is not None and self.sockaddr is not None:
            server = {'host': hostname, 'port': self.sockaddr[1]}
            await self.addAhaServer(server)

        self.provdmon = None

        provurl = self._getProvListen()
        if provurl is not None:
            self.provdmon = await ProvDmon.anit(self)
            self.onfini(self.provdmon)
            logger.info(f'provision listening: {provurl}')
            self.provaddr = await self.provdmon.listen(provurl)

    async def _clearInactiveSessions(self):

        async for svc in self.getAhaSvcs():
            if svc.get('svcinfo', {}).get('online') is None:
                continue
            current_sessions = {s_common.guid(iden) for iden in self.dmon.sessions.keys()}
            svcname = svc.get('svcname')
            network = svc.get('svcnetw')
            linkiden = svc.get('svcinfo').get('online')
            if linkiden not in current_sessions:
                logger.info(f'AhaCell activecoro setting service offline [{svcname}.{network}]',
                             extra=await self.getLogExtra(name=svcname, netw=network))
                await self.setAhaSvcDown(svcname, linkiden, network=network)

        # Wait until we are cancelled or the cell is fini.
        await self.waitfini()

    async def _waitAhaSvcOnline(self, name, timeout=None):

        name = self._getAhaName(name)

        while True:

            async with self.nexslock:

                retn = await self.getAhaSvc(name)
                if retn['svcinfo'].get('online') is not None:
                    return retn

                waiter = self.waiter(1, f'aha:svcadd:{name}')

            if await waiter.wait(timeout=timeout) is None:
                raise s_exc.TimeOut(mesg=f'Timeout waiting for aha:svcadd:{name}')

    async def _waitAhaSvcDown(self, name, timeout=None):

        name = self._getAhaName(name)

        while True:

            async with self.nexslock:

                retn = await self.getAhaSvc(name)
                online = retn['svcinfo'].get('online')
                if online is None:
                    return retn

                waiter = self.waiter(1, f'aha:svcdown:{name}')

            if await waiter.wait(timeout=timeout) is None:
                raise s_exc.TimeOut(mesg=f'Timeout waiting for aha:svcdown:{name}')

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
        logger.info(f'Adding service [{svcfull}] from [{unfo.get("scheme")}://{unfo.get("host")}:{unfo.get("port")}]',
                     extra=await self.getLogExtra(name=svcname, netw=svcnetw))

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
        await self.fire(f'aha:svcadd:{svcfull}', svcinfo=svcinfo)

    async def getAhaSvcProxy(self, svcdef, timeout=None):

        client = await self.getAhaSvcClient(svcdef)
        if client is None:
            return None

        return await client.proxy(timeout=timeout)

    async def getAhaSvcClient(self, svcdef):

        svcfull = svcdef.get('name')

        client = self.clients.get(svcfull)
        if client is not None:
            return client

        svcurl = self.getAhaSvcUrl(svcdef)

        client = self.clients[svcfull] = await s_telepath.ClientV2.anit(svcurl)
        async def fini():
            self.clients.pop(svcfull, None)

        client.onfini(fini)
        return client

    def _getAhaName(self, name):
        # the modern version of names is absolute or ...
        if name.endswith('...'):
            return name[:-2] + self.conf.req('aha:network')
        return name

    async def getAhaPool(self, name):
        name = self._getAhaName(name)
        byts = self.slab.get(name.encode(), db='aha:pools')
        if byts is not None:
            return s_msgpack.un(byts)

    def _savePoolInfo(self, poolinfo):
        s_schemas.reqValidAhaPoolDef(poolinfo)
        name = poolinfo.get('name')
        self.slab.put(name.encode(), s_msgpack.en(poolinfo), db='aha:pools')

    def _loadPoolInfo(self, name):
        byts = self.slab.get(name.encode(), db='aha:pools')
        if byts is not None:
            return s_msgpack.un(byts)

    def _reqPoolInfo(self, name):

        poolinfo = self._loadPoolInfo(name)
        if poolinfo is not None:
            return poolinfo

        mesg = f'There is no AHA service pool named {name}.'
        raise s_exc.NoSuchName(mesg=mesg, name=name)

    async def addAhaPool(self, name, info):

        name = self._getAhaName(name)

        if await self._getAhaSvc(name) is not None:
            mesg = f'An AHA service or pool is already using the name "{name}".'
            raise s_exc.DupName(mesg=mesg, name=name)

        info['name'] = name
        info['created'] = s_common.now()
        info['services'] = {}

        info.setdefault('creator', self.getDmonUser())

        return await self._push('aha:pool:add', info)

    async def getAhaPools(self):
        for lkey, byts in self.slab.scanByFull(db='aha:pools'):
            yield s_msgpack.un(byts)

    @s_nexus.Pusher.onPush('aha:pool:add')
    async def _addAhaPool(self, info):
        self._savePoolInfo(info)
        return info

    async def addAhaPoolSvc(self, poolname, svcname, info):
        info['created'] = s_common.now()
        info.setdefault('creator', self.getDmonUser())
        return await self._push('aha:pool:svc:add', poolname, svcname, info)

    @s_nexus.Pusher.onPush('aha:pool:svc:add')
    async def _addAhaPoolSvc(self, poolname, svcname, info):

        svcname = self._getAhaName(svcname)
        poolname = self._getAhaName(poolname)

        svcitem = await self._reqAhaSvc(svcname)

        poolinfo = self._loadPoolInfo(poolname)
        poolinfo['services'][svcname] = info

        self._savePoolInfo(poolinfo)

        for wind in self.poolwindows.get(poolname, ()):
            await wind.put(('svc:add', svcitem))

        return poolinfo

    @s_nexus.Pusher.onPushAuto('aha:pool:del')
    async def delAhaPool(self, name):
        name = self._getAhaName(name)
        byts = self.slab.pop(name.encode(), db='aha:pools')

        for wind in self.poolwindows.get(name, ()):
            await wind.fini()

        if byts is not None:
            return s_msgpack.un(byts)

    @s_nexus.Pusher.onPushAuto('aha:pool:svc:del')
    async def delAhaPoolSvc(self, poolname, svcname):

        svcname = self._getAhaName(svcname)
        poolname = self._getAhaName(poolname)

        poolinfo = self._reqPoolInfo(poolname)
        poolinfo['services'].pop(svcname, None)

        self._savePoolInfo(poolinfo)

        for wind in self.poolwindows.get(poolname, ()):
            await wind.put(('svc:del', {'name': svcname}))

        return poolinfo

    async def _getAhaSvc(self, svcname):
        # no fancy auto-resolve, just get actual service
        svcpath = ('aha', 'svcfull', svcname)
        return await self.jsonstor.getPathObj(svcpath)

    async def _reqAhaSvc(self, svcname):
        svcpath = ('aha', 'svcfull', svcname)
        svcitem = await self.jsonstor.getPathObj(svcpath)
        if svcitem is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service is currently named "{svcname}".', name=svcname)
        return svcitem

    @s_nexus.Pusher.onPushAuto('aha:svc:del')
    async def delAhaSvc(self, name, network=None):

        name = self._getAhaName(name)
        svcname, svcnetw, svcfull = self._nameAndNetwork(name, network)

        logger.info(f'Deleting service [{svcfull}].', extra=await self.getLogExtra(name=svcname, netw=svcnetw))

        full = ('aha', 'svcfull', svcfull)
        path = ('aha', 'services', svcnetw, svcname)

        await self.jsonstor.delPathObj(path)
        await self.jsonstor.delPathObj(full)

        # mostly for testing...
        await self.fire('aha:svcdel', svcname=svcname, svcnetw=svcnetw)

    async def setAhaSvcDown(self, name, linkiden, network=None):

        name = self._getAhaName(name)
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

        if await self.jsonstor.cmpDelPathObjProp(path, 'svcinfo/online', linkiden):
            await self.jsonstor.setPathObjProp(path, 'svcinfo/ready', False)

        # Check if we have any links which may need to be removed
        current_sessions = {s_common.guid(iden): sess for iden, sess in self.dmon.sessions.items()}
        sess = current_sessions.get(linkiden)
        if sess is not None:
            for link in [lnk for lnk in self.dmon.links if lnk.get('sess') is sess]:
                await link.fini()

        await self.fire('aha:svcdown', svcname=svcname, svcnetw=svcnetw)
        await self.fire(f'aha:svcdown:{svcfull}', svcname=svcname, svcnetw=svcnetw)

        logger.info(f'Set [{svcfull}] offline.',
                        extra=await self.getLogExtra(name=svcname, netw=svcnetw))

        client = self.clients.pop(svcfull, None)
        if client is not None:
            await client.fini()

    async def getAhaSvc(self, name, filters=None):

        name = self._getAhaName(name)

        path = ('aha', 'svcfull', name)
        svcentry = await self.jsonstor.getPathObj(path)

        if svcentry is not None:
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

        pooldef = await self.getAhaPool(name)
        if pooldef is not None:

            # in case the caller is not pool aware, merge a service entry and the pool def
            svcnames = list(pooldef.get('services').keys())

            # if there are not services added to the pool it does not exist yet
            if not svcnames:
                mesg = f'No services configured for pool: {name}'
                raise s_exc.BadArg(mesg=mesg)

            svcentry = await self.jsonstor.getPathObj(('aha', 'svcfull', random.choice(svcnames)))
            svcentry = s_msgpack.deepcopy(svcentry)
            svcentry.update(pooldef)

            return svcentry

        return None

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

        logger.info(f'Generating CA certificate for {network}',
                    extra=await self.getLogExtra(netw=network))
        fut = s_coro.executor(self.certdir.genCaCert, network, save=False)
        pkey, cert = await fut

        cakey = self.certdir._pkeyToByts(pkey).decode()
        cacert = self.certdir._certToByts(cert).decode()

        # nexusify storage..
        await self.saveCaCert(network, cakey, cacert)

        return cacert

    async def _genHostCert(self, hostname, signas=None):

        if self.certdir.getHostCertPath(hostname) is not None:
            return

        pkey, cert = await s_coro.executor(self.certdir.genHostCert, hostname, signas=signas, save=False)
        pkey = self.certdir._pkeyToByts(pkey).decode()
        cert = self.certdir._certToByts(cert).decode()
        await self.saveHostCert(hostname, pkey, cert)

    async def _genUserCert(self, username, signas=None):

        if self.certdir.getUserCertPath(username) is not None:
            return

        logger.info(f'Adding user certificate for {username}')

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

        hostname = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value

        hostpath = self.certdir.getHostCertPath(hostname)
        if hostpath is not None:
            os.unlink(hostpath)

        if signas is None:
            signas = hostname.split('.', 1)[1]

        logger.info(f'Signing host CSR for [{hostname}], signas={signas}, sans={sans}',
                    extra=await self.getLogExtra(hostname=hostname, signas=signas))

        pkey, cert = self.certdir.signHostCsr(xcsr, signas=signas, sans=sans)

        return self.certdir._certToByts(cert).decode()

    async def signUserCsr(self, csrtext, signas=None):
        xcsr = self.certdir._loadCsrByts(csrtext.encode())

        username = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value

        userpath = self.certdir.getUserCertPath(username)
        if userpath is not None:
            os.unlink(userpath)

        if signas is None:
            signas = username.split('@', 1)[1]

        logger.info(f'Signing user CSR for [{username}], signas={signas}',
                    extra=await self.getLogExtra(name=username, signas=signas))

        pkey, cert = self.certdir.signUserCsr(xcsr, signas=signas)

        return self.certdir._certToByts(cert).decode()

    async def getAhaUrls(self, user='root'):

        # for backward compat...
        urls = self.conf.get('aha:urls')
        if urls is not None:
            return urls

        network = self.conf.req('aha:network')

        urls = []
        for server in await self.getAhaServers():
            host = server.get('host')
            port = server.get('port')
            urls.append(f'ssl://{host}:{port}?certname={user}@{network}')

        return urls

    def getMyUrl(self, user='root'):
        port = self.sockaddr[1]
        host = self._getDnsName()
        network = self.conf.req('aha:network')
        return f'ssl://{host}:{port}?certname={user}@{network}'

    async def getAhaClone(self, iden):
        lkey = s_common.uhex(iden)
        byts = self.slab.get(lkey, db='aha:clones')
        if byts is not None:
            return s_msgpack.un(byts)

    async def addAhaClone(self, host, port=27492, conf=None):

        if conf is None:
            conf = {}

        network = self.conf.req('aha:network')

        conf['mirror'] = self.getMyUrl()

        conf['dns:name'] = host
        conf['aha:network'] = network
        conf['dmon:listen'] = f'ssl://0.0.0.0:{port}?hostname={host}&ca={network}'

        iden = s_common.guid()
        clone = {
            'iden': iden,
            'host': host,
            'port': port,
            'conf': conf,
        }
        await self._push('aha:clone:add', clone)

        logger.info(f'Created AHA clone provisioning for {host} with iden {iden}',
                     extra=await self.getLogExtra(iden=iden, name=host, netw=network))

        return self._getProvClientUrl(iden)

    @s_nexus.Pusher.onPush('aha:clone:add')
    async def _addAhaClone(self, clone):
        iden = clone.get('iden')
        lkey = s_common.uhex(iden)
        self.slab.put(lkey, s_msgpack.en(clone), db='aha:clones')

    async def addAhaSvcProv(self, name, provinfo=None):

        if not name:
            raise s_exc.BadArg(mesg='Empty name values are not allowed for provisioning.')

        self._reqProvListen()

        if provinfo is None:
            provinfo = {}

        iden = s_common.guid()

        provinfo['iden'] = iden

        conf = provinfo.setdefault('conf', {})

        netw = self.conf.req('aha:network')

        ahaadmin = self.conf.get('aha:admin')
        if ahaadmin is not None: # pragma: no cover
            conf.setdefault('aha:admin', ahaadmin)

        ahauser = conf.setdefault('aha:user', 'root')
        ahaurls = await self.getAhaUrls(user=ahauser)

        conf['aha:network'] = netw

        hostname = f'{name}.{netw}'

        if len(hostname) > 64:
            mesg = f'Hostname value must not exceed 64 characters in length. {hostname=}, len={len(hostname)}'
            raise s_exc.BadArg(mesg=mesg)

        conf.setdefault('aha:name', name)
        dmon_port = provinfo.get('dmon:port', 0)
        dmon_listen = f'ssl://0.0.0.0:{dmon_port}?hostname={hostname}&ca={netw}'
        conf.setdefault('dmon:listen', dmon_listen)

        https_port = provinfo.get('https:port', s_common.novalu)
        if https_port is not s_common.novalu:
            conf.setdefault('https:port', https_port)

        # if the relative name contains a dot, we are a mirror peer.
        peer = name.find('.') != -1
        leader = name.rsplit('.', 1)[-1]

        if peer:
            conf.setdefault('aha:leader', leader)

        conf.setdefault('aha:registry', ahaurls)

        mirname = provinfo.get('mirror')
        if mirname is not None:
            conf['mirror'] = f'aha://{ahauser}@{mirname}...'

        user = await self.auth.getUserByName(ahauser)
        if user is None:
            user = await self.auth.addUser(ahauser)

        perms = [
            ('aha', 'service', 'get', netw),
            ('aha', 'service', 'add', netw, name),
        ]
        if peer:
            perms.append(('aha', 'service', 'add', netw, leader))
        for perm in perms:
            if user.allowed(perm):
                continue
            await user.allow(perm)

        iden = await self._push('aha:svc:prov:add', provinfo)

        logger.info(f'Created service provisioning for {name}.{netw} with iden {iden}',
                     extra=await self.getLogExtra(iden=iden, name=name, netw=netw))

        return self._getProvClientUrl(iden)

    def _getProvClientUrl(self, iden):

        provlisn = self._getProvListen()

        provport = self.provaddr[1]
        provhost = self._getDnsName()

        urlinfo = s_telepath.chopurl(provlisn)

        host = urlinfo.get('hostname')
        scheme = urlinfo.get('scheme')

        if host is None:
            host = urlinfo.get('host')

        newinfo = {
            'host': provhost,
            'port': provport,
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

    @s_nexus.Pusher.onPushAuto('aha:svc:prov:clear')
    async def clearAhaSvcProvs(self):
        for iden, byts in self.slab.scanByFull(db='aha:provs'):
            self.slab.delete(iden, db='aha:provs')
            provinfo = s_msgpack.un(byts)
            logger.info(f'Deleted service provisioning service={provinfo.get("conf").get("aha:name")}, iden={iden.decode()}')
            await asyncio.sleep(0)

    @s_nexus.Pusher.onPushAuto('aha:enroll:clear')
    async def clearAhaUserEnrolls(self):
        for iden, byts in self.slab.scanByFull(db='aha:enrolls'):
            self.slab.delete(iden, db='aha:enrolls')
            userinfo = s_msgpack.un(byts)
            logger.info(f'Deleted user enrollment username={userinfo.get("name")}, iden={iden.decode()}')
            await asyncio.sleep(0)

    @s_nexus.Pusher.onPushAuto('aha:clone:clear')
    async def clearAhaClones(self):
        for lkey, byts in self.slab.scanByFull(db='aha:clones'):
            self.slab.delete(lkey, db='aha:clones')
            cloninfo = s_msgpack.un(byts)
            logger.info(f'Deleted AHA clone enrollment username={cloninfo.get("host")}, iden={s_common.ehex(lkey)}')
            await asyncio.sleep(0)

    @s_nexus.Pusher.onPushAuto('aha:svc:prov:del')
    async def delAhaSvcProv(self, iden):
        self.slab.delete(iden.encode(), db='aha:provs')

    async def addAhaUserEnroll(self, name, userinfo=None, again=False):

        if not name:
            raise s_exc.BadArg(mesg='Empty name values are not allowed for provisioning.')

        provurl = self._reqProvListen()
        ahanetw = self.conf.req('aha:network')

        username = f'{name}@{ahanetw}'

        if len(username) > 64:
            mesg = f'Username value must not exceed 64 characters in length. username={username}, len={len(username)}'
            raise s_exc.BadArg(mesg=mesg)

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

        logger.info(f'Created user provisioning for {name} with iden {iden}',
                     extra=await self.getLogExtra(iden=iden, name=name))

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
