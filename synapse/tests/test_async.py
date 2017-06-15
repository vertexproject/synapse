import os
import json
import time
import uuid
import tempfile
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

        def mylongjob():
            time.sleep(2.0)

        jid = s_async.jobid()
        job = boss.initJob(jid, task=(myjob,(),{}), timeout=0.01)

        boss.wait(jid)

        self.eq( job[1]['err'], 'HitMaxTime' )

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
        self.eq( ret1[1]['ret'], 23 )

        ret2 = data.get('job2')
        self.nn(ret2)
        self.eq(ret2[1]['err'], 'Exception')
        self.eq(ret2[1]['errmsg'], 'hi')

        boss.fini()

    def test_async_subprocess(self):
        boss = s_async.Boss()

        def jobmeth(x, y=20):
            return (os.getpid(), os.getppid(), x + y)

        jid1 = s_async.jobid()
        task1 = (jobmeth, (3,), {})

        job1 = boss.initJob(jid1, task=task1, subprocess=True)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertNotEqual(job1[1]['ret'][0], os.getpid())
        self.assertEqual(job1[1]['ret'][1], os.getpid())
        self.assertEqual(job1[1]['ret'][2], 23 )
        self.assertEqual(job1[1].get('err'), None)

        boss.fini()

    def test_async_subprocess_timeout(self):
        boss = s_async.Boss()

        def jobtoolong():
            time.sleep(1)

        def justintime(x, y):
            return x + y

        jid1 = s_async.jobid()
        task1 = (jobtoolong, (), {})

        job1 = boss.initJob(jid1, task=task1, subprocess=True, timeout=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job1[1].get('err'), 'HitMaxTime')
        self.assertEqual(job1[1].get('ret'), None)

        jid2 = s_async.jobid()
        task2 = (justintime, (5,8), {})

        job2 = boss.initJob(jid2, task=task2, subprocess=True, timeout=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job2)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job2[1].get('err'), None)
        self.assertEqual(job2[1].get('ret'), 13)

        boss.fini()

    def test_async_subprocess_maxmemory(self):
        boss = s_async.Boss()
        def eatsalot():
            wooties = []
            for i in range(1024*1024*8):
                wooties.append(b'12345678')
            time.sleep(0.2)
            return 'woot'

        jid1 = s_async.jobid()
        task1 = (eatsalot, (), {})

        job1 = boss.initJob(jid1, task=task1, subprocess=True, maxmemory=1024*1024*64, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job1[1].get('err'), 'HitMaxMemory')
        self.assertEqual(job1[1].get('ret'), None)

        jid2 = s_async.jobid()
        task2 = (eatsalot, (), {})

        job2 = boss.initJob(jid2, task=task2, subprocess=True, maxmemory=1024*1024*128, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job2)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job2[1].get('err'), None)
        self.assertEqual(job2[1].get('ret'), 'woot')

        boss.fini()

    def test_async_subprocess_maxcpu(self):
        boss = s_async.Boss()
        def runningwarm():
            currTime = now()
            d = 1
            while True:
                d += 1
                if d % 10000 == 0 and (now() - currTime) > 500:
                    break
            return True

        jid1 = s_async.jobid()
        task1 = (runningwarm, (), {})

        job1 = boss.initJob(jid1, task=task1, subprocess=True, maxcpu=50, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job1[1].get('err'), 'HitMaxCPU')
        self.assertEqual(job1[1].get('ret'), None)

        jid2 = s_async.jobid()
        task2 = (runningwarm, (), {})

        job2 = boss.initJob(jid2, task=task2, subprocess=True, maxcpu=100, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job2)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job2[1].get('err'), None)
        self.assertEqual(job2[1].get('ret'), True)

    def test_async_subprocess_maxcpu_cycles(self):
        boss = s_async.Boss()
        def spikes():
            currTime = now()
            d = 1
            while True:
                d += 1
                if d % 10000 == 0:
                    runtime = now() - currTime
                    if runtime > 500:
                        break
                    elif runtime > 300:
                        time.sleep(0.1)
            return True

        jid1 = s_async.jobid()
        task1 = (spikes, (), {})

        job1 = boss.initJob(jid1, task=task1, subprocess=True, maxcpu=50, maxcpucycles=4, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job1)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job1[1].get('err'), None)
        self.assertEqual(job1[1].get('ret'), True)

        jid2 = s_async.jobid()
        task2 = (spikes, (), {})

        job2 = boss.initJob(jid2, task=task2, subprocess=True, maxcpu=50, maxcpucycles=1, monitorinterval=0.1)
        self.assertEqual( len(boss.jobs()), 1)

        boss._runJob(job2)
        self.assertEqual( len(boss.jobs()), 0)

        self.assertEqual(job2[1].get('err'), 'HitMaxCPU')
        self.assertEqual(job2[1].get('ret'), None)
