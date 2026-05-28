import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.boss as s_boss
import synapse.lib.cell as s_cell
import synapse.tests.utils as s_test

class BossCell(s_cell.Cell):
    async def initServiceRuntime(self):
        self.cboss = await s_boss.Boss.anit()
        self.onfini(self.cboss)

class BossTest(s_test.SynTest):

    async def test_boss_base(self):

        async with self.getTestCell(BossCell) as bcell:
            boss = bcell.cboss
            root = await bcell.auth.getUserByName('root')

            evnt = asyncio.Event()

            async def testloop():
                evnt.set()
                while True:
                    await asyncio.sleep(10)

            self.len(0, boss.ps())

            synt = await boss.promote('test', root, info={'hehe': 'haha'})

            self.len(1, boss.ps())

            self.eq('test', synt.name)
            self.eq('haha', synt.info.get('hehe'))
            self.eq(root.iden, synt.user.iden)

            synt0 = await boss.execute(testloop(), 'testloop', root, info={'foo': 'bar'})
            iden = synt0.iden

            with self.raises(s_exc.BadArg):
                _ = await boss.execute(asyncio.sleep(1), 'testsleep', root, iden=iden)

            await evnt.wait()

            self.len(2, boss.ps())

            await synt0.kill()

            self.len(1, boss.ps())

            with self.getLoggerStream('synapse.lib.boss') as stream:

                iden = s_common.guid()

                async def double_promote():
                    await boss.promote('double', root, taskiden=iden)
                    await boss.promote('double', root, taskiden=iden + iden)

                coro = boss.schedCoro(double_promote())
                await stream.expect('Iden specified for existing task', timeout=6)
                await coro

            async with boss.shutdown_lock:
                with self.raises(s_exc.ShuttingDown):
                    boss.reqNotShut()

            boss.is_shutdown = True
            with self.raises(s_exc.ShuttingDown):
                boss.reqNotShut()

    async def test_boss_shutdown_no_drain(self):

        async with self.getTestCell(BossCell) as bcell:
            boss = bcell.cboss
            root = await bcell.auth.getUserByName('root')

            evnt = asyncio.Event()

            async def stuck():
                evnt.set()
                while True:
                    await asyncio.sleep(10)

            await boss.execute(stuck(), 'stuck', root)
            await evnt.wait()

            self.len(1, boss.ps())

            self.true(await boss.shutdown(timeout=2, drain=False))
            self.true(boss.is_shutdown)

    async def test_boss_shutdown_no_drain_slowexit(self):

        async with self.getTestCell(BossCell) as bcell:
            boss = bcell.cboss
            root = await bcell.auth.getUserByName('root')

            evnt = asyncio.Event()

            async def slowexit():
                evnt.set()
                try:
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    # simulate a slow cleanup that blows the timeout
                    await asyncio.sleep(0.5)
                    raise

            await boss.execute(slowexit(), 'slowexit', root)
            await evnt.wait()

            self.false(await boss.shutdown(timeout=0.05, drain=False))
            self.false(boss.is_shutdown)

    async def test_boss_shutdown_shared_budget(self):

        async with self.getTestCell(BossCell) as bcell:
            boss = bcell.cboss
            root = await bcell.auth.getUserByName('root')

            evnt0 = asyncio.Event()
            evnt1 = asyncio.Event()

            async def slow(evnt):
                evnt.set()
                await asyncio.sleep(10)

            await boss.execute(slow(evnt0), 'slow0', root)
            await boss.execute(slow(evnt1), 'slow1', root)
            await evnt0.wait()
            await evnt1.wait()

            start = asyncio.get_running_loop().time()
            self.false(await boss.shutdown(timeout=0.2))
            elapsed = asyncio.get_running_loop().time() - start

            # shared budget: total wall time must respect timeout, not 2*timeout
            self.lt(elapsed, 0.4)
            self.false(boss.is_shutdown)
