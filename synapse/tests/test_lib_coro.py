import contextlib

import synapse.exc as s_exc
import synapse.lib.coro as s_coro
import synapse.tests.utils as s_t_utils

class CoroTest(s_t_utils.SynTest):

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

    async def test_genr2agenr(self):

        def testgenr(n):
            yield from range(n)

        await self.agenlen(10, s_coro.genr2agenr(testgenr, 10, qsize=5))

        def badgenr(n):
            yield 42
            raise s_exc.MustBeLocal()

        await self.agenraises(s_exc.MustBeLocal, s_coro.genr2agenr(badgenr, 10))

    def test_asynctosynccmgr(self):

        @contextlib.asynccontextmanager
        async def testmgr():
            yield 42

        syncmgr = s_coro.AsyncToSyncCMgr(testmgr)
        with syncmgr as foo:
            self.eq(foo, 42)
