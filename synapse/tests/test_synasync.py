import time
import unittest
import threading

import synapse.synasync as s_async
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

        self.eq(job1[0], jid1)

        self.eq(len(boss.jobs()), 2)

        boss._runJob(job1)
        self.eq(len(boss.jobs()), 1)

        boss._runJob(job2)
        self.eq(len(boss.jobs()), 0)

        ret1 = data.get('job1')

        self.nn(ret1)
        self.eq(ret1[1]['ret'], 23)

        ret2 = data.get('job2')
        self.nn(ret2)
        self.eq(ret2[1]['err'], 'Exception')

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

        self.eq(job1[0], jid1)

        boss.wait(jid1, timeout=1)
        boss.wait(jid2, timeout=1)

        ret1 = data.get('job1')

        self.nn(ret1)
        self.eq(ret1[1]['ret'], 23)

        ret2 = data.get('job2')
        self.nn(ret2)
        self.eq(ret2[1]['err'], 'Exception')
        self.eq(ret2[1]['errmsg'], 'hi')

        boss.fini()

    def test_async_timeout(self):

        boss = s_async.Boss()

        def myjob():
            time.sleep(0.2)

        def mylongjob():
            time.sleep(2.0)

        jid = s_async.jobid()
        job = boss.initJob(jid, task=(myjob, (), {}), timeout=0.01)

        boss.wait(jid)

        self.eq(job[1]['err'], 'HitMaxTime')

        # Ensure the boss.sync() fails as well
        jid = s_async.jobid()
        job = boss.initJob(jid, task=(mylongjob, (), {}), timeout=0.1)
        # Try a sync() call which times out.
        with self.raises(HitMaxTime) as cm:
            boss.sync(job, timeout=0.01)

        boss.fini()

    def test_async_sync(self):

        boss = s_async.Boss()
        boss.runBossPool(1)

        def myjob():
            time.sleep(0.1)
            return True

        jid = s_async.jobid()
        job = boss.initJob(jid, task=(myjob, (), {}), timeout=0.2)
        # Try a sync() call which times out.
        with self.raises(HitMaxTime) as cm:
            boss.sync(job, timeout=0.01)
        self.false(job[1].get('status'))
        # Now sync() again and get the job ret
        ret = boss.sync(job)
        self.true(ret)

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

        self.true(evt.wait(timeout=1))
        job = data.get('job')

        self.eq(job[1].get('ret'), 10)

        boss.fini()

    def test_async_wait_timeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.Boss()
        boss.runBossPool(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initJob(jid, task=task)

        self.false(boss.wait(jid, timeout=0.01))

        self.true(boss.wait(jid, timeout=1))

        boss.fini()

    def test_async_wait_syntimeout(self):

        def longtime():
            time.sleep(0.1)

        boss = s_async.Boss()
        boss.runBossPool(1)

        jid = s_async.jobid()
        task = s_async.newtask(longtime)

        boss.initJob(jid, task=task)

        with s_scope.enter({'syntimeout': 0.01}):
            self.false(boss.wait(jid))

        self.true(boss.wait(jid, timeout=1))

        boss.fini()

    def test_async_sugar(self):

        boss = s_async.Boss()

        job = boss.initJob()

        boss.done(job[0], 5)

        boss.wait(job[0])

        self.eq(job[1].get('ret'), 5)

        boss.fini()

    def test_async_custom_pool_basics(self):
        # Demonstrate Boss use with a custom thread pool.
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

        self.eq(job1[0], jid1)
        self.eq(job2[0], jid2)

        # Test __iter__ since we've got jobs in the boss that haven't been run.
        jobs = [job for job in boss]
        self.eq(len(jobs), 2)

        my_pool.call(boss._runJob, job1)
        my_pool.call(boss._runJob, job2)

        boss.wait(jid1, timeout=1)
        boss.wait(jid2, timeout=1)

        ret1 = data.get('job1')

        self.nn(ret1)
        self.eq(ret1[1]['ret'], 23)

        ret2 = data.get('job2')
        self.nn(ret2)
        self.eq(ret2[1]['err'], 'Exception')
        self.eq(ret2[1]['errmsg'], 'hi')

        boss.fini()
