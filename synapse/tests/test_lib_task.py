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
                          'user': root.iden, 'username': 'root', 'kids': {}})

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
