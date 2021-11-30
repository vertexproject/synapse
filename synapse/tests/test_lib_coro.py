import sys
import time
import asyncio
import threading

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.lib.coro as s_coro
import synapse.tests.utils as s_t_utils

class FakeError(Exception): pass

def spawnfunc(x, y=10):
    return x + y

def spawnsleep(n=10):
    time.sleep(n)
    return True

def spawnfakeit():
    raise FakeError()

def spawnexit():
    sys.exit(0)

def chkpool():
    return s_coro.forkpool is None

class CoroTest(s_t_utils.SynTest):

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
        with self.raises(FakeError):
            await s_coro.spawn(todo)

        todo = (spawnexit, (), {})
        with self.raises(s_exc.SpawnExit):
            await s_coro.spawn(todo)

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
