import time
import asyncio

import synapse.common as s_common

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
