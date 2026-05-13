import asyncio

import synapse.exc as s_exc
import synapse.lib.boss as s_boss
import synapse.lib.cell as s_cell
import synapse.lib.task as s_task
import synapse.tests.utils as s_test

class BossCell(s_cell.Cell):
    async def initServiceRuntime(self):
        self.cboss = await s_boss.Boss.anit()
        self.onfini(self.cboss)

class TaskTest(s_test.SynTest):

    def test_loop_none(self):
        self.none(s_task.loop())

    async def test_loop_nn(self):
        self.nn(s_task.loop())

    async def test_task_module(self):

        async with self.getTestCell(BossCell) as bcell:
            boss = bcell.cboss
            root = await bcell.auth.getUserByName('root')

            synt = await boss.promote('test', root, info={'hehe': 'haha'})

            self.eq(s_task.user(), root)
            self.eq(s_task.current(), synt)
            self.eq(s_task.username(), 'root')

            ret = synt.pack()
            self.nn(ret.pop('iden'))
            self.nn(ret.pop('tick'))
            self.eq(ret, {'name': 'test', 'info': {'hehe': 'haha'},
                          'user': 'root', 'kids': {}})

            ret = synt.packv2()
            self.nn(ret.pop('iden'))
            self.nn(ret.pop('tick'))
            self.eq(ret, {'name': 'test', 'info': {'hehe': 'haha'},
                          'user': root.iden, 'username': 'root', 'kids': {},
                          'protected': False, 'background': False})

    async def test_taskvars(self):
        s_task.varset('test', 'foo')
        self.eq(s_task.varget('test'), 'foo')

        self.none(s_task.varget('nope'))

        s_task.vardefault('test2', lambda: [1, 2, 3])
        test2 = s_task.varget('test2')
        self.eq(test2, [1, 2, 3])
        test2.append(4)
        self.eq([1, 2, 3, 4], s_task.varget('test2'))

        async def taskfunc():
            self.none(s_task.varget('test'))
            self.eq([1, 2, 3], s_task.varget('test2'))
            s_task.varset('test', 42)

        await asyncio.create_task(taskfunc())

        self.eq(s_task.varget('test'), 'foo')

    async def test_task_iden(self):
        async with self.getTestCell(BossCell) as bcell:
            root = await bcell.auth.getUserByName('root')
            boss = bcell.cboss

            with self.raises(s_exc.BadArg):
                await s_task.Task.anit(boss, asyncio.current_task(), None, root, iden=10)
            with self.raises(s_exc.BadArg):
                await s_task.Task.anit(boss, asyncio.current_task(), None, root, iden='woot')

    async def test_task_done_boss_fini(self):
        # _onTaskDone must not call schedCoroSafe when the boss is already fini'd.
        # Previously this would attempt to schedule Task.fini() on the dead Boss,
        # producing an orphan task that would never be cleaned up.
        async with self.getTestCell(BossCell) as bcell:
            root = await bcell.auth.getUserByName('root')
            boss = bcell.cboss

            done_evt = asyncio.Event()

            async def longrun():
                await done_evt.wait()

            task = boss.schedCoro(longrun())
            synt = await s_task.Task.anit(boss, task, 'longrun', root)

            # Fini the boss first (simulating what happens during Cell.fini when the
            # Boss is a tofini child and is torn down before _kill_active_tasks runs).
            await boss.fini()

            # Task's asyncio done-callback fires here; with the fix it must skip
            # schedCoroSafe rather than scheduling fini() on the dead boss.
            done_evt.set()
            await asyncio.sleep(0)

            # The boss is fini'd and its task registry is clear — no orphan tasks.
            self.true(boss.isfini)
            self.eq(boss.tasks, {})
            # _syn_task is cleared so the asyncio task is no longer associated.
            self.none(task._syn_task)

    async def test_task_promoted_boss_reuse(self):
        # A task promoted under Boss A must not carry its stale _syn_task reference
        # into operations on Boss B after Boss A has been fini'd. Specifically,
        # _onTaskFini must clear _syn_task so that the next boss.promote() call
        # creates a fresh Task rather than returning the dead one.
        async with self.getTestCell(BossCell) as bcell:
            root = await bcell.auth.getUserByName('root')

            async with await s_boss.Boss.anit() as boss_a:
                # Promote the current asyncio task under boss_a.
                synt_a = await boss_a.promote('work', root)
                self.nn(s_task.current())
                self.eq(s_task.current(), synt_a)

            # boss_a is fini'd; _onTaskFini should have cleared _syn_task.
            self.true(boss_a.isfini)
            self.none(asyncio.current_task()._syn_task)
            self.none(s_task.current())

            async with await s_boss.Boss.anit() as boss_b:
                # Promoting under boss_b must succeed and return a fresh Task.
                synt_b = await boss_b.promote('work', root)
                self.nn(synt_b)
                self.eq(synt_b.boss, boss_b)
                self.false(synt_b.boss.isfini)
