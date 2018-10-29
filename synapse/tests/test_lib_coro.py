import asyncio
import unittest

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.lib.coro as s_coro

import synapse.tests.utils as s_t_utils

class CoroTest(s_t_utils.SynTest):

    def test_coro_queue(self):

        async def init():
            queue = await s_coro.Queue.anit()
            queue.put('foo')
            return queue

        async def poke():
            await s_glob.plex.sleep(0.1)
            queue.put('bar')

        queue = s_glob.sync(init())

        self.eq(['foo'], s_glob.sync(queue.slice()))

        s_glob.plex.coroToTask(poke())
        self.eq(['bar'], s_glob.sync(queue.slice()))

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

    async def test_coro_s2aqueue(self):

        async with await s_coro.S2AQueue.anit(10) as q:

            def sync():
                for i in range(10):
                    q.put(i)

            task = asyncio.get_running_loop().run_in_executor(None, sync)

            for i in range(10):
                await q.get()

            self.len(0, q)

        await task

    async def test_genr2agenr(self):

        def testgenr(n):
            yield from range(n)

        await self.agenlen(10, s_coro.genr2agenr(testgenr, 10, qsize=5))

        def badgenr(n):
            yield 42
            raise s_exc.MustBeLocal()

        await self.agenraises(s_exc.MustBeLocal, s_coro.genr2agenr(badgenr, 10))

    async def test_coro_genrhelp(self):

        @s_coro.genrhelp
        async def woot():
            yield 1
            yield 2
            yield 3

        self.none(await woot().spin())
        self.eq([1,2,3], await woot().list())
