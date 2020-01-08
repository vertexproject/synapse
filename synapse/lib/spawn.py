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
import synapse.lib.grammar as s_grammar

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

    user = core.auth.user(useriden)
    if user is None:
        raise s_exc.NoSuchUser(iden=useriden)

    view = core.views.get(viewiden)
    if view is None:
        raise s_exc.NoSuchView(iden=viewiden)

    async for mesg in view.streamstorm(text, opts=opts, user=user):
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

    async with await SpawnCore.anit(spawninfo) as core:

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
            return self.done.get()

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

    async def __anit__(self, spawninfo):

        await s_base.Base.__anit__(self)

        self.pid = os.getpid()
        self.views = {}
        self.layers = {}
        self.spawninfo = spawninfo

        self.conf = spawninfo.get('conf')
        self.iden = spawninfo.get('iden')
        self.dirn = spawninfo.get('dirn')

        self.stormcmds = {}
        self.stormmods = spawninfo['storm']['mods']

        for name, ctor in spawninfo['storm']['cmds']['ctors']:
            self.stormcmds[name] = ctor

        for name, cdef in spawninfo['storm']['cmds']['cdefs']:
            ctor = functools.partial(s_storm.PureCmd, cdef)
            self.stormcmds[name] = ctor

        self.libroot = spawninfo.get('storm').get('libs')

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss.fini)

        self.model = s_datamodel.Model()
        self.model.addDataModels(spawninfo.get('model'))

        self.prox = await s_telepath.openurl(f'cell://{self.dirn}')
        self.onfini(self.prox.fini)

        self.hive = await s_hive.openurl(f'cell://{self.dirn}', name='*/hive')
        self.onfini(self.hive)

        # TODO cortex configured for remote auth...
        node = await self.hive.open(('auth',))
        self.auth = await s_hive.HiveAuth.anit(node)
        self.onfini(self.auth.fini)

        for layrinfo in self.spawninfo.get('layers'):

            iden = layrinfo.get('iden')
            path = ('cortex', 'layers', iden)

            ctorname = layrinfo.get('ctor')

            ctor = s_dyndeps.tryDynLocal(ctorname)

            node = await self.hive.open(path)
            layr = await ctor(self, node, readonly=True)

            self.onfini(layr)

            self.layers[iden] = layr

        for viewinfo in self.spawninfo.get('views'):

            iden = viewinfo.get('iden')
            path = ('cortex', 'views', iden)

            node = await self.hive.open(path)
            view = await s_view.View.anit(self, node)

            self.onfini(view)

            self.views[iden] = view

        # initialize pass-through methods from the telepath proxy
        # Lift
        self.runRuntLift = self.prox.runRuntLift
        # StormType Queue APIs
        self.addCoreQueue = self.prox.addCoreQueue
        self.hasCoreQueue = self.prox.hasCoreQueue
        self.delCoreQueue = self.prox.delCoreQueue
        self.getCoreQueue = self.prox.getCoreQueue
        self.getCoreQueues = self.prox.getCoreQueues
        self.getsCoreQueue = self.prox.getsCoreQueue
        self.putCoreQueue = self.prox.putCoreQueue
        self.putsCoreQueue = self.prox.putsCoreQueue
        self.cullCoreQueue = self.prox.cullCoreQueue
        # Feedfunc support
        self.getFeedFuncs = self.prox.getFeedFuncs
        # storm pkgfuncs
        self.addStormPkg = self.prox.addStormPkg
        self.delStormPkg = self.prox.delStormPkg
        self.getStormPkgs = self.prox.getStormPkgs

        # TODO: Add Dmon management functions ($lib.dmon support)
        # TODO: Add Axon management functions ($lib.bytes support)

    def getStormQuery(self, text):
        '''
        Parse storm query text and return a Query object.
        '''
        query = s_grammar.Parser(text).query()
        query.init(self)
        return query

    def _logStormQuery(self, text, user):
        '''
        Log a storm query.
        '''
        if self.conf.get('storm:log'):
            lvl = self.conf.get('storm:log:level')
            logger.log(lvl, 'Executing spawn storm query {%s} as [%s] from [%s]', text, user.name, self.pid)

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    async def getStormMods(self):
        return self.stormmods

    def getStormLib(self, path):
        root = self.libroot
        for name in path:
            step = root[1].get(name)
            if step is None:
                return None
            root = step
        return root
