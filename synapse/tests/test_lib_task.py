import asyncio

import synapse.lib.boss as s_boss
import synapse.lib.task as s_task
import synapse.tests.utils as s_test

class FakeUser:
    def __init__(self, name):
        self.name = name

class TaskTest(s_test.SynTest):

    def test_loop_none(self):
        self.none(s_task.loop())

    async def test_loop_nn(self):
        self.nn(s_task.loop())

    async def test_task_module(self):

        async with await s_boss.Boss.anit() as boss:

            user = FakeUser('visi')

            synt = await boss.promote('test', user, info={'hehe': 'haha'})

            self.eq(s_task.user(), user)
            self.eq(s_task.current(), synt)
            self.eq(s_task.username(), 'visi')

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
