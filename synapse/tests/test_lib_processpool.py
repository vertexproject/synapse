import gc
import time
import signal
import asyncio
import weakref
import multiprocessing

from unittest import mock

import synapse.common as s_common

import synapse.lib.logging as s_logging
import synapse.lib.process as s_process
import synapse.lib.processpool as s_processpool

import synapse.tests.utils as s_t_utils

class FakeError(Exception): pass

def spawnfunc(x, y=10):
    return x + y

def spawntime(n):
    time.sleep(n)
    return s_common.now()

def spawnfakeit():
    raise FakeError()

def chkpool():
    return s_processpool.forkpool is None

def spawn_initpool():
    # a spawned (non-MainProcess) process gets no forkpool at import; set a
    # logconf first to exercise the re-apply path, then confirm idempotency.
    before = s_processpool.forkpool is None
    s_processpool._pool_logconf = {}
    s_processpool.initForkPool()
    pool = s_processpool.forkpool
    inited = pool is not None and pool._initializer is not None
    s_processpool.initForkPool()
    same = s_processpool.forkpool is pool
    return (before, inited, same)

class ProcessTest(s_t_utils.SynTest):

    async def test_lib_process_forked(self):

        self.true(await s_processpool.forked(chkpool))

        self.eq(50, await s_processpool.forked(spawnfunc, 20, y=30))

        with self.raises(FakeError):
            await s_processpool.forked(spawnfakeit)

        self.eq(50, await s_processpool.forked(spawnfunc, 20, y=30))

        def newp():
            return 23

        with self.raises(Exception):
            await s_processpool.forked(newp)

        oldpool = s_processpool.forkpool
        s_processpool.forkpool = None

        try:
            self.eq(50, await s_processpool.forked(spawnfunc, 20, y=30))
        finally:
            s_processpool.forkpool = oldpool

    async def test_lib_process_init_child(self):
        # a spawn()ed child does not get the MainProcess import-time forkpool;
        # initForkPool() stands one up in-process so its CPU-bound work uses the
        # pool rather than a per-call spawn.
        retn = await s_process.spawn((spawn_initpool, (), {}), timeout=60)
        self.eq((True, True, True), retn)

    async def test_lib_process_init_pool_worker(self):

        # _initPoolWorker is what a pool worker runs on startup once a log config is
        # in hand: it applies that config and leaves SIGINT to the process owning the
        # pool. s_logging.setup() is mocked because it reconfigures logging for the
        # whole process, which a worker wants and this test does not.
        oldhandler = signal.getsignal(signal.SIGINT)

        try:
            with mock.patch.object(s_logging, 'setup') as fakesetup:

                s_processpool._initPoolWorker({'defval': 'debug'})

                self.eq(1, fakesetup.call_count)
                self.eq({'defval': 'debug'}, fakesetup.call_args.kwargs)

            self.eq(signal.SIG_IGN, signal.getsignal(signal.SIGINT))

        finally:
            signal.signal(signal.SIGINT, oldhandler)

    async def test_lib_process_fini_pool(self):

        # A process that owns its pool releases it from its own teardown, since a
        # signalled process never reaches atexit. Released means the executor is
        # really deallocated, which is what frees the five named semaphores its
        # queues hold, so the bound method initForkPool gave atexit comes back too.
        try:
            s_processpool.initForkPool()

            pool = s_processpool.forkpool
            self.nn(pool)

            poolref = weakref.ref(pool)

            # a pool worker only exists once something has run through the pool
            self.eq(50, await s_processpool.forked(spawnfunc, 20, y=30))

            s_processpool.finiForkPool()

            self.none(s_processpool.forkpool)
            self.none(s_processpool.forkpool_sema)
            self.none(s_processpool.max_workers)

            # idempotent
            s_processpool.finiForkPool()

            del pool
            gc.collect()

            # anything still holding the executor keeps its semaphores with it
            self.none(poolref())

        finally:
            # the pool is per process and the rest of the suite shares it
            s_processpool.initForkPool()

    async def test_lib_process_main_import_guard(self):
        # The auto-init fires in a real MainProcess and nowhere else, which keeps a
        # process to one pool. A forkserver is also named MainProcess and imports its
        # parent's main module, so the _inheriting window has to read as "not main".
        proc = multiprocessing.current_process()

        self.true(s_processpool._isMainImport())

        # the window where a child re-imports the main module
        proc._inheriting = True
        try:
            self.false(s_processpool._isMainImport())
        finally:
            del proc._inheriting

        self.true(s_processpool._isMainImport())

        # anything not named MainProcess never auto-inits, inheriting or not
        with mock.patch.object(proc, '_name', 'ForkServerProcess-1'):
            self.false(s_processpool._isMainImport())

    async def test_lib_process_semafork(self):

        oldsema = s_processpool.forkpool_sema
        self.true(isinstance(oldsema, asyncio.Semaphore))

        try:

            s_processpool.forkpool_sema = asyncio.Semaphore(1)

            async with asyncio.TaskGroup() as tg:
                task0 = tg.create_task(s_processpool.semafork(spawntime, 1.1))
                task1 = tg.create_task(s_processpool.semafork(spawntime, 1.1))

            self.gt(abs(await task1 - await task0), 1_000)

            s_processpool.forkpool_sema = None

            self.eq(50, await s_processpool.semafork(spawnfunc, 20, y=30))

        finally:

            s_processpool.forkpool_sema = oldsema

    async def test_lib_process_parserforked(self):

        self.true(await s_processpool._parserforked(chkpool))

        self.eq(50, await s_processpool._parserforked(spawnfunc, 20, y=30))

        with self.raises(FakeError):
            await s_processpool._parserforked(spawnfakeit)

        self.eq(50, await s_processpool._parserforked(spawnfunc, 20, y=30))

        def newp():
            return 23

        with self.raises(Exception):
            await s_processpool._parserforked(newp)

    async def test_lib_process_parserforked_nopool(self):
        # a spawned worker never creates the forkpool (only MainProcess does), so
        # the concurrent.futures.process submodule may be unbound. _parserforked
        # must still run via the default executor and propagate real exceptions
        # rather than masking them with an AttributeError on the missing submodule.
        import concurrent.futures

        oldpool = s_processpool.forkpool
        realproc = getattr(concurrent.futures, 'process', None)

        s_processpool.forkpool = None
        try:
            if realproc is not None:
                delattr(concurrent.futures, 'process')

            self.eq(50, await s_processpool._parserforked(spawnfunc, 20, y=30))

            with self.raises(FakeError):
                await s_processpool._parserforked(spawnfakeit)

        finally:
            if realproc is not None:
                concurrent.futures.process = realproc
            s_processpool.forkpool = oldpool
