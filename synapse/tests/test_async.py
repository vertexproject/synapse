import time
import unittest
import threading

import synapse.async as s_async
import synapse.session as s_session
import synapse.threads as s_threads

from synapse.tests.common import *

class AsyncTests(SynTest):

    def test_async_basics(self):

        boss = s_async.Boss()

        data = {}
        def jobmeth(x, y=20):
            return x + y

        def jobdork(x, y=20):
            raise Exception('hi')

        def jobfini(job):
            name = job[1].get('name')
            data[name] = job

        jid1 = s_async.jobid()
        jid2 = s_async.jobid()

        task1 = (jobmeth, (3,), {})
        task2 = (jobdork, (3,), {})

        job1 = boss.initJob(jid1, task=task1, name='job1', onfini=jobfini)
        job2 = boss.initJob(jid2, task=task2, name='job2', onfini=jobfini)

        self.assertEqual( job1[0], jid1 )

        self.assertEqual( len(boss.getJobs()), 2 )

        boss._runJob(job1)
        self.assertEqual( len(boss.getJobs()), 1 )

        boss._runJob(job2)
        self.assertEqual( len(boss.getJobs()), 0 )

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual( ret2[1]['err'], 'Exception' )

        boss.fini()

    def test_async_pool_basics(self):
        boss = s_async.Boss()
        boss.runBossPool(3)

        data = {}
        def jobmeth(x, y=20):
            return x + y

        def jobdork(x, y=20):
            raise Exception('hi')

        def jobfini(job):
            name = job[1].get('name')
            data[name] = job

        jid1 = s_async.jobid()
        jid2 = s_async.jobid()

        task1 = (jobmeth, (3,), {})
        task2 = (jobdork, (3,), {})

        job1 = boss.initJob(jid1, task=task1, name='job1', onfini=jobfini)
        job2 = boss.initJob(jid2, task=task2, name='job2', onfini=jobfini)

        self.assertEqual( job1[0], jid1 )

        boss.waitJob(jid1, timeout=1)
        boss.waitJob(jid2, timeout=1)

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual( ret2[1]['err'], 'Exception' )

        boss.fini()

    def test_async_timeout(self):

        boss = s_async.Boss()

        def myjob():
            time.sleep(0.2)

        jid = s_async.jobid()
        job = boss.initJob(jid, task=(myjob,(),{}), timeout=0.01)

        boss.waitJob(jid)

        self.assertEqual( job[1]['err'], 'HitMaxTime' )

        boss.fini()

    def test_async_onfini(self):

        boss = s_async.Boss()
        boss.runBossPool(3)

        data = {}
        evt = threading.Event()

        def onfini(job):
            data['job'] = job
            evt.set()

        def woot():
            return 10

        jid = s_async.jobid()
        task = s_async.newtask(woot)
        boss.initJob(jid, task=task, onfini=onfini)

        self.assertTrue( evt.wait(timeout=1) )
        job = data.get('job')

        self.assertEqual( job[1].get('ret'), 10 )

        boss.fini()

    def test_async_async(self):

        class Foo(s_async.Async):
            def bar(self, x):
                return x + 20

        boss = s_async.Boss()
        boss.runBossPool(3)

        foo = Foo(boss)

        jid = foo.async('bar',20)
        job = foo.resync(jid)
        ret = s_async.jobret(job)

        self.assertEqual( ret, 40 )

        boss.fini()

    def test_async_wait_timeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.Boss()
        boss.runBossPool(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initJob(jid, task=task)

        self.assertFalse( boss.waitJob(jid,timeout=0.01) )

        self.assertTrue( boss.waitJob(jid,timeout=1) )

        boss.fini()
