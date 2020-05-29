'''
Spawn is mechanism so that a cortex can execute different queries in separate processes
'''

import os
import asyncio
import logging
import functools
import threading
import contextlib
import collections
import multiprocessing
import concurrent.futures

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.coro as s_coro
import synapse.lib.hive as s_hive
import synapse.lib.link as s_link
import synapse.lib.view as s_view
import synapse.lib.storm as s_storm
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.hiveauth as s_hiveauth

logger = logging.getLogger(__name__)

async def storm(core, item):
    '''
    Storm implementation for SpawnCore use.
    '''
    useriden = item.get('user')
    viewiden = item.get('view')

    storminfo = item.get('storm')

    opts = storminfo.get('opts')
    text = storminfo.get('query')

    if opts is None:
        opts = {}

    user = core.auth.user(useriden)
    if user is None:
        raise s_exc.NoSuchUser(iden=useriden)

    view = core.views.get(viewiden)
    if view is None:
        raise s_exc.NoSuchView(iden=viewiden)

    opts['user'] = useriden
    async for mesg in view.storm(text, opts=opts):
        yield mesg

async def _innerloop(core, todo, done):
    '''
    Inner loop for the multiprocessing target code.

    Args:
        spawninfo (dict): Spawninfo dictionary.
        todo (multiprocessing.Queue): RX Queue
        done (multiprocessing.Queue): TX Queue

    Returns:
        None: Returns None.
    '''
    item = await s_coro.executor(todo.get)
    if item is None:
        return

    link = await s_link.fromspawn(item.get('link'))

    await s_daemon.t2call(link, storm, (core, item,), {})

    wasfini = link.isfini

    await link.fini()

    await s_coro.executor(done.put, wasfini)

    return True

async def _workloop(spawninfo, todo, done):
    '''
    Workloop executed by the multiprocessing target.

    Args:
        spawninfo (dict): Spawninfo dictionary.
        todo (multiprocessing.Queue): RX Queue
        done (multiprocessing.Queue): TX Queue

    Returns:
        None: Returns None.
    '''
    s_glob.iAmLoop()

    ctorname = spawninfo.get('spawncorector')
    ctor = s_dyndeps.tryDynLocal(ctorname)

    async with await ctor.anit(spawninfo) as core:

        while not core.isfini:

            if not await _innerloop(core, todo, done):
                break

def corework(spawninfo, todo, done):
    '''
    Multiprocessing target for hosting a SpawnCore launched by a SpawnProc.
    '''

    # This logging call is okay to run since we're executing in
    # our own process space and no logging has been configured.
    s_common.setlogging(logger, spawninfo.get('loglevel'))

    asyncio.run(_workloop(spawninfo, todo, done))

class SpawnProc(s_base.Base):
    '''
    '''
    async def __anit__(self, core):

        await s_base.Base.__anit__(self)

        self.core = core
        self.iden = s_common.guid()
        self.proc = None

        self.ready = asyncio.Event()
        self.mpctx = multiprocessing.get_context('spawn')

        name = f'SpawnProc#{self.iden[:8]}'
        self.threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix=name)

        self.todo = self.mpctx.Queue()
        self.done = self.mpctx.Queue()
        self.proc = None  # type: multiprocessing.Process
        self.procstat = None
        self.obsolete = False

        spawninfo = await core.getSpawnInfo()
        self.finievent = threading.Event()

        @s_common.firethread
        def procwaiter():
            '''
            Wait for child process to exit
            '''
            self.procstat = self.proc.join()
            self.proc.close()
            if not self.isfini:
                self.schedCoroSafe(self.fini())

        @s_common.firethread
        def finiwaiter():
            '''
            Wait for the SpawnProc to complete on another thread (so we can block)
            '''
            self.finievent.wait()
            self.todo.put(None)
            self.todo.close()
            self.done.put(None)
            self.done.close()
            self.todo.join_thread()
            self.done.join_thread()
            if self.procstat is None:
                try:
                    self.proc.terminate()
                except ValueError:
                    pass
            self.threadpool.shutdown()

        # avoid blocking the ioloop during process construction
        def getproc():
            self.proc = self.mpctx.Process(target=corework, args=(spawninfo, self.todo, self.done))
            self.proc.start()

        await self.executor(getproc)
        finiwaiter()
        procwaiter()

        async def fini():
            self.obsolete = True
            self.finievent.set()

        self.onfini(fini)

    def __repr__(self):  # pragma: no cover
        info = [self.__class__.__module__ + '.' + self.__class__.__name__]
        info.append(f'at {hex(id(self))}')
        info.append(f'isfini={self.isfini}')
        info.append(f'iden={self.iden}')
        info.append(f'obsolete={self.obsolete}')
        if self.proc and not self.proc._closed:
            info.append(f'proc={self.proc.pid}')
        else:
            info.append('proc=None')
        return '<{}>'.format(' '.join(info))

    async def retire(self):
        logger.debug(f'Proc {self} marked obsolete')
        self.obsolete = True

    async def xact(self, mesg):

        def doit():
            self.todo.put(mesg)
            try:
                return self.done.get()
            except (TypeError, OSError) as e:
                logger.warning('Queue torn out from underneath me. (%s)', e)
                assert self.isfini
                return True

        return await self.executor(doit)

    def executor(self, func, *args, **kwargs):
        def real():
            return func(*args, **kwargs)

        return asyncio.get_running_loop().run_in_executor(self.threadpool, real)

class SpawnPool(s_base.Base):

    async def __anit__(self, core):

        await s_base.Base.__anit__(self)

        self.core = core

        self.poolsize = await core.getConfOpt('spawn:poolsize')

        self.spawns = {}
        self.spawnq = collections.deque()

        async def fini():
            await self.kill()

        self.onfini(fini)

    async def bump(self):
        if not self.spawns:
            return
        [await s.retire() for s in list(self.spawns.values())]
        [await s.fini() for s in self.spawnq]
        self.spawnq.clear()

    async def kill(self):
        if not self.spawns:
            return
        self.spawnq.clear()
        [await s.fini() for s in list(self.spawns.values())]

    @contextlib.asynccontextmanager
    async def get(self):
        '''
        Get a SpawnProc instance; either from the pool or a new process.

        Returns:
            SpawnProc: Yields a SpawnProc.  This is placed back into the pool if no exceptions occur.
        '''

        if self.isfini: # pragma: no cover
            raise s_exc.IsFini()

        proc = None

        if self.spawnq:
            proc = self.spawnq.popleft()

        if proc is None:
            proc = await self._new()

        yield proc

        await self._put(proc)

    async def _put(self, proc):

        if not proc.obsolete and len(self.spawnq) < self.poolsize:
            self.spawnq.append(proc)
            return

        await proc.fini()

    async def _new(self):

        proc = await SpawnProc.anit(self.core)

        logger.debug(f'Made new SpawnProc {proc}')

        self.spawns[proc.iden] = proc

        async def fini():
            self.spawns.pop(proc.iden, None)

        proc.onfini(fini)

        return proc

class SpawnCore(s_base.Base):
    '''
    A SpawnCore instance is the substitute for a Cortex in non-cortex processes
    '''

    async def __anit__(self, spawninfo):

        await s_base.Base.__anit__(self)

        self.pid = os.getpid()
        self.views = {}
        self.layers = {}
        self.nexsroot = None
        self.isleader = False
        self.spawninfo = spawninfo

        self.conf = spawninfo.get('conf')
        self.iden = spawninfo.get('iden')
        self.dirn = spawninfo.get('dirn')

        self.trigson = self.conf.get('trigger:enable')

        self.svcsbyiden = {}
        self.svcsbyname = {}

        self.stormcmds = {}
        self.storm_cmd_ctors = {}
        self.storm_cmd_cdefs = {}
        self.stormmods = spawninfo['storm']['mods']
        self.pkginfo = spawninfo['storm']['pkgs']
        self.svcinfo = spawninfo['storm']['svcs']

        self.model = s_datamodel.Model()
        self.model.addDataModels(spawninfo.get('model'))

        self.stormpkgs = {}     # name: pkgdef
        await self._initStormCmds()

        for sdef in self.svcinfo:
            await self._addStormSvc(sdef)

        for pkgdef in self.pkginfo:
            await self._tryLoadStormPkg(pkgdef)

        for name, ctor in spawninfo['storm']['cmds']['ctors']:
            self.stormcmds[name] = ctor

        for name, cdef in spawninfo['storm']['cmds']['cdefs']:
            self.storm_cmd_cdefs[name] = cdef

        self.libroot = spawninfo.get('storm').get('libs')

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss.fini)

        self.prox = await s_telepath.openurl(f'cell://{self.dirn}')
        self.onfini(self.prox.fini)

        self.hive = await s_hive.openurl(f'cell://{self.dirn}', name='*/hive')
        self.onfini(self.hive)

        node = await self.hive.open(('auth',))
        self.auth = await s_hiveauth.Auth.anit(node)
        self.onfini(self.auth.fini)
        for layrinfo in self.spawninfo.get('layers'):
            await self._initLayr(layrinfo)

        for viewinfo in self.spawninfo.get('views'):

            iden = viewinfo.get('iden')
            path = ('cortex', 'views', iden)

            node = await self.hive.open(path)
            view = await s_view.View.anit(self, node)

            self.onfini(view)

            self.views[iden] = view

        for view in self.views.values():
            view.init2()

        self.addStormDmon = self.prox.addStormDmon
        self.delStormDmon = self.prox.delStormDmon
        self.getStormDmon = self.prox.getStormDmon
        self.getStormDmons = self.prox.getStormDmons

    async def _initLayr(self, layrinfo):
        iden = layrinfo.get('iden')
        ctorname = layrinfo.get('ctor')

        ctor = s_dyndeps.tryDynLocal(ctorname)

        layrinfo['readonly'] = True

        layr = await self._ctorLayr(ctor, layrinfo)

        self.onfini(layr)

        self.layers[iden] = layr

    async def _ctorLayr(self, ctor, layrinfo):
        iden = layrinfo.get('iden')
        layrdirn = s_common.genpath(self.dirn, 'layers', iden)
        layr = await ctor.anit(layrinfo, layrdirn)
        return layr

    async def dyncall(self, iden, todo, gatekeys=()):
        return await self.prox.dyncall(iden, todo, gatekeys=gatekeys)

    async def dyniter(self, iden, todo, gatekeys=()):
        async for item in self.prox.dyniter(iden, todo, gatekeys=gatekeys):
            yield item

    def _logStormQuery(self, text, user):
        '''
        Log a storm query.
        '''
        if self.conf.get('storm:log'):
            lvl = self.conf.get('storm:log:level')
            logger.log(lvl, 'Executing spawn storm query {%s} as [%s] from [%s]', text, user.name, self.pid)

    async def addStormPkg(self, pkgdef):
        '''
        Do it for the proxy, then myself
        '''
        todo = s_common.todo('addStormPkg', pkgdef)
        await self.dyncall('cortex', todo)

        await self.loadStormPkg(pkgdef)

    async def delStormPkg(self, name):
        '''
        Do it for the proxy, then myself
        '''
        todo = s_common.todo('delStormPkg', name)
        await self.dyncall('cortex', todo)

        pkgdef = self.stormpkgs.get(name)
        if pkgdef is None:
            return

        await self._dropStormPkg(pkgdef)

    async def bumpSpawnPool(self):
        pass

    async def getStormPkgs(self):
        return list(self.stormpkgs.values())

    async def _addStormSvc(self, sdef):

        iden = sdef.get('iden')
        ssvc = self.svcsbyiden.get(iden)
        if ssvc is not None:
            return ssvc.sdef

        ssvc = await self._setStormSvc(sdef)

        return ssvc.sdef

    async def _delStormSvcPkgs(self, iden):
        '''
        For now don't actually run this in the spawn case. This only needs to be
        done in the master Cortex, not in spawns. Deleting a storm service package
        from a spawn should not be making persistent changes.
        '''
        pass

    async def _hndladdStormPkg(self, pdef):
        '''
        For now don't actually run this in the spawn case. This only needs to be
        done in the master Cortex, not in spawns. Adding a storm service package
        from a spawn should not be making persistent changes.
        '''
        # Note - this represents the bottom half of addStormPkg which is made
        # via the @s_nexus.Pusher.onPushAuto('pkg:add') decorator.
        pass

    async def setStormSvcEvents(self, iden, edef):
        svc = self.svcsbyiden.get(iden)
        if svc is None:
            mesg = f'No storm service with iden: {iden}'
            raise s_exc.NoSuchStormSvc(mesg=mesg)

        sdef = svc.sdef

        sdef['evts'] = edef
        return sdef

    # A little selective inheritance
    # TODO:  restructure cortex to avoid this hackery
    _setStormSvc = s_cortex.Cortex._setStormSvc
    _confirmStormPkg = s_cortex.Cortex._confirmStormPkg
    _dropStormPkg = s_cortex.Cortex._dropStormPkg
    _reqStormCmd = s_cortex.Cortex._reqStormCmd
    _setStormCmd = s_cortex.Cortex._setStormCmd
    _tryLoadStormPkg = s_cortex.Cortex._tryLoadStormPkg
    _trySetStormCmd = s_cortex.Cortex._trySetStormCmd
    addStormCmd = s_cortex.Cortex.addStormCmd
    getDataModel = s_cortex.Cortex.getDataModel
    getStormCmd = s_cortex.Cortex.getStormCmd
    getStormCmds = s_cortex.Cortex.getStormCmds
    getStormLib = s_cortex.Cortex.getStormLib
    getStormMods = s_cortex.Cortex.getStormMods
    getStormPkg = s_cortex.Cortex.getStormPkg
    getStormQuery = s_cortex.Cortex.getStormQuery
    getStormSvc = s_cortex.Cortex.getStormSvc
    loadStormPkg = s_cortex.Cortex.loadStormPkg

    _initStormCmds = s_cortex.Cortex._initStormCmds
    _initStormOpts = s_cortex.Cortex._initStormOpts

    _viewFromOpts = s_cortex.Cortex._viewFromOpts
    _userFromOpts = s_cortex.Cortex._userFromOpts
    getView = s_cortex.Cortex.getView
