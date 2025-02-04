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

            with self.getAsyncLoggerStream('synapse.lib.boss',
                                           'Iden specified for existing task') as stream:

                iden = s_common.guid()

                async def double_promote():
                    await boss.promote(f'double', root, taskiden=iden)
                    await boss.promote(f'double', root, taskiden=iden + iden)

                coro = boss.schedCoro(double_promote())
                self.true(await stream.wait(timeout=6))
                await coro
