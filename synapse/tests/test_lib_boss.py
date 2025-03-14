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
                    await boss.promote('double', root, taskiden=iden)
                    await boss.promote('double', root, taskiden=iden + iden)

                coro = boss.schedCoro(double_promote())
                self.true(await stream.wait(timeout=6))
                await coro

    async def test_boss_promote_worker(self):

        async with self.getTestCell(s_cell.Cell) as cell:

            evt00 = asyncio.Event()
            evt01 = asyncio.Event()

            async def doit():
                async def worker(name, reparent):
                    root = None
                    if reparent:
                        root = cell.boss.getRoot()

                    info = {'id': 'worker', 'name': name, 'reparent': reparent}
                    synt = await cell.boss.promote(name, cell.auth.rootuser, info=info, root=root)

                    await synt.worker(evt00.wait(), f'{name}-worker')
                    await evt00.wait()

                synt = await cell.boss.promote('doit', cell.auth.rootuser, info={'id': 'doit'})
                await synt.worker(worker('noparent', False), 'worker00')
                await synt.worker(worker('parent', True), 'worker01')

                evt01.set()

        await cell.boss.schedCoro(doit())
        await evt01.wait()

        # tasks below should look like this:
        # Task name               | Variable
        # ------------------------+---------
        # - doit                  | t0
        #   - worker01            | t0k0
        #   - parent              | t0k1
        #     - parent-worker     | t0k1k0
        # - worker00              | t1
        #   - noparent-worker     | t1k0

        tasks = cell.boss.ps()
        self.len(2, tasks)

        t0, t1 = tasks

        # This is the root task
        self.eq(t0.name, 'doit')
        self.eq(t0.info, {'id': 'doit'})
        self.len(2, t0.kids)

        t0k0, t0k1 = list(t0.kids.values())

        self.eq(t0k0.name, 'worker01')
        self.eq(t0k0.info, {})
        self.len(0, t0k0.kids)

        self.eq(t0k1.name, 'parent')
        self.eq(t0k1.info, {'id': 'worker', 'name': 'parent', 'reparent': True})
        self.len(1, t0k1.kids)

        t0k1k0 = list(t0k1.kids.values())[0]
        self.eq(t0k1k0.name, 'parent-worker')
        self.eq(t0k1k0.info, {})
        self.len(0, t0k1k0.kids)

        # This is the promoted worker task
        self.eq(t1.name, 'worker00')
        self.eq(t1.info, {})
        self.len(1, t1.kids)

        t1k0 = list(t1.kids.values())[0]
        self.eq(t1k0.name, 'noparent-worker')
        self.eq(t1k0.info, {})
        self.len(0, t1k0.kids)

        # release the tasks
        evt00.set()
