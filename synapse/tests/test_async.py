import time
import unittest
import threading

import synapse.async as s_async
import synapse.lib.scope as s_scope
import synapse.lib.threads as s_threads

from synapse.tests.common import *

class AsyncTests(SynTest):

    def test_async_basics(self):

        boss = s_async.Boss()

        data = {}
        def jobmeth(x, y=20):
            return x + y

        def jobdork(x, y=20):
            raise Exception('hi')

        def jobdone(job):
            name = job[1].get('name')
            data[name] = job

        jid1 = s_async.jobid()
        jid2 = s_async.jobid()

        task1 = (jobmeth, (3,), {})
        task2 = (jobdork, (3,), {})

        job1 = boss.initJob(jid1, task=task1, name='job1', ondone=jobdone)
        job2 = boss.initJob(jid2, task=task2, name='job2', ondone=jobdone)

        self.assertEqual( job1[0], jid1 )

        self.assertEqual( len(boss.jobs()), 2 )

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 1 )

        boss._runJob(job2)
        self.assertEqual( len(boss.jobs()), 0 )

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

        def jobdone(job):
            name = job[1].get('name')
            data[name] = job

        jid1 = s_async.jobid()
        jid2 = s_async.jobid()

        task1 = (jobmeth, (3,), {})
        task2 = (jobdork, (3,), {})

        job1 = boss.initJob(jid1, task=task1, name='job1', ondone=jobdone)
        job2 = boss.initJob(jid2, task=task2, name='job2', ondone=jobdone)

        self.assertEqual( job1[0], jid1 )

        boss.wait(jid1, timeout=1)
        boss.wait(jid2, timeout=1)

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual( ret2[1]['err'], 'Exception' )
        self.assertEqual( ret2[1]['errmsg'], 'hi' )

        boss.fini()

    def test_async_timeout(self):

        boss = s_async.Boss()

        def myjob():
            time.sleep(0.2)

        jid = s_async.jobid()
        job = boss.initJob(jid, task=(myjob,(),{}), timeout=0.01)

        boss.wait(jid)

        self.assertEqual( job[1]['err'], 'HitMaxTime' )

        boss.fini()

    def test_async_ondone(self):

        boss = s_async.Boss()
        boss.runBossPool(3)

        data = {}
        evt = threading.Event()

        def ondone(job):
            data['job'] = job
            evt.set()

        def woot():
            return 10

        jid = s_async.jobid()
        task = s_async.newtask(woot)
        boss.initJob(jid, task=task, ondone=ondone)

        self.assertTrue( evt.wait(timeout=1) )
        job = data.get('job')

        self.assertEqual( job[1].get('ret'), 10 )

        boss.fini()

    def test_async_wait_timeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.Boss()
        boss.runBossPool(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initJob(jid, task=task)

        self.assertFalse( boss.wait(jid,timeout=0.01) )

        self.assertTrue( boss.wait(jid,timeout=1) )

        boss.fini()

    def test_async_wait_syntimeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.Boss()
        boss.runBossPool(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initJob(jid, task=task)

        with s_scope.enter({'syntimeout':0.01}):
            self.assertFalse( boss.wait(jid) )

        self.assertTrue( boss.wait(jid,timeout=1) )

        boss.fini()

    def test_async_sugar(self):

        boss = s_async.Boss()

        job = boss.initJob()

        boss.done(job[0],5)

        boss.wait(job[0])

        self.assertEqual( job[1].get('ret'), 5 )

        boss.fini()

    def test_async_custom_pool_basics(self):
        """
        Demonstrate Boss use with a custom thread pool.
        """
        boss = s_async.Boss()

        my_pool = s_threads.Pool(3, maxsize=8)

        data = {}
        def jobmeth(x, y=20):
            return x + y

        def jobdork(x, y=20):
            raise Exception('hi')

        def jobdone(job):
            name = job[1].get('name')
            data[name] = job

        jid1 = s_async.jobid()
        jid2 = s_async.jobid()

        task1 = (jobmeth, (3,), {})
        task2 = (jobdork, (3,), {})

        job1 = boss.initJob(jid1, task=task1, name='job1', ondone=jobdone)
        job2 = boss.initJob(jid2, task=task2, name='job2', ondone=jobdone)

        self.assertEqual(job1[0], jid1)
        self.assertEqual(job2[0], jid2)

        my_pool.call(boss._runJob, job1)
        my_pool.call(boss._runJob, job2)

        boss.wait(jid1, timeout=1)
        boss.wait(jid2, timeout=1)

        ret1 = data.get('job1')

        self.assertIsNotNone(ret1)
        self.assertEqual( ret1[1]['ret'], 23 )

        ret2 = data.get('job2')
        self.assertIsNotNone(ret2)
        self.assertEqual(ret2[1]['err'], 'Exception')
        self.assertEqual(ret2[1]['errmsg'], 'hi')

        boss.fini()
