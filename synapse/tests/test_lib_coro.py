import asyncio

import synapse.glob as s_glob
import synapse.lib.coro as s_coro

import synapse.tests.common as s_test

class CoroTest(s_test.SynTest):

    @s_test.run_sync
    async def test_coro_fini(self):

        event = asyncio.Event()
        async def setit():
            event.set()

        f = s_coro.Fini()
        async with f as f:
            f.onfini(setit)

        self.true(f.isfini)
        self.true(event.is_set())
        self.false(f._isExitExc())


    def test_coro_queue(self):

        async def init():
            queue = s_coro.Queue()
            queue.put('foo')
            return queue

        async def poke():
            await asyncio.sleep(0.1)
            queue.put('bar')

        queue = s_glob.sync(init())

        self.eq(['foo'], s_glob.sync(queue.slice()))

        s_glob.plex.coroToTask(poke())
        self.eq(['bar'], s_glob.sync(queue.slice()))
