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
import synapse.lib.provision as s_provision

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
            }
        }
    },
    'additionalProperties': False,
    'required': ['name'],
}
provSvcSchema = s_config.getJsValidator(_provSvcSchema)


class AhaProvisionServiceV3(s_httpapi.Handler):

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

class AhaServicesV3(s_httpapi.Handler):

    async def get(self):

        if not await self.reqAuthAdmin():
            return

        if not await self.reqNoBody():
            return

        ret = []

        try:

            async for info in self.cell.getAhaSvcs():
                ret.append(info)

        except Exception as e:  # pragma: no cover
            logger.exception('Error getting Aha services.')
            return self.sendRestErr(e.__class__.__name__, str(e))

        return self.sendRestRetn(ret)

class AhaApi(s_cell.CellApi):

    @s_cell.adminapi()
    async def addAhaClone(self, host, *, port=27492, conf=None):
        return await self.cell.addAhaClone(host, port=port, conf=conf)

    async def getAhaUrls(self, *, user='root'):
        ahaurls = await self.cell.getAhaUrls(user=user)
        return ahaurls

    @s_cell.adminapi()
    async def callAhaPeerApi(self, iden, todo, *, timeout=None, skiprun=None):
        async for item in self.cell.callAhaPeerApi(iden, todo, timeout=timeout, skiprun=skiprun):
            yield item

    @s_cell.adminapi()
    async def callAhaPeerGenr(self, iden, todo, *, timeout=None, skiprun=None):
        async for item in self.cell.callAhaPeerGenr(iden, todo, timeout=timeout, skiprun=skiprun):
            yield item

    async def getAhaSvc(self, name, *, filters=None):
        '''
        Return an AHA service description dictionary for a service name.
        '''
        svcentry = await self.cell.getAhaSvc(name, filters=filters)
        if svcentry is None:
            return None

        svcentry = s_msgpack.deepcopy(svcentry)

        # suggest that the user of the remote service is the same
        username = self.user.name.split('@')[0]

        if svcentry.get('info'):
            svcentry['info']['urlinfo']['user'] = username

        return svcentry

    async def getAhaSvcs(self):
        '''
        Yield AHA service entry dictionaries.
        '''
        async for svcentry in self.cell.getAhaSvcs():
            yield svcentry

    async def getAhaSvcsByIden(self, iden, *, online=True, skiprun=None):
        async for svcentry in self.cell.getAhaSvcsByIden(iden, online=online, skiprun=skiprun):
            yield svcentry

    @s_cell.adminapi()
    async def getAhaTopo(self):
        '''
        Yield AHA topology messages ( svc:add / svc:del / svc:sync ) beginning
        with a snapshot of all current services followed by live updates.
        '''
        async for mesg in self.cell.getAhaTopo():
            yield mesg

    async def getAhaSvcsByType(self, celltype, *, online=True):
        '''
        Yield AHA service entry dictionaries for a given cell type.
        '''
        async for svcentry in self.cell.getAhaSvcsByType(celltype, online=online):
            yield svcentry

    async def getAhaSvcByType(self, celltype, *, filters=None):
        '''
        Return the AHA service description for the single instance of a cell type.
        '''
        svcentry = await self.cell.getAhaSvcByType(celltype, filters=filters)
        if svcentry is None:
            return None

        svcentry = s_msgpack.deepcopy(svcentry)

        # suggest that the user of the remote service is the same
        username = self.user.name.split('@')[0]

        if svcentry.get('info'):
            svcentry['info']['urlinfo']['user'] = username

        return svcentry

    async def addAhaSvc(self, name, info):
        '''
        Register a service with the AHA discovery server.

        NOTE: In order for the service to remain marked "up" a caller
              must maintain the telepath link.
        '''

        await self._reqUserAllowed(('aha', 'service', 'add'))

        name = self.cell._getAhaName(name)

        # dont disclose the real session...
        sess = s_common.guid(self.sess.iden)
        info['session'] = sess
        info.setdefault('ready', True)

        if self.link.sock is not None:
            host, port = self.link.sock.getpeername()
            urlinfo = info.get('urlinfo', {})
            urlinfo.setdefault('host', host)

        async def fini():

            if self.cell.isfini:  # pragma: no cover
                mesg = f'{self.cell.__class__.__name__} is fini. Unable to set {name} as down.'
                logger.warning(mesg, self.cell.getLogExtra(name=name))
                return

            logger.info(f'AhaCellApi fini, setting service offline [{name}]', extra=self.cell.getLogExtra(name=name))

            coro = self.cell.setAhaSvcDown(name, sess)
            self.cell.schedCoro(coro)  # this will eventually execute or get cancelled.

        retn = await self.cell.addAhaSvc(name, info)

        # only mark the service down on link teardown once it registered
        self.onfini(fini)

        return retn

    async def modAhaSvcInfo(self, name, svcinfo):

        for key in svcinfo.keys():
            if key not in ('ready',):
                mesg = f'Editing AHA service info property ({key}) is not supported!'
                raise s_exc.BadArg(mesg=mesg)

        svcentry = await self.cell.getAhaSvc(name)
        if svcentry is None:
            return False

        await self._reqUserAllowed(('aha', 'service', 'add'))

        return await self.cell.modAhaSvcInfo(name, svcinfo)

    async def getAhaSvcMirrors(self, name):
        '''
        Return list of AHA service entry dictionaries for mirrors of a service.
        '''
        svcentry = await self.cell.getAhaSvc(name)
        if svcentry is None:
            return None

        svciden = svcentry['info']['iden']
        return await self.cell.getAhaSvcMirrors(svciden)

    async def delAhaSvc(self, name):
        '''
        Remove an AHA service entry.
        '''
        await self._reqUserAllowed(('aha', 'service', 'del'))
        return await self.cell.delAhaSvc(name)

    async def getCaCert(self):
        return await self.cell.getCaCert()

    async def signHostCsr(self, csrtext, *, sans=None):
        await self._reqUserAllowed(('aha', 'csr', 'host'))
        return await self.cell.signHostCsr(csrtext, sans=sans)

    async def signUserCsr(self, csrtext):
        await self._reqUserAllowed(('aha', 'csr', 'user'))
        return await self.cell.signUserCsr(csrtext)

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
                item[1]['info']['urlinfo']['user'] = username

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
    async def addAhaSvcProv(self, name, *, provinfo=None):
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
    async def setAhaSvcTypeIndex(self, name, valu):
        '''
        Set the auto-provisioning index for a service type.
        '''
        return await self.cell.setAhaSvcTypeIndex(name, valu)

    async def getLeadTerm(self, svctype):
        '''
        Return the current leadership term for a service type.
        '''
        return await self.cell.getLeadTerm(svctype)

    async def regLeadTerm(self, svctype, svcname, nexsoffs, term=None):
        '''
        Register a service with the leadership term for its service type.
        '''
        await self._reqUserAllowed(('aha', 'service', 'add'))
        return await self.cell.regLeadTerm(svctype, svcname, nexsoffs, term=term)

    async def setLeadTerm(self, svctype, svcname, nexsoffs):
        '''
        Create a new leadership term for a service type to record an API driven promotion.
        '''
        await self._reqUserAllowed(('aha', 'service', 'add'))
        return await self.cell.setLeadTerm(svctype, svcname, nexsoffs)

    @s_cell.adminapi()
    async def addAhaUserEnroll(self, name, *, userinfo=None, again=False):
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
            logger.info(mesg, extra=self.aha.getLogExtra(iden=name, name=anam, netw=anet))
            return ProvApi(self.aha, provinfo)

        userinfo = await self.aha.getAhaUserEnroll(name)
        if userinfo is not None:
            unam = userinfo.get('name')
            mesg = f'Retrieved user provisioning info for {unam} iden {name}'
            logger.info(mesg, extra=self.aha.getLogExtra(iden=name, name=unam))
            await self.aha.delAhaUserEnroll(name)
            return EnrollApi(self.aha, userinfo)

        clone = await self.aha.getAhaClone(name)
        if clone is not None:
            host = clone.get('host')
            mesg = f'Retrieved AHA clone info for {host} iden {name}'
            logger.info(mesg, extra=self.aha.getLogExtra(iden=name, host=host))
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

    async def iterNewBackupArchive(self, *, name=None, remove=False):
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
        return await self.aha.getCaCert()

    async def signUserCsr(self, byts):

        ahauser = self.userinfo.get('name')
        network = self.aha.conf.req('aha:network')

        username = f'{ahauser}@{network}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != username:
            mesg = f'Invalid user CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing user CSR for [{username}]', extra=self.aha.getLogExtra(name=username))

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, signas=network, save=False)
        return self.aha.certdir._certToByts(cert)

class ProvApi:

    def __init__(self, aha, provinfo):
        self.aha = aha
        self.provinfo = provinfo

    async def getProvInfo(self):
        return self.provinfo

    async def getCaCert(self):
        return await self.aha.getCaCert()

    async def signHostCsr(self, byts):

        ahaname = self.provinfo['conf'].get('aha:name')
        ahanetw = self.provinfo['conf'].get('aha:network')

        hostname = f'{ahaname}.{ahanetw}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != hostname:
            mesg = f'Invalid host CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing host CSR for [{hostname}]', extra=self.aha.getLogExtra(name=hostname))

        pkey, cert = self.aha.certdir.signHostCsr(xcsr, ahanetw, save=False)
        return self.aha.certdir._certToByts(cert)

    async def signUserCsr(self, byts):

        network = self.provinfo['conf'].get('aha:network')

        username = f'root@{network}'

        xcsr = self.aha.certdir._loadCsrByts(byts)
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
        if name != username:
            mesg = f'Invalid user CSR CN={name}.'
            raise s_exc.BadArg(mesg=mesg)

        logger.info(f'Signing user CSR for [{username}]', extra=self.aha.getLogExtra(name=username))

        pkey, cert = self.aha.certdir.signUserCsr(xcsr, signas=network, save=False)
        return self.aha.certdir._certToByts(cert)

class AhaCell(s_cell.Cell):

    celltype = 'aha'

    cellapi = AhaApi
    confbase = copy.deepcopy(s_cell.Cell.confbase)
    confbase['parent']['hidedocs'] = False  # type: ignore
    confbase['parent']['hidecmdl'] = False  # type: ignore
    confbase['aha:network']['default'] = 'syn'  # type: ignore
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
        'provision:listen': {
            'description': 'A telepath URL for the AHA provisioning listener.',
            'type': ['string', 'null'],
            'pattern': '^ssl://.+$'
        },
    }

    # Rename the class and remove these two overrides in 3.0.0
    @classmethod
    def getEnvPrefix(cls):
        return ('SYN_AHA', f'SYN_{cls.__name__.upper()}', )

    def getSvcName(self):
        # The AHA service does not register itself with AHA, so the
        # default cell logic that derives the log service name from
        # 'aha:name' + 'aha:network' will not produce a value when
        # 'aha:name' is not configured. Fall back to 'dns:name' so
        # the 'service' log key is still populated.
        name = super().getSvcName()
        if name is not None:
            return name

        return self.conf.get('dns:name')

    async def _initCellBoot(self):

        await self._bootCloneMcast()

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

    async def _bootCloneMcast(self):
        # On an inaugural boot with SYN_PROVISION_SECRET and SYN_PROVISION_FOLLOWER
        # set and no explicit clone URL, discover the leader AHA via encrypted
        # multicast and enroll as a clone. The minted clone URL is adopted as our
        # 'clone' config so the normal clone bootstrap below proceeds unchanged.

        if self.conf.get('clone') is not None:
            return

        if os.environ.get('SYN_PROVISION_SECRET') is None:
            return

        if os.environ.get('SYN_PROVISION_FOLLOWER') is None:
            return

        if os.path.isfile(s_common.genpath(self.dirn, 'cell.guid')):
            return

        host = self.conf.get('dns:name')
        if host is None:
            mesg = 'SYN_PROVISION_FOLLOWER requires dns:name to be set to enroll as an AHA clone.'
            raise s_exc.FatalErr(mesg=mesg)

        logger.info('Attempting AHA clone provisioning discovery.')

        mesg = {'type': 'aha', 'data': {'host': host}}

        warnmesg = 'SYN_PROVISION_FOLLOWER is set but AHA clone provisioning discovery received ' \
                   'no response; waiting for the leader AHA to appear.'

        # assume a leader AHA exists: retry discovery indefinitely, logging a
        # warning roughly every PROV_FOLLOWER_WARN_TIMEOUT seconds until it responds.
        lastwarn = s_common.now()

        # NOTE: this runs during _initCellBoot, before Base.__anit__ sets
        # self.isfini, so this loop cannot use 'while not self.isfini'.
        while True:

            data = await self._runProvMcastDiscover(mesg)
            if data is not None:
                break

            lastwarn = self._logFollowerWait(lastwarn, warnmesg)

        self.conf['clone'] = data.get('url')
        logger.info('AHA clone provisioning discovery succeeded.')

    async def initServiceStorage(self):

        self.features['callpeers'] = 1
        self.features['getAhaSvcsByIden'] = 1

        self.slab.initdb('aha:provs')
        self.slab.initdb('aha:enrolls')

        self.slab.initdb('aha:clones')
        self.slab.initdb('aha:servers')

        self.slab.initdb('aha:pools')

        self.slab.initdb('svc:type:index')

        # the service registry: the aha:svcs db is keyed by the full service
        # name and stores the svc entry. the byiden/bytype dbs are dupsort
        # indexes keyed by the ( immutable ) service iden / type with the
        # service names stored as duplicate values.
        self.slab.initdb('aha:svcs')
        self.slab.initdb('aha:svcs:byiden', dupsort=True)
        self.slab.initdb('aha:svcs:bytype', dupsort=True)

        # tracks the session iden which currently holds a service online,
        # keyed by service name. the service entry itself carries only a
        # boolean online flag.
        self.slab.initdb('svc:sess')

        # leadership terms tracked per service type. aha:lead:term is keyed by
        # the service type and stores the current term. aha:lead:terms stores
        # the historical terms keyed by <type>\x00<nexsoffs><created> so they
        # sort chronologically within a type for range scans.
        self.slab.initdb('aha:lead:term')
        self.slab.initdb('aha:lead:terms')

        self.poolwindows = collections.defaultdict(list)
        self.topowindows = []

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

        await self.slab.put(lkey, s_msgpack.en(server), db='aha:servers')

        await self._fireTopoAhaServers()

        return True

    @s_nexus.Pusher.onPushAuto('aha:server:del')
    async def delAhaServer(self, host, port):

        lkey = s_msgpack.en((host, port))

        byts = self.slab.pop(lkey, db='aha:servers')
        if byts is None:
            return None

        await self._fireTopoAhaServers()

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

                svcentry = self._getSvcEntry(svcname)
                if not svcentry:
                    logger.warning(f'Pool ({name}) includes service ({svcname}) which does not exist.')
                    continue

                await wind.put(('svc:add', svcentry))

            # subscribe to changes
            self.poolwindows[name].append(wind)
            async def onfini():
                self.poolwindows[name].remove(wind)

            wind.onfini(onfini)

            # iterate events...
            async for mesg in wind:
                yield mesg

    async def getAhaTopo(self):

        async with await s_queue.Window.anit(maxsize=10000) as wind:

            # register the window under the nexus lock so that no topology
            # mutation may run between registration and the snapshot without
            # also being delivered through the window. the lock is held only
            # for the ( cheap ) registration, not the service scan below, so
            # that concurrent registrations are not blocked.
            async with self.nexslock:

                self.topowindows.append(wind)
                async def onfini():
                    self.topowindows.remove(wind)

                wind.onfini(onfini)

            # stream the current snapshot ( read without holding the lock )
            # followed by the sync sentinel. any change that races the snapshot
            # is also queued in the window and applied idempotently after it,
            # so the client converges on the correct topology state.
            yield ('aha:servers', {'urls': await self.getAhaUrls()})

            async for svcentry in self.getAhaSvcs():
                yield ('svc:add', {'entry': svcentry})

            yield ('svc:sync', {})

            async for mesg in wind:
                yield mesg

    async def _fireTopoMod(self, svcentry):
        for wind in tuple(self.topowindows):
            await wind.put(('svc:mod', {'entry': svcentry}))

    async def _fireTopoDel(self, name):
        for wind in tuple(self.topowindows):
            await wind.put(('svc:del', {'name': name}))

    async def _fireTopoAhaServers(self):
        # the set of AHA servers changed ( e.g. a new clone called in ): push
        # the current urls so clients update their stored AHA server list.
        urls = await self.getAhaUrls()
        for wind in tuple(self.topowindows):
            await wind.put(('aha:servers', {'urls': urls}))

    def _initCellHttpApis(self):
        s_cell.Cell._initCellHttpApis(self)
        self.addHttpApi('/api/v3/aha/services', AhaServicesV3, {'cell': self})
        self.addHttpApi('/api/v3/aha/provision/service', AhaProvisionServiceV3, {'cell': self})

    async def callAhaSvcApi(self, name, todo, timeout=None):
        name = self._getAhaName(name)
        svcentry = await self._getAhaSvc(name)
        return self._callAhaSvcApi(svcentry, todo, timeout=timeout)

    async def _callAhaSvcApi(self, svcentry, todo, timeout=None):
        try:
            proxy = await self.getAhaSvcProxy(svcentry, timeout=timeout)
            meth = getattr(proxy, todo[0])
            return await s_common.waitretn(meth(*todo[1], **todo[2]), timeout=timeout)
        except Exception as e:
            # in case proxy construction fails
            return (False, s_common.excinfo(e))

    async def _callAhaSvcGenr(self, svcentry, todo, timeout=None):
        try:
            proxy = await self.getAhaSvcProxy(svcentry, timeout=timeout)
            meth = getattr(proxy, todo[0])
            async for item in s_common.waitgenr(meth(*todo[1], **todo[2]), timeout=timeout):
                yield item
        except Exception as e:
            # in case proxy construction fails
            yield (False, s_common.excinfo(e))

    async def getAhaSvcsByIden(self, iden, online=True, skiprun=None):

        runs = set()
        for svcname in self._getSvcNamesByIden(iden):
            await asyncio.sleep(0)

            svcentry = self._getSvcEntry(svcname)
            if svcentry is None: # pragma: no cover
                continue

            if online and not svcentry.get('online'):
                continue

            svcrun = svcentry['info'].get('run')
            if svcrun in runs:
                continue

            if skiprun == svcrun:
                continue

            runs.add(svcrun)
            yield svcentry

    def getAhaSvcUrl(self, svcentry, user='root'):
        name = svcentry.get('name')
        network = self.conf.get('aha:network')
        host = svcentry['info']['urlinfo']['host']
        port = svcentry['info']['urlinfo']['port']
        return f'ssl://{host}:{port}?hostname={name}&certname={user}@{network}'

    async def callAhaPeerApi(self, iden, todo, timeout=None, skiprun=None):

        if not self.isactive:
            proxy = await self.nexsroot.client.proxy(timeout=timeout)
            async for item in proxy.callAhaPeerApi(iden, todo, timeout=timeout, skiprun=skiprun):
                yield item

        queue = asyncio.Queue()
        async with await s_base.Base.anit() as base:

            async def call(svcentry):
                name = svcentry.get('name')
                await queue.put((name, await self._callAhaSvcApi(svcentry, todo, timeout=timeout)))

            count = 0
            async for svcentry in self.getAhaSvcsByIden(iden, skiprun=skiprun):
                count += 1
                base.schedCoro(call(svcentry))

            for i in range(count):
                yield await queue.get()

    async def callAhaPeerGenr(self, iden, todo, timeout=None, skiprun=None):

        if not self.isactive:
            proxy = await self.nexsroot.client.proxy(timeout=timeout)
            async for item in proxy.callAhaPeerGenr(iden, todo, timeout=timeout, skiprun=skiprun):
                yield item

        queue = asyncio.Queue()
        async with await s_base.Base.anit() as base:

            async def call(svcentry):
                name = svcentry.get('name')
                try:
                    async for item in self._callAhaSvcGenr(svcentry, todo, timeout=timeout):
                        await queue.put((name, item))
                finally:
                    await queue.put(None)

            count = 0
            async for svcentry in self.getAhaSvcsByIden(iden, skiprun=skiprun):
                count += 1
                base.schedCoro(call(svcentry))

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

            await self._initCaCert()

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

        return await super().initServiceRuntime()

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
            if not lisn.startswith('ssl://'):
                raise s_exc.BadConfValu(mesg='dmon:listen: AHA bind URLs must begin with ssl://')
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
        self.provmcast = None

        provurl = self._getProvListen()
        if provurl is not None:
            self.provdmon = await ProvDmon.anit(self)
            self.onfini(self.provdmon)
            logger.info(f'provision listening: {provurl}')
            self.provaddr = await self.provdmon.listen(provurl)

            secret = os.environ.get('SYN_PROVISION_SECRET')
            if secret is not None:
                await self._initProvMcast(secret)

    async def _initProvMcast(self, secret):

        key = s_provision.deriveKey(secret)

        self.provmcast = await s_provision.ProvCast.anit(key, s_provision.DEFAULT_MCAST_PORT,
                                                         group=s_provision.DEFAULT_MCAST_GROUP, join=True)
        self.onfini(self.provmcast)

        logger.info(f'provision discovery listening: {s_provision.DEFAULT_MCAST_GROUP}:{s_provision.DEFAULT_MCAST_PORT}')

        self.schedCoro(self._runProvMcast())

    async def _runProvMcast(self):

        while not self.isfini:

            item = await self.provmcast.recv()
            if item is None: # pragma: no cover
                continue

            mesg, addr = item
            await self._onProvMcastReq(mesg, addr)

    async def _onProvMcastReq(self, mesg, addr):

        # only the current leader services provisioning requests.
        if not self.isactive:
            return

        try:
            s_schemas.reqValidProvRequest(mesg)
        except s_exc.SchemaViolation:
            logger.warning('Ignoring invalid provision discovery request.')
            return

        mtype = mesg.get('type')
        data = mesg.get('data')

        try:
            if mtype == 'aha':
                # enroll the sender as a clone of this ( leader ) AHA service.
                url = await self.addAhaClone(data.get('host'), port=data.get('port', 27492))

            else:
                celltype = data.get('type')
                name = await self._getProvMcastName(celltype)
                url = await self.addAhaSvcProv(name)

            resp = {'type': 'retn', 'data': (True, {'url': url})}

        except Exception as e:
            logger.exception(f'Error auto-provisioning discovery request of type {mtype}')
            resp = {'type': 'retn', 'data': s_common.retnexc(e)}

        self.provmcast.send(resp, addr)

    async def _getProvMcastName(self, celltype):

        # each instance of a service type provisions as NNN.<type>. the first to
        # register a leadership term becomes the leader; the rest follow it.
        indx = await self.getSvcTypeIndex(celltype)
        return f'{indx:03d}.{celltype}'

    async def _clearInactiveSessions(self):

        async for svcentry in self.getAhaSvcs():

            name = svcentry.get('name')

            linkiden = self._getSvcSess(name)
            if linkiden is None:
                continue

            current_sessions = {s_common.guid(iden) for iden in self.dmon.sessions.keys()}

            if linkiden not in current_sessions:
                logger.info(f'AhaCell activecoro setting service offline [{name}]', extra=self.getLogExtra(name=name))
                await self.setAhaSvcDown(name, linkiden)

        # Wait until we are cancelled or the cell is fini.
        await self.waitfini()

    async def _waitAhaSvcOnline(self, name, timeout=None):

        name = self._getAhaName(name)

        while True:

            async with self.nexslock:

                retn = await self.getAhaSvc(name)
                if retn and retn.get('online'):
                    return retn

                waiter = self.waiter(1, 'aha:svc:add')

            if await waiter.wait(timeout=timeout) is None:
                raise s_exc.TimeOut(mesg='Timeout waiting for aha:svc:add')

    async def _waitAhaSvcDown(self, name, timeout=None):

        name = self._getAhaName(name)

        while True:

            async with self.nexslock:

                retn = await self.getAhaSvc(name)
                if not retn.get('online'):
                    return retn

                waiter = self.waiter(1, 'aha:svc:down')

            if await waiter.wait(timeout=timeout) is None:
                raise s_exc.TimeOut(mesg='Timeout waiting for aha:svc:down')

    async def _waitAhaSvcLeader(self, celltype, timeout=None):

        # poll for the cell type to resolve to an online leader. leadership is
        # driven by the current leadership term ( which may flag an already
        # registered service ) rather than a fresh aha:svc:add, so we re-check
        # rather than only waiting on registration events.
        async def poll():
            while not self.isfini:
                svcentry = await self.getAhaSvcByType(celltype)
                if svcentry is not None:
                    return svcentry

                if await self.waitfini(timeout=0.1):  # pragma: no cover
                    return None

        try:
            return await asyncio.wait_for(poll(), timeout=timeout)
        except asyncio.TimeoutError:  # pragma: no cover
            mesg = f'Timeout waiting for an online leader of type {celltype}'
            raise s_exc.TimeOut(mesg=mesg) from None

    def _getSvcEntry(self, name):
        byts = self.slab.get(name.encode(), db='aha:svcs')
        if byts is None:
            return None

        return s_msgpack.un(byts)

    def _getSvcSess(self, name):
        # return the session iden which currently holds the service online.
        byts = self.slab.get(name.encode(), db='svc:sess')
        if byts is None:
            return None

        return byts.decode()

    async def _setSvcEntry(self, svcentry):

        name = svcentry.get('name')
        info = svcentry.get('info')

        # the leader flag is managed exclusively by the leadership terms: an
        # entry is the leader when its name matches the current term for its type.
        svctype = info.get('type')
        term = self._getLeadTerm(svctype) if svctype is not None else None
        svcentry['leader'] = term is not None and term.get('name') == name

        lkey = name.encode()

        # drop stale index rows if a re-registration changed the iden/type.
        oldb = self.slab.get(lkey, db='aha:svcs')
        if oldb is not None:

            oldinfo = s_msgpack.un(oldb).get('info')

            oldiden = oldinfo.get('iden')
            if oldiden is not None and oldiden != info.get('iden'):
                self.slab.delete(oldiden.encode(), lkey, db='aha:svcs:byiden')

            oldtype = oldinfo.get('type')
            if oldtype is not None and oldtype != info.get('type'):
                self.slab.delete(oldtype.encode(), lkey, db='aha:svcs:bytype')

        await self.slab.put(lkey, s_msgpack.en(svcentry), db='aha:svcs')

        iden = info.get('iden')
        if iden is not None:
            await self.slab.put(iden.encode(), lkey, dupdata=True, db='aha:svcs:byiden')

        celltype = info.get('type')
        if celltype is not None:
            await self.slab.put(celltype.encode(), lkey, dupdata=True, db='aha:svcs:bytype')

    async def _popSvcEntry(self, name):

        lkey = name.encode()

        byts = self.slab.pop(lkey, db='aha:svcs')
        if byts is None:
            return None

        svcentry = s_msgpack.un(byts)
        info = svcentry.get('info')

        iden = info.get('iden')
        if iden is not None:
            self.slab.delete(iden.encode(), lkey, db='aha:svcs:byiden')

        celltype = info.get('type')
        if celltype is not None:
            self.slab.delete(celltype.encode(), lkey, db='aha:svcs:bytype')

        return svcentry

    def _getSvcNamesByType(self, celltype):
        return [byts.decode() for _, byts in self.slab.scanByDups(celltype.encode(), db='aha:svcs:bytype')]

    def _getSvcNamesByIden(self, iden):
        return [byts.decode() for _, byts in self.slab.scanByDups(iden.encode(), db='aha:svcs:byiden')]

    async def getAhaSvcs(self):
        for _, byts in self.slab.scanByFull(db='aha:svcs'):
            yield s_msgpack.un(byts)

    @s_nexus.Pusher.onPushAuto('aha:svc:mod')
    async def modAhaSvcInfo(self, name, svcinfo):

        svcentry = await self.getAhaSvc(name)
        if svcentry is None:
            return False

        name = svcentry.get('name')

        # re-fetch the raw stored entry ( getAhaSvc may resolve pools/types )
        svcentry = self._getSvcEntry(name)
        if svcentry is None: # pragma: no cover
            return False

        for prop, valu in svcinfo.items():
            svcentry['info'][prop] = valu

        await self._setSvcEntry(svcentry)

        await self._fireTopoMod(svcentry)

        return True

    async def addAhaSvc(self, name, info):

        name = self._getAhaName(name)

        self._reqSvcType(info)
        await self._reqSvcTypeUnique(info)

        return await self._push('aha:svc:add', name, info)

    def _reqSvcType(self, info):
        # implementers must override the service type. the base ``cell`` type
        # is not a deployable service and may not register with AHA.
        if info.get('type') == 'cell':
            mesg = 'AHA service type cell may not register; implementers must override the service type.'
            raise s_exc.BadArg(mesg=mesg, celltype='cell')

    async def _reqSvcTypeUnique(self, info):
        # enforce that only one instance ( iden ) of a given cell type may
        # register with this AHA deployment. leader + mirrors share an iden
        # so they are allowed to re-register. online=False so that an offline
        # instance still holds the type until it is explicitly removed.
        celltype = info.get('type')
        if celltype is None:
            return

        iden = info.get('iden')

        async for svcentry in self.getAhaSvcsByType(celltype, online=False):

            if svcentry['info'].get('iden') == iden:
                continue

            mesg = f'AHA service type {celltype} is already registered by a different service instance.'
            raise s_exc.BadArg(mesg=mesg, celltype=celltype)

    @s_nexus.Pusher.onPush('aha:svc:add')
    async def _addAhaSvc(self, name, info):

        unfo = info.get('urlinfo')
        logger.info(f'Adding service [{name}] from [{unfo.get("scheme")}://{unfo.get("host")}:{unfo.get("port")}]',
                     extra=self.getLogExtra(name=name))

        # the online session iden is tracked in the svc:sess db rather than
        # within the service info. the entry itself carries a boolean flag and
        # the stored info omits the session key ( without mutating the caller ).
        session = info.get('session')

        svcinfo = {k: v for (k, v) in info.items() if k != 'session'}

        svcentry = {
            'name': name,
            'info': svcinfo,
            'online': session is not None,
        }

        # compute the derived leader flag the same way _setSvcEntry does so an
        # unchanged re-registration ( e.g. a nexus replay or a redundant
        # check-in ) can be detected and fire no events.
        svctype = svcinfo.get('type')
        term = self._getLeadTerm(svctype) if svctype is not None else None
        svcentry['leader'] = term is not None and term.get('name') == name

        # distinguish a newly added service from an existing service which is
        # checking back in ( e.g. a reconnect ). if nothing changed, do not
        # fire any events.
        oldentry = self._getSvcEntry(name)
        if oldentry is not None:

            if (s_common.flatten(svcentry) == s_common.flatten(oldentry) and
                    self._getSvcSess(name) == session):
                return

            evnt = 'svc:mod'

        else:
            evnt = 'svc:add'

        await self._setSvcEntry(svcentry)

        if session is not None:
            await self.slab.put(name.encode(), session.encode(), db='svc:sess')

        for wind in tuple(self.topowindows):
            await wind.put((evnt, {'entry': svcentry}))

        # mostly for testing...
        await self.fire('aha:svc:add', svcentry=svcentry)

    async def getAhaSvcProxy(self, svcentry, timeout=None):

        client = await self.getAhaSvcClient(svcentry)
        if client is None:
            return None

        return await client.proxy(timeout=timeout)

    async def getAhaSvcClient(self, svcentry):

        svcfull = svcentry.get('name')

        client = self.clients.get(svcfull)
        if client is not None:
            return client

        svcurl = self.getAhaSvcUrl(svcentry)

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
        self.slab._put(name.encode(), s_msgpack.en(poolinfo), db='aha:pools')

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

        svcentry = await self._reqAhaSvc(svcname)

        poolinfo = self._loadPoolInfo(poolname)
        poolinfo['services'][svcname] = info

        self._savePoolInfo(poolinfo)

        for wind in self.poolwindows.get(poolname, ()):
            await wind.put(('svc:add', svcentry))

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

    async def _getAhaSvc(self, name):
        # no fancy auto-resolve, just get actual service
        return self._getSvcEntry(name)

    async def _reqAhaSvc(self, svcname):
        svcentry = self._getSvcEntry(svcname)
        if svcentry is None:
            raise s_exc.NoSuchName(mesg=f'No AHA service is currently named "{svcname}".', name=svcname)
        return svcentry

    @s_nexus.Pusher.onPushAuto('aha:svc:del')
    async def delAhaSvc(self, name):

        name = self._getAhaName(name)

        logger.info(f'Deleting service [{name}].', extra=self.getLogExtra(name=name))

        svcentry = self._getSvcEntry(name)

        await self._popSvcEntry(name)

        # drop the online tracking for the removed service.
        self.slab.delete(name.encode(), db='svc:sess')

        await self._fireTopoDel(name)

        # if this was the last service of its type, pop the current leadership
        # term so a future service of that type may start clean as the leader.
        if svcentry is not None:
            svctype = svcentry['info'].get('type')
            if svctype is not None and not self._getSvcNamesByType(svctype):
                self.slab.pop(svctype.encode(), db='aha:lead:term')

        # mostly for testing...
        await self.fire('aha:svc:del', name=name)

    async def setAhaSvcDown(self, name, linkiden):

        name = self._getAhaName(name)

        svcentry = self._getSvcEntry(name)
        if svcentry is None:
            return

        if not svcentry.get('online'):
            return

        await self._push('aha:svc:down', name, linkiden)

    @s_nexus.Pusher.onPush('aha:svc:down')
    async def _setAhaSvcDown(self, name, linkiden):

        name = self._getAhaName(name)

        # compare-and-set: only clear online if it still matches linkiden.
        svcentry = self._getSvcEntry(name)
        if svcentry is not None:

            if self._getSvcSess(name) == linkiden:
                self.slab.delete(name.encode(), db='svc:sess')
                svcentry['online'] = False
                svcentry['info']['ready'] = False
                await self._setSvcEntry(svcentry)
                await self._fireTopoMod(svcentry)

        # Check if we have any links which may need to be removed
        current_sessions = {s_common.guid(iden): sess for iden, sess in self.dmon.sessions.items()}
        sess = current_sessions.get(linkiden)
        if sess is not None:
            for link in [lnk for lnk in self.dmon.links if lnk.get('sess') is sess]:
                await link.fini()

        await self.fire('aha:svc:down', name=name)

        logger.info(f'Set [{name}] offline.', extra=self.getLogExtra(name=name))

        client = self.clients.pop(name, None)
        if client is not None:
            await client.fini()

    async def getAhaSvc(self, name, filters=None):

        name = self._getAhaName(name)

        svcentry = self._getSvcEntry(name)

        if svcentry is not None:

            # if they requested a mirror, try to locate one
            if filters is not None and filters.get('mirror'):

                svcinfo = svcentry.get('info')
                if svcinfo is None: # pragma: no cover
                    return svcentry

                celliden = svcinfo.get('iden')
                mirrors = await self.getAhaSvcMirrors(celliden)

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

            # _getSvcEntry returns a fresh copy, so it is safe to mutate
            svcentry = self._getSvcEntry(random.choice(svcnames))
            svcentry.update(pooldef)

            return svcentry

        # fall back to resolving a bare label as a cell type. this allows
        # aha://<type>... URLs to locate the single instance of a cell type.
        celltype = self._getSvcTypeFromName(name)
        if celltype is not None:
            return await self.getAhaSvcByType(celltype, filters=filters)

        return None

    def _getSvcTypeFromName(self, name):
        # a fully qualified name whose sole label ( minus the network suffix )
        # contains no dots may be resolved as a cell type.
        netw = self.conf.get('aha:network')
        if netw is None: # pragma: no cover
            return None

        suffix = f'.{netw}'
        if not name.endswith(suffix):
            return None

        label = name[:-len(suffix)]
        if not label or '.' in label:
            return None

        return label

    async def getAhaSvcsByType(self, celltype, online=True):
        # yield a single svcentry per instance ( iden ) of a cell type.
        idens = set()

        for svcname in self._getSvcNamesByType(celltype):
            await asyncio.sleep(0)

            svcentry = self._getSvcEntry(svcname)
            if svcentry is None: # pragma: no cover
                continue

            svcinfo = svcentry.get('info')

            if online and not svcentry.get('online'):
                continue

            iden = svcinfo.get('iden')
            if iden in idens:
                continue

            idens.add(iden)
            yield svcentry

    async def getAhaSvcByType(self, celltype, filters=None):
        # return a single connectable svcentry for a cell type. prefer the
        # online leader so that failover follows the active instance.
        for svcname in self._getSvcNamesByType(celltype):

            svcentry = self._getSvcEntry(svcname)
            if svcentry is None: # pragma: no cover
                continue

            svcinfo = svcentry.get('info')

            if not svcentry.get('online'):
                continue

            if not svcentry.get('leader'):
                continue

            if filters is not None and filters.get('mirror'):
                mirrors = await self.getAhaSvcMirrors(svcinfo.get('iden'))
                if mirrors:
                    return random.choice(mirrors)

            return svcentry

        return None

    async def getAhaSvcMirrors(self, iden):

        retn = {}

        for svcname in self._getSvcNamesByIden(iden):

            svcentry = self._getSvcEntry(svcname)
            if svcentry is None: # pragma: no cover
                continue

            svcinfo = svcentry.get('info')

            if not svcentry.get('online'):
                continue

            if not svcinfo.get('ready'):
                continue

            if svcentry.get('leader'):
                continue

            retn[svcinfo.get('run')] = svcentry

        return list(retn.values())

    def _getSvcTypeIndex(self, name):
        byts = self.slab.get(name.encode(), db='svc:type:index')
        if byts is None:
            return 0
        return s_msgpack.un(byts)

    @s_nexus.Pusher.onPush('aha:svc:type:index:set')
    async def _setAhaSvcTypeIndex(self, name, curv, valu):
        # interlocked check-and-set: only update the index if the stored value
        # still matches curv. returns True if the value was updated.
        if self._getSvcTypeIndex(name) != curv:
            return False

        await self.slab.put(name.encode(), s_msgpack.en(valu), db='svc:type:index')
        return True

    async def setAhaSvcTypeIndex(self, name, valu):
        # explicitly set the service type index to valu.
        while not self.isfini:
            curv = self._getSvcTypeIndex(name)
            if await self._push('aha:svc:type:index:set', name, curv, valu):
                return valu

    async def getSvcTypeIndex(self, name):
        # local only: atomically return the next index for a service type and
        # advance the stored value.
        while not self.isfini:
            curv = self._getSvcTypeIndex(name)
            if await self._push('aha:svc:type:index:set', name, curv, curv + 1):
                return curv

    def _getLeadTerm(self, svctype):
        byts = self.slab.get(svctype.encode(), db='aha:lead:term')
        if byts is None:
            return None

        return s_msgpack.un(byts)

    def _getLeadTerms(self, svctype):
        # return the historical terms for a service type in chronological order.
        prefix = svctype.encode() + b'\x00'
        return [s_msgpack.un(byts) for _, byts in self.slab.scanByPref(prefix, db='aha:lead:terms')]

    def _getNextLeadTerm(self, svctype, term, svcname):
        # Return the term, created after the caller's own ( term ), which forked
        # at the lowest service nexus offset, or None. A schism can only occur
        # when the caller *led* its own last acknowledged term ( otherwise it was
        # only ever a follower and never wrote divergent changes ). The history is
        # keyed by AHA's monotonic nexus offset ( stored as the term ``id`` ), so
        # the caller's own id bounds a scan of only the terms created after it. We
        # consider every such later term rather than only the immediately
        # following one, because a lagging peer force-promoted at a low service
        # offset can create a superseding term *after* one at a higher offset. A
        # caller with no known term ( or one lacking an id ) has nothing to anchor
        # against.
        if term is None:
            return None

        termoffs = term.get('id')
        if termoffs is None:  # pragma: no cover
            return None

        # if we did not lead our last term we were only ever a follower and
        # cannot have entered a schism, so we simply follow.
        if term.get('name') != svcname:
            return None

        prefix = svctype.encode() + b'\x00'
        lmin = prefix + s_common.int64en(termoffs + 1)
        lmax = prefix + b'\xff' * 8

        nextterm = None
        for _, byts in self.slab.scanByRange(lmin, lmax, db='aha:lead:terms'):

            later = s_msgpack.un(byts)
            if nextterm is None or later.get('nexsoffs') < nextterm.get('nexsoffs'):
                nextterm = later

        return nextterm

    async def _makeLeadTerm(self, svctype, name, nexsoffs, created, ahaoffs):

        iden = s_common.guid((svctype, name, nexsoffs, created))
        term = {'iden': iden, 'name': name, 'nexsoffs': nexsoffs, 'created': created, 'id': ahaoffs}

        s_schemas.reqValidLeadTerm(term)

        await self.slab.put(svctype.encode(), s_msgpack.en(term), db='aha:lead:term')

        # key the history by our own ( monotonic ) AHA nexus transaction offset,
        # also stored as the term ``id``, so scans walk the terms in the order
        # they were created and a caller can anchor a bounded scan at its own
        # term. the service nexus offset stored in the term ( nexsoffs ) is a
        # different value which is not monotonic across leadership changes.
        lkey = svctype.encode() + b'\x00' + s_common.int64en(ahaoffs)
        await self.slab.put(lkey, s_msgpack.en(term), db='aha:lead:terms')

        # re-flag the registered services of this type so the leader follows the
        # new term ( _setSvcEntry recomputes the leader flag from the term ).
        for svcname in self._getSvcNamesByType(svctype):
            svcentry = self._getSvcEntry(svcname)
            if svcentry is not None:
                await self._setSvcEntry(svcentry)

        # notify topology subscribers of the leadership term change. the term
        # is enveloped ( with its service type ) so the message may carry
        # additional fields in future and clients need not cache the leader.
        for wind in tuple(self.topowindows):
            await wind.put(('svc:lead', {'type': svctype, 'term': term}))

        return term

    async def getLeadTerm(self, svctype):
        # return the current leadership term for a service type ( or None ).
        return self._getLeadTerm(svctype)

    async def promote(self, graceful=False):
        # AHA cells cannot resolve their own leader via aha:// ( they are the
        # registry ), so they follow via an explicit parent. Manage that config
        # directly on promotion rather than relying on dynamic resolution.
        if graceful:
            upstream = self.getParentUrl()
            if upstream is not None:
                myurl = self.getMyUrl()
                logger.warning('PROMOTION: Requesting leadership handoff from the current leader.')
                async with await s_telepath.openurl(upstream) as lead:
                    await lead.handoff(myurl)
                return

        # a promoted AHA cell becomes the leader and follows no upstream; drop the
        # explicit parent so it does not re-follow on restart ( and so the base
        # promotion guard permits the promotion ).
        if self.conf.get('parent') is not None:
            self.modCellConf({'parent': None})

        await s_cell.Cell.promote(self, graceful=graceful)

    async def handoff(self, turl, timeout=30):
        await s_cell.Cell.handoff(self, turl, timeout=timeout)

        # a demoted AHA leader follows the new leader via an explicit ( persisted )
        # parent, since it cannot resolve the leader dynamically via aha://.
        self.modCellConf({'parent': turl})
        await self.nexsroot.startup()

    async def regLeadTerm(self, svctype, svcname, nexsoffs, term=None):
        '''
        Register a service with the leadership term for its service type and
        return the current term. The caller passes its own last acknowledged
        term ( or None ) so the schism check can anchor on it. If the returned
        term name matches svcname, the caller should take leadership. If the
        caller has diverged from the term history, a LeaderSchism error is raised
        and the caller must be restored from a backup.
        '''
        created = s_common.now()

        curterm = await self._push('aha:lead:term:reg', svctype, svcname, nexsoffs, term, created)
        if curterm is None:
            mesg = f'Service {svcname} at nexus offset {nexsoffs} is in schism! Restore from backup!'
            raise s_exc.LeaderSchism(mesg=mesg, svctype=svctype, name=svcname, nexsoffs=nexsoffs)

        return curterm

    @s_nexus.Pusher.onPush('aha:lead:term:reg', passitem=True)
    async def _regLeadTerm(self, svctype, svcname, nexsoffs, term, created, nexsitem):

        curterm = self._getLeadTerm(svctype)

        # if there is no current term or we are the current leader, we ( re )take
        # leadership by creating a new term at our current nexus offset.
        if curterm is None or curterm.get('name') == svcname:
            return await self._makeLeadTerm(svctype, svcname, nexsoffs, created, nexsitem[0])

        # if we have already acknowledged the current term there is no later term
        # to have diverged from, so we simply follow the current leader. this is
        # the common re-registration path and avoids scanning the term history.
        if term is not None and term.get('iden') == curterm.get('iden'):
            return curterm

        # a different service is the current leader and we last acknowledged an
        # older term. if the term which superseded ours began at a nexus offset
        # below ours, we wrote changes a newer leader never saw and have entered
        # a schism ( signalled by None ).
        nextterm = self._getNextLeadTerm(svctype, term, svcname)
        if nextterm is not None and nextterm.get('nexsoffs') < nexsoffs:
            return None

        # otherwise we are safely behind the current leader and join as a mirror.
        return curterm

    async def setLeadTerm(self, svctype, svcname, nexsoffs):
        '''
        Create a new leadership term for a service type. Used to record an API
        driven promotion, whether graceful or forced.
        '''
        created = s_common.now()
        return await self._push('aha:lead:term:set', svctype, svcname, nexsoffs, created)

    @s_nexus.Pusher.onPush('aha:lead:term:set', passitem=True)
    async def _setLeadTerm(self, svctype, svcname, nexsoffs, created, nexsitem):
        return await self._makeLeadTerm(svctype, svcname, nexsoffs, created, nexsitem[0])

    async def getCaCert(self):

        network = self.conf.get('aha:network')
        path = self.certdir.getCaCertPath(network)
        if path is None:
            return None

        with open(path, 'rb') as fd:
            return fd.read()

    async def _initCaCert(self):

        network = self.conf.get('aha:network')
        path = self.certdir.getCaCertPath(network)
        if path is not None:
            return

        logger.info(f'Generating CA certificate for {network}', extra=self.getLogExtra(netw=network))

        pkey, cert = await s_coro.executor(self.certdir.genCaCert, network, save=False)

        cakey = self.certdir._pkeyToByts(pkey).decode()
        cacert = self.certdir._certToByts(cert).decode()

        await self.saveCaCert(network, cakey, cacert)

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

    async def signHostCsr(self, csrtext, sans=None):
        xcsr = self.certdir._loadCsrByts(csrtext.encode())

        hostname = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value

        hostpath = self.certdir.getHostCertPath(hostname)
        if hostpath is not None:
            os.unlink(hostpath)

        logger.info(f'Signing host CSR for [{hostname}], sans={sans}', extra=self.getLogExtra(hostname=hostname))

        signas = self.conf.get('aha:network')
        pkey, cert = self.certdir.signHostCsr(xcsr, signas=signas, sans=sans)

        return self.certdir._certToByts(cert).decode()

    async def signUserCsr(self, csrtext):

        xcsr = self.certdir._loadCsrByts(csrtext.encode())

        username = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value

        userpath = self.certdir.getUserCertPath(username)
        if userpath is not None:
            os.unlink(userpath)

        logger.info(f'Signing user CSR for [{username}]', extra=self.getLogExtra(name=username))

        signas = self.conf.get('aha:network')
        pkey, cert = self.certdir.signUserCsr(xcsr, signas=signas)

        return self.certdir._certToByts(cert).decode()

    async def getAhaUrls(self, user='root'):

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

        conf['parent'] = self.getMyUrl()

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
                     extra=self.getLogExtra(iden=iden, name=host, netw=network))

        return self._getProvClientUrl(iden)

    @s_nexus.Pusher.onPush('aha:clone:add')
    async def _addAhaClone(self, clone):
        iden = clone.get('iden')
        lkey = s_common.uhex(iden)
        await self.slab.put(lkey, s_msgpack.en(clone), db='aha:clones')

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

        ahaurls = await self.getAhaUrls()

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

        conf.setdefault('aha:servers', ahaurls)

        # services connect as the root user, which is already an admin on AHA.

        iden = await self._push('aha:svc:prov:add', provinfo)

        logger.info(f'Created service provisioning for {name}.{netw} with iden {iden}',
                     extra=self.getLogExtra(iden=iden, name=name, netw=netw))

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
        await self.slab.put(iden.encode(), s_msgpack.en(provinfo), db='aha:provs')
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

        userinfo = {
            'name': name,
            'iden': s_common.guid(),
        }

        iden = await self._push('aha:enroll:add', userinfo)

        logger.info(f'Created user provisioning for {name} with iden {iden}',
                     extra=self.getLogExtra(iden=iden, name=name))

        return self._getProvClientUrl(iden)

    async def getAhaUserEnroll(self, iden):
        byts = self.slab.get(iden.encode(), db='aha:enrolls')
        if byts is not None:
            return s_msgpack.un(byts)

    @s_nexus.Pusher.onPush('aha:enroll:add')
    async def _addAhaUserEnroll(self, userinfo):
        iden = userinfo.get('iden')
        await self.slab.put(iden.encode(), s_msgpack.en(userinfo), db='aha:enrolls')
        return iden

    @s_nexus.Pusher.onPushAuto('aha:enroll:del')
    async def delAhaUserEnroll(self, iden):
        self.slab.delete(iden.encode(), db='aha:enrolls')
