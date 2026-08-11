'''
Boot a multi-service topology ( eg a Cortex with its axon / jsonstor peers, plus
any additional Storm services ) on a single ephemeral AHA network.
'''
import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.common as s_common

import synapse.lib.aha as s_aha
import synapse.lib.base as s_base
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.msgpack as s_msgpack

@contextlib.contextmanager
def _mayDir(dirn):
    # a bare-bones, framework-agnostic equivalent of SynTest.mayTestDir(): use
    # dirn as-is if given, else make ( and clean up ) an ephemeral one.
    if dirn is not None:
        yield dirn
        return

    with s_common.getTempDir() as dirn:
        yield dirn

@contextlib.asynccontextmanager
async def bootAha(conf=None, dirn=None, ctor=None):
    '''
    Boot an AHA cell suitable for use as a Cluster's own network.

    Args:
        conf (dict): Conf overrides for the AHA cell boot.
        dirn (str): Directory to boot the cell in. An ephemeral one is created
            ( and cleaned up ) if not given.
        ctor: The AHA cell ctor. Defaults to ``synapse.lib.aha.AhaCell.anit``.

    Yields:
        The booted AhaCell.
    '''
    if conf is None:
        conf = {}

    if ctor is None:
        ctor = s_aha.AhaCell.anit

    conf = s_msgpack.deepcopy(conf)

    hasdmonlisn = 'dmon:listen' in conf
    hasprovlisn = 'provision:listen' in conf

    network = conf.setdefault('aha:network', 'synapse')
    hostname = conf.setdefault('dns:name', '000.aha.loop.vertex.link')

    if hostname:
        conf.setdefault('provision:listen', f'ssl://0.0.0.0:0?hostname={hostname}')
        conf.setdefault('dmon:listen', f'ssl://0.0.0.0:0?hostname={hostname}&ca={network}')

    conf.setdefault('health:sysctl:checks', False)

    with _mayDir(dirn) as dirn:

        async with await ctor(dirn, conf=conf) as aha:

            mods = {}
            if not hasdmonlisn and hostname:
                mods['dmon:listen'] = f'ssl://0.0.0.0:{aha.sockaddr[1]}?hostname={hostname}&ca={network}'

            if not hasprovlisn and hostname:
                mods['provision:listen'] = f'ssl://0.0.0.0:{aha.provaddr[1]}?hostname={hostname}'

            if mods:
                aha.modCellConf(mods)

            # an active AHA leader self-registers 000.aha ( over a dns:name
            # link ) via an active coro; wait for it before yielding so a
            # caller counting aha:svc:add events or listing services is not
            # racing the leader's own registration. followers/clones skip
            # self-registration.
            if aha.isactive and (ahaname := aha.conf.get('aha:name')) is not None:
                await aha._waitAhaSvcOnline(f'{ahaname}...', timeout=12)

            yield aha

class Cluster(s_base.Base):
    '''
    Holds the set of services booted by getCluster().

    A Base which owns the fini() teardown of the booted services. Exposes one
    attribute per service type ( the leader instance, eg ``clus.cortex`` /
    ``clus.axon`` / ``clus.search`` ) and a ``svcs`` dict keyed by AHA short
    name ( eg ``000.cortex`` / ``001.cortex`` ) for reaching individual
    instances such as mirrors.

    Additional services can be booted onto the same AHA network after creation
    with addSvc(), which awaits their discovery so a caller may immediately use
    or watch them. Each service lives in a predictable directory under the
    cluster dir ( see getSvcDirn() ), so a caller may pre-populate a service
    dir before boot, and restart() can fini and re-boot a service from the
    same directory.
    '''
    async def __anit__(self, dirn):
        await s_base.Base.__anit__(self)
        self.dirn = dirn    # the cluster storage directory
        self.aha = None
        self.svcs = {}      # aha short name -> cell
        self.bytype = {}    # celltype -> leader cell
        self.counts = {}    # celltype -> number of instances booted
        self.svcinfo = {}   # aha short name -> boot info for restart()

    def __getattr__(self, name):
        bytype = self.__dict__.get('bytype')
        if bytype is not None and name in bytype:
            return bytype[name]

        raise AttributeError(name)

    def get(self, celltype):
        return self.bytype.get(celltype)

    def getLocalUrl(self, celltype='cortex'):
        return self.bytype[celltype].getLocalUrl()

    def getSvcDirn(self, svcname):
        '''
        Return the on-disk directory for a service by its AHA short name ( eg
        ``000.cortex`` / ``001.search`` ). The convention is stable, so a
        caller which passed an explicit ``dirn`` to getCluster() may
        pre-populate a service directory ( eg restore a backup ) before the
        service boots.
        '''
        return s_common.genpath(self.dirn, svcname)

    @contextlib.asynccontextmanager
    async def proxy(self, celltype='cortex'):
        async with self.bytype[celltype].getLocalProxy() as prox:
            yield prox

    async def _waitSvcReady(self, celltype, cell, leader, timeout=15):
        if not leader:
            # a same-type mirror follows the leader of its cell type
            await asyncio.wait_for(cell.nexsroot.ready.wait(), timeout=12)
            return

        # a booted Storm service is auto-discovered by an active Cortex via AHA;
        # wait for the Cortex to add it so the cluster is ready to use.
        core = self.bytype.get('cortex')
        if core is not None and cell is not core and cell.features.get('stormservice'):
            await core.waitStormSvc(celltype, timeout=timeout)

    async def _addSvcToAha(self, svcname, ctor, conf=None, provinfo=None):
        '''
        Provision and boot a service ( in its getSvcDirn() ) into the cluster's
        AHA network and return the booted cell. The cluster owns the cell's
        teardown.
        '''
        aha = self.aha
        onetime = await aha.addAhaSvcProv(svcname, provinfo=provinfo)

        conf = dict(conf) if conf else {}
        conf.setdefault('health:sysctl:checks', False)
        conf['aha:provision'] = onetime

        dirn = self.getSvcDirn(svcname)
        s_common.yamlsave(conf, dirn, 'cell.yaml')

        cell = await self.enter_context(await ctor.anit(dirn))
        await aha._waitAhaSvcOnline(f'{svcname}...', timeout=10)

        return cell

    async def addSvc(self, ctor, conf=None, timeout=15):
        '''
        Boot a service onto the cluster's AHA network and return the booted cell.
        The service type is taken from ``ctor.getCellType()``. The first instance
        of a type is its leader ( reachable as ``clus.<celltype>`` ); each
        subsequent same-type instance follows it as a mirror ( reachable by AHA
        short name in ``svcs`` ).

        The boot is not considered complete until the service is usable: a
        Storm service leader is awaited until the Cortex has auto-discovered it
        via AHA, and a mirror is awaited until its nexus is caught up.

        Note:
            This is for a caller that must add a service dynamically ( eg after
            manipulating the cluster, or to observe discovery ). Most callers
            should instead declare the whole service topology up front in the
            getCluster() ``svcs`` argument.

        Args:
            ctor: The cell class to boot.
            conf (dict): Optional service config.
            timeout (int): Seconds to wait for storm-svc discovery.
        '''
        celltype = ctor.getCellType()

        indx = self.counts.get(celltype, 0)
        self.counts[celltype] = indx + 1

        svcname = f'{indx:03d}.{celltype}'
        leader = indx == 0

        cell = await self._addSvcToAha(svcname, ctor, conf=conf)

        self.svcs[svcname] = cell
        self.svcinfo[svcname] = {'celltype': celltype, 'ctor': ctor, 'leader': leader}

        if leader:
            self.bytype[celltype] = cell

        await self._waitSvcReady(celltype, cell, leader, timeout=timeout)

        return cell

    def _reqSvcInfo(self, svcname):
        info = self.svcinfo.get(svcname)
        if info is None:
            mesg = f'getCluster() has no such service: {svcname}'
            raise s_exc.BadArg(mesg=mesg, svcname=svcname)

        return info

    async def shutdown(self, svcname):
        '''
        Fini the named service instance, leaving its storage directory intact so
        a caller may inspect or manipulate it by hand before a startup()/restart().

        Args:
            svcname (str): The AHA short name of the service ( eg ``000.search`` ).
        '''
        self._reqSvcInfo(svcname)

        cell = self.svcs.get(svcname)
        if cell is not None and not cell.isfini:
            await cell.fini()

    async def startup(self, svcname):
        '''
        Boot a fresh instance of a previously added service from its storage
        directory ( which keeps its persisted iden and AHA config ), awaiting its
        return to the AHA network. Returns the new cell.

        Args:
            svcname (str): The AHA short name of the service ( eg ``000.search`` ).
        '''
        info = self._reqSvcInfo(svcname)

        cell = await self.enter_context(await info['ctor'].anit(self.getSvcDirn(svcname)))

        self.svcs[svcname] = cell
        if info['leader']:
            self.bytype[info['celltype']] = cell

        await self.aha._waitAhaSvcOnline(f'{svcname}...', timeout=10)
        await self._waitSvcReady(info['celltype'], cell, info['leader'])

        return cell

    async def restart(self, svcname):
        '''
        Fini the named service and boot a fresh instance from the same storage
        directory, awaiting its return to the AHA network. Equivalent to a
        shutdown() followed by a startup(). Returns the new cell.

        Args:
            svcname (str): The AHA short name of the service ( eg ``000.search`` ).
        '''
        await self.shutdown(svcname)
        return await self.startup(svcname)

@contextlib.asynccontextmanager
async def getCluster(svcs=None, dirn=None, ahaconf=None):
    '''
    Boot a set of services on a single AHA network under one temp dir.

    Args:
        svcs (dict): Maps a service type ( eg 'cortex', 'axon', 'search' ) to
            an envelope dict with keys ``conf`` ( the service config dict ),
            ``ctor`` ( the cell ctor to boot -- required, except for the
            'axon'/'jsonstor' peers implicitly added for a 'cortex' entry
            that does not specify its own ), and ``mirrors`` ( the number of
            mirrors to boot alongside the leader; defaults to 0, ie leader
            only ). The special key ``aha`` configures the AHA cell via a
            ``conf`` envelope; an AHA network is always created. Defaults to
            a single 'cortex' entry using the base ``synapse.cortex.Cortex``.
        dirn (str): Optional base directory for all services.
        ahaconf (dict): Conf defaults for the AHA cell, merged under any
            ``svcs['aha']['conf']`` ( which wins on key conflicts ).

    Notes:
        Services locate their peers by cell type via AHA. Requesting a
        'cortex' implicitly also boots an 'axon' and 'jsonstor' ( the base
        synapse ctors, unless the caller supplied its own envelope for
        either ). Any deployed Storm service is auto-discovered by the
        Cortex via AHA. Additional services may be booted onto the same
        network afterwards with the returned cluster's addSvc() method.

    Yields:
        Cluster: An object exposing the booted services ( one attribute per
        service type for the leader, plus a ``svcs`` dict keyed by AHA name ).
    '''
    if svcs is None:
        svcs = {'cortex': {'ctor': s_cortex.Cortex}}

    svcs = {celltype: (dict(env) if env is not None else None)
            for (celltype, env) in svcs.items()}

    # getCluster() always boots an AHA network; it cannot be disabled.
    ahaenv = svcs.pop('aha', {})
    if ahaenv is None:
        mesg = 'getCluster() always uses AHA; the network cannot be disabled.'
        raise s_exc.BadArg(mesg=mesg)

    ahaconf = dict(ahaconf or {})
    ahaconf.update(ahaenv.get('conf') or {})

    # a cortex locates its axon and jsonstor peers by cell type via AHA
    if 'cortex' in svcs:
        svcs.setdefault('axon', {'ctor': s_axon.Axon})
        svcs.setdefault('jsonstor', {'ctor': s_jsonstor.JsonStorCell})

    # boot peers before the services which discover them
    order = ('axon', 'jsonstor', 'cortex')
    celltypes = [t for t in order if t in svcs]
    celltypes.extend([t for t in svcs if t not in order])

    with _mayDir(dirn) as dirn:

        async with await Cluster.anit(dirn) as clus:

            clus.aha = await clus.enter_context(
                bootAha(conf=ahaconf, dirn=s_common.genpath(dirn, '000.aha')))

            for celltype in celltypes:

                env = svcs[celltype] or {}

                extra = set(env) - {'conf', 'ctor', 'mirrors'}
                if extra:
                    mesg = f'getCluster() service {celltype} has invalid envelope keys: {sorted(extra)}'
                    raise s_exc.BadArg(mesg=mesg)

                conf = env.get('conf') or {}
                mirrors = env.get('mirrors', 0)
                ctor = env.get('ctor')
                if ctor is None:
                    mesg = f'getCluster() service {celltype} requires an explicit ctor.'
                    raise s_exc.BadArg(mesg=mesg, celltype=celltype)

                # boot the leader ( first instance ) plus ``mirrors`` mirrors;
                # addSvc() promotes the first to leader and follows it with
                # each subsequent same-type instance as a mirror.
                for _ in range(1 + mirrors):
                    await clus.addSvc(ctor, conf=conf)

            yield clus
