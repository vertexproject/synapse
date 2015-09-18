import time
import unittest
import threading

import synapse.async as s_async

class AsyncTests(unittest.TestCase):

    def test_async_basics(self):

        boss = s_async.AsyncBoss()

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

        job1 = boss.initAsyncJob(jid1, task=task1, name='job1')
        job2 = boss.initAsyncJob(jid2, task=task2, name='job2')

        boss.onJobFini(jid1, jobfini)
        boss.onJobFini(jid2, jobfini)

        self.assertEqual( job1[0], jid1 )
        self.assertIsNotNone( job1[1]['times'].get('init') )

        self.assertEqual( len(boss.getAsyncJobs()), 2 )

        boss._runAsyncJob(job1)
        self.assertEqual( len(boss.getAsyncJobs()), 1 )

        boss._runAsyncJob(job2)
        self.assertEqual( len(boss.getAsyncJobs()), 0 )

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )
        self.assertEqual( ret1[1]['status'], 'done' )
        self.assertIsNotNone( ret1[1]['times'].get('fini') )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual( ret2[1]['err'], 'Exception' )
        self.assertEqual( ret2[1]['status'], 'err' )

        boss.fini()

    def test_async_pool_basics(self):
        boss = s_async.AsyncBoss(size=3)

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

        job1 = boss.initAsyncJob(jid1, task=task1, name='job1')
        job2 = boss.initAsyncJob(jid2, task=task2, name='job2')

        boss.onJobFini(jid1, jobfini)
        boss.onJobFini(jid2, jobfini)

        self.assertEqual( job1[0], jid1 )
        self.assertIsNotNone( job1[1]['times'].get('init') )

        boss.queAsyncJob(jid1)
        boss.queAsyncJob(jid2)

        boss.waitAsyncJob(jid1, timeout=1)
        boss.waitAsyncJob(jid2, timeout=1)

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )
        self.assertEqual( ret1[1]['status'], 'done' )
        self.assertIsNotNone( ret1[1]['times'].get('fini') )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual( ret2[1]['err'], 'Exception' )
        self.assertEqual( ret2[1]['status'], 'err' )

        boss.fini()

    def test_async_timeout(self):

        boss = s_async.AsyncBoss(size=3)

        def myjob():
            time.sleep(0.2)

        jid = s_async.jobid()
        job = boss.initAsyncJob(jid, task=(myjob,(),{}), timeout=0.01)

        boss.waitAsyncJob(jid)

        self.assertEqual( job[1]['status'], 'err' )
        self.assertEqual( job[1]['err'], 'JobTimedOut' )

        boss.fini()

    def test_async_onfini(self):

        boss = s_async.AsyncBoss(size=3)

        data = {}
        evt = threading.Event()

        def onfini(job):
            data['job'] = job
            evt.set()

        def woot():
            return 10

        jid = s_async.jobid()
        task = s_async.newtask(woot)
        boss.initAsyncJob(jid, task=task, onfini=onfini)

        self.assertTrue( evt.wait(timeout=1) )
        job = data.get('job')

        self.assertEqual( job[1].get('ret'), 10 )
        self.assertEqual( job[1].get('status'), 'done' )

        boss.fini()

    def test_async_api(self):

        class Foo:
            def bar(self, x):
                return x + 20

        foo = Foo()

        boss = s_async.AsyncBoss(1)
        async = s_async.AsyncApi(boss, foo)

        job = async.bar(30)

        boss.waitAsyncJob( job[0] )

        self.assertEqual( s_async.jobret(job), 50 )

        boss.fini()

    def test_async_wait_timeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.AsyncBoss(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initAsyncJob(jid, task=task)

        self.assertFalse( boss.waitAsyncJob(jid,timeout=0.01) )

        self.assertTrue( boss.waitAsyncJob(jid,timeout=1) )

        boss.fini()
