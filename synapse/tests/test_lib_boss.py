import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.boss as s_boss
import synapse.tests.utils as s_test

class BossTest(s_test.SynTest):

    async def test_boss_base(self):

        async with await s_boss.Boss.anit() as boss:

            evnt = asyncio.Event()

            async def testloop():
                evnt.set()
                while True:
                    await asyncio.sleep(10)

            self.len(0, boss.ps())

            synt = await boss.promote('test', None, info={'hehe': 'haha'})

            self.len(1, boss.ps())

            self.eq('test', synt.name)
            self.eq('haha', synt.info.get('hehe'))

            synt0 = await boss.execute(testloop(), 'testloop', None, info={'foo': 'bar'})
            iden = synt0.iden

            with self.raises(s_exc.BadArg):
                _ = await boss.execute(asyncio.sleep(1), 'testsleep', None, iden=iden)

            await evnt.wait()

            self.len(2, boss.ps())

            await synt0.kill()

            self.len(1, boss.ps())

            with self.getAsyncLoggerStream('synapse.lib.boss',
                                           'Iden specified for existing task') as stream:

                iden = s_common.guid()

                async def double_promote():
                    await boss.promote(f'double', None, taskiden=iden)
                    await boss.promote(f'double', None, taskiden=iden + iden)

                coro = boss.schedCoro(double_promote())
                self.true(await stream.wait(timeout=6))
                await coro
