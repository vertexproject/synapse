import asyncio
import unittest

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

    @s_glob.synchelp
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
