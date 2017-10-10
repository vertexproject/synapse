from synapse.tests.common import *

import synapse.common as s_common
import synapse.lib.task as s_task

class TaskTest(SynTest):

    def test_task_base(self):

        data = {}
        def onretn(retn):
            data['ok'], data['valu'] = retn

        with s_task.Task() as task:
            task.set('foo', 'bar')
            self.eq(task.get('foo'), 'bar')

        with s_task.Task() as task:

            task.onretn(onretn)

            task.retn(30)

            self.true(data['ok'])
            self.eq(data['valu'], 30)

            task.err({'hehe':'haha'})

            self.false(data['ok'])
            self.eq(data['valu']['hehe'], 'haha')

        with s_task.Task() as task:
            task.onretn(onretn)

            task.fire('task:fini', retn=(True,100))
            self.true(task.isfini)

            self.true(data['ok'])
            self.eq(data['valu'], 100)

        with s_task.Task() as task:
            self.raises(s_common.NoSuchImpl, task.run)

    def test_task_call(self):
        data = {}
        def onretn(retn):
            data['ok'], data['valu'] = retn

        def doit(x,y):
            return x + y

        call = (doit,(10,20),{})
        with s_task.CallTask(call) as task:
            task.onretn(onretn)
            task.run()

        self.true(data['ok'])

        self.eq(data['valu'], 30)
