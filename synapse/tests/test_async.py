import unittest

import synapse.async as s_async

class AsyncTests(unittest.TestCase):

    def test_async_basics(self):
        boss = s_async.AsyncBoss()

        data = {}
        def ondone(ret):
            data['done'] = ret

        def onerr(exc):
            data['err'] = exc

        def onshut(exc):
            data['shut'] = exc

        job1 = boss.initAsyncJob()
        job1.synOn('done',ondone)

        job2 = boss.initAsyncJob()
        job2.synOn('err',onerr)

        job3 = boss.initAsyncJob()
        job3.synOn('err',onshut)

        jid1 = job1.getJobId()
        jid2 = job2.getJobId()
        jid3 = job3.getJobId()

        self.assertEqual( len(boss.getAsyncJobs()), 3)
        self.assertIsNotNone( boss.getAsyncJob(jid1) )
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job1.synFireDone('foo')

        self.assertEqual( data.get('done'), 'foo' )
        self.assertIsNone( boss.getAsyncJob(jid1) )
        self.assertEqual( len(boss.getAsyncJobs()), 2)
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job2.synFireErr('bar')

        self.assertEqual( data.get('err'), 'bar' )
        self.assertIsNone( boss.getAsyncJob(jid2) )
        self.assertEqual( len(boss.getAsyncJobs()), 1)
        self.assertIsNotNone( boss.getAsyncJob(jid3) )

        boss.synFireFini()

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
        boss.synFireFini()

    def test_async_pool_nopool(self):
        boss = s_async.AsyncBoss()
        job = boss.initAsyncJob()
        self.assertRaises(s_async.BossHasNoPool, job.runInPool )
        boss.synFireFini()

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
        def ondone(x):
            data['done'] = x
        def onerr(y):
            data['err'] = y

        job1 = boss.initAsyncJob()
        job1.synOn('done',ondone)

        job2 = boss.initAsyncJob()
        job2.synOn('err',onerr)

        job1[foo].bar(10)
        job2[foo].baz(20)

        job1.waitForJob()
        job2.waitForJob()

        self.assertEqual( data.get('done'), 30 )
        self.assertEqual( data.get('err'), excpt)

