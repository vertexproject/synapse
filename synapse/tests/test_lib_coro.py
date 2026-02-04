import sys
import time
import asyncio
import threading

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.tests.utils as s_t_utils

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

    async def test_lib_coro_create_task(self):

        async def sleep(n):
            await asyncio.sleep(n)
            if n == 0:
                return 1 / 0
            return n

        s_coro.create_task(sleep(0.1))
        s_coro.create_task(sleep(0.15))
        s_coro.create_task(sleep(0.2))
        self.len(3, s_coro.bgtasks)
        results = await s_coro.await_bg_tasks()
        self.eq(set(results), {0.1, 0.15, 0.2})
        self.len(0, s_coro.bgtasks)
        results = await s_coro.await_bg_tasks()
        self.eq(results, [])

        s_coro.create_task(sleep(0))
        results = await s_coro.await_bg_tasks()
        self.len(1, results)
        self.isinstance(results[0], ZeroDivisionError)

        task = s_coro.create_task(sleep(10))
        self.eq([], await s_coro.await_bg_tasks(timeout=0.001))
        task.cancel()
        self.eq([], await s_coro.await_bg_tasks())
