import asyncio

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

            await evnt.wait()

            self.len(2, boss.ps())

            await synt0.kill()

            self.len(1, boss.ps())
