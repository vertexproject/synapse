import unittest

import synapse.async as s_async

class AsyncTests(unittest.TestCase):

    def test_async_basics(self):
        boss = s_async.AsyncBoss()

        data = {}
        def ondone(event):
            ret = event[1].get('ret')
            data['done'] = ret

        def onerr(event):
            exc = event[1].get('exc')
            data['err'] = exc

        def onshut(event):
            exc = event[1].get('exc')
            data['shut'] = exc

        job1 = boss.initAsyncJob()
        job1.on('done',ondone)

        job2 = boss.initAsyncJob()
        job2.on('err',onerr)

        job3 = boss.initAsyncJob()
        job3.on('err',onshut)

        jid1 = job1.getJobId()
        jid2 = job2.getJobId()
        jid3 = job3.getJobId()

        self.assertEqual( len(boss.getAsyncJobs()), 3)
        self.assertIsNotNone( boss.getAsyncJob(jid1) )
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job1.jobDone('foo')

        self.assertEqual( data.get('done'), 'foo' )
        self.assertIsNone( boss.getAsyncJob(jid1) )
        self.assertEqual( len(boss.getAsyncJobs()), 2)
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job2.jobErr('bar')

        self.assertEqual( data.get('err'), 'bar' )
        self.assertIsNone( boss.getAsyncJob(jid2) )
        self.assertEqual( len(boss.getAsyncJobs()), 1)
        self.assertIsNotNone( boss.getAsyncJob(jid3) )

        boss.fini()

        self.assertTrue( isinstance(data.get('shut'),s_async.BossShutDown))
        self.assertIsNone( boss.getAsyncJob(jid3) )
        self.assertEqual( len(boss.getAsyncJobs()), 0)

    def test_async_pool_terse(self):

        boss = s_async.AsyncBoss(pool=3)
        class Foo:
            def bar(self, x):
                return x + 20

        foo = Foo()

        job = boss[foo].bar(20)
        job.waitForJob()

        self.assertEqual( job.retval, 40 )
        boss.fini()

    def test_async_pool_nopool(self):
        boss = s_async.AsyncBoss()
        job = boss.initAsyncJob()
        self.assertRaises(s_async.BossHasNoPool, job.runInPool )
        boss.fini()

    def test_async_pool_basics(self):

        boss = s_async.AsyncBoss(pool=3)
        excpt = Exception()
        class Foo:
            def bar(self, x):
                return x + 20
            def baz(self, y):
                raise excpt

        foo = Foo()

        data = {}
        def ondone(event):
            data['done'] = event[1].get('ret')

        def onerr(event):
            data['err'] = event[1].get('exc')

        job1 = boss.initAsyncJob()
        job1.on('done',ondone)

        job2 = boss.initAsyncJob()
        job2.on('err',onerr)

        job1[foo].bar(10)
        job2[foo].baz(20)

        job1.waitForJob()
        job2.waitForJob()

        self.assertEqual( data.get('done'), 30 )
        self.assertEqual( data.get('err'), excpt)

