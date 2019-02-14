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
