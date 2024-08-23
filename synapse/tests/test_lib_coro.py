import sys
import time
import asyncio
import threading

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.tests.utils as s_t_utils

class FakeError(Exception): pass

def spawnfunc(x, y=10):
    return x + y

def spawnsleep(n=10):
    time.sleep(n)
    return True

def spawntime(n):
    time.sleep(n)
    return s_common.now()

def spawnfakeit():
    raise FakeError()

def spawnexit():
    sys.exit(0)

def chkpool():
    return s_coro.forkpool is None

def synerr():
    raise s_exc.SynErr(mesg='fail')

def nopickle():
    class Bar: pass
    return Bar()

class CoroTest(s_t_utils.SynTest):

    async def test_coro_chunks(self):
        async def agen():
            for i in range(101):
                yield i

        chunks = []
        async for chunk in s_coro.chunks(agen()):
            chunks.append(chunk)

        self.len(1, chunks[1])
        self.len(100, chunks[0])

    async def test_coro_event(self):

        evnt = s_coro.Event()

        evnt.set()
        self.true(await evnt.timewait())

        evnt.clear()
        self.false(await evnt.timewait(timeout=0.001))

    async def test_coro_iscoro(self):

        async def agen():
            yield 42

        def genr():
            yield 'woot'

        async def woot():
            return 10

        item = woot()
        self.true(s_coro.iscoro(item))

        await item

        self.false(s_coro.iscoro(genr()))
        self.false(s_coro.iscoro(agen()))

    async def test_coro_genrhelp(self):

        @s_coro.genrhelp
        async def woot():
            yield 1
            yield 2
            yield 3

        self.none(await woot().spin())
        self.eq([1, 2, 3], await woot().list())

    async def test_executor(self):

        def func(*args, **kwargs):
            tid = threading.get_ident()
            return tid, args, kwargs

        future = s_coro.executor(func, 1, key='valu')
        tid, args, kwargs = await future
        # Ensure that we were not executed on the ioloop thread
        self.ne(tid, s_glob._glob_thrd.ident)
        # Ensure that args are passed as expected
        self.eq(args, (1,))
        self.eq(kwargs, {'key': 'valu'})

        async def afunc():
            tid = threading.get_ident()
            return tid
        # Ensure a generic coroutine is executed on the ioloop thread
        self.eq(s_glob._glob_thrd.ident, await afunc())

    async def test_lib_coro_spawn(self):

        todo = (spawnfunc, (20,), {'y': 30})
        self.eq(50, await s_coro.spawn(todo))

        todo = (spawnsleep, (1.5,), {})
        self.true(await s_coro.spawn(todo))

        todo = (spawnsleep, (), {})
        with self.raises(asyncio.TimeoutError):
            await s_coro.spawn(todo, timeout=0.1)

        todo = (spawnfakeit, (), {})
        with self.raises(s_exc.SynErr) as cm:
            await s_coro.spawn(todo)
        self.eq('FakeError', cm.exception.get('name'))
        self.isin('Error executing spawn function: FakeError', cm.exception.get('mesg'))

        todo = (spawnexit, (), {})
        with self.raises(s_exc.SpawnExit):
            await s_coro.spawn(todo)

        todo = (synerr, (), {})
        with self.raises(s_exc.SynErr) as cm:
            await s_coro.spawn(todo)
        self.eq('fail', cm.exception.get('mesg'))

        # by convention spawn functions should
        # never return non-pickleable results
        todo = (nopickle, (), {})
        with self.raises(s_exc.SpawnExit) as cm:
            await s_coro.spawn(todo)
        self.eq(0, cm.exception.get('code'))
        self.isin('without a result', cm.exception.get('mesg'))

    async def test_lib_coro_forked(self):

        self.true(await s_coro.forked(chkpool))

        self.eq(50, await s_coro.forked(spawnfunc, 20, y=30))

        with self.raises(FakeError):
            await s_coro.forked(spawnfakeit)

        self.eq(50, await s_coro.forked(spawnfunc, 20, y=30))

        def newp():
            return 23

        with self.raises(Exception):
            await s_coro.forked(newp)

        oldpool = s_coro.forkpool
        s_coro.forkpool = None

        try:
            self.eq(50, await s_coro.forked(spawnfunc, 20, y=30))
        finally:
            s_coro.forkpool = oldpool

    async def test_lib_coro_semafork(self):

        oldsema = s_coro.forkpool_sema
        self.true(isinstance(oldsema, asyncio.Semaphore))

        try:

            s_coro.forkpool_sema = asyncio.Semaphore(1)

            async with asyncio.TaskGroup() as tg:
                task0 = tg.create_task(s_coro.semafork(spawntime, 1.1))
                task1 = tg.create_task(s_coro.semafork(spawntime, 1.1))

            self.gt(abs(await task1 - await task0), 1_000)

            s_coro.forkpool_sema = None

            self.eq(50, await s_coro.semafork(spawnfunc, 20, y=30))

        finally:

            s_coro.forkpool_sema = oldsema

    async def test_lib_coro_parserforked(self):

        self.true(await s_coro._parserforked(chkpool))

        self.eq(50, await s_coro._parserforked(spawnfunc, 20, y=30))

        with self.raises(FakeError):
            await s_coro._parserforked(spawnfakeit)

        self.eq(50, await s_coro._parserforked(spawnfunc, 20, y=30))

        def newp():
            return 23

        with self.raises(Exception):
            await s_coro._parserforked(newp)
