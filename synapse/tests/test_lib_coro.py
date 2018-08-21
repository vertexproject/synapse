import asyncio

import synapse.glob as s_glob
import synapse.lib.coro as s_coro

import synapse.tests.common as s_test

@s_coro.generator
async def asyncgenr():
    yield 1
    yield 2
    yield 3

class Hehe(s_coro.Anit):

    def __init__(self, foo):
        s_coro.Anit.__init__(self)
        self.foo = foo

    async def __anit__(self):
        self.bar = self.foo + 10

class CoroTest(s_test.SynTest):

    @s_glob.synchelp
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

    def test_coro_genr_sync(self):

        items = []

        for x in asyncgenr():
            items.append(x)

        self.eq(items, (1, 2, 3))

    @s_glob.synchelp
    async def test_coro_genr_async(self):

        items = []

        async for x in asyncgenr():
            items.append(x)

        self.eq(items, (1, 2, 3))

    @s_glob.synchelp
    async def test_coro_anit(self):

        afoo = await Hehe.anit(20)
        self.eq(afoo.foo, 20)
        self.eq(afoo.bar, 30)

    #def test_coro_init_sync(self):

        #afoo = FooInit(20).anit()
        #self.eq(afoo.foo, 20)
        #self.eq(afoo.bar, 30)

    @s_glob.synchelp
    async def test_coro_iscoro(self):

        async def agen():
            yield foo

        def genr():
            yield foo

        async def woot():
            return 10

        item = woot()
        self.true(s_coro.iscoro(item))

        await item

        self.false(s_coro.iscoro(genr()))
        self.false(s_coro.iscoro(agen()))
