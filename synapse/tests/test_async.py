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
        job1.on('job:done',ondone)

        job2 = boss.initAsyncJob()
        job2.on('job:err',onerr)

        job3 = boss.initAsyncJob()
        job3.on('job:err',onshut)

        jid1 = job1.jid
        jid2 = job2.jid
        jid3 = job3.jid

        self.assertEqual( len(boss.getAsyncJobs()), 3)
        self.assertIsNotNone( boss.getAsyncJob(jid1) )
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job1.done('foo')

        self.assertEqual( data.get('done'), 'foo' )
        self.assertIsNone( boss.getAsyncJob(jid1) )
        self.assertEqual( len(boss.getAsyncJobs()), 2)
        self.assertIsNotNone( boss.getAsyncJob(jid2) )

        job2.err('bar')

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
        self.assertTrue( job.wait() )

        self.assertEqual( job.retval, 40 )
        boss.fini()

    def test_async_pool_nopool(self):
        boss = s_async.AsyncBoss()
        job = boss.initAsyncJob()
        self.assertRaises(s_async.BossHasNoPool, job.runInPool )
        boss.fini()

    def test_async_pool_basics(self):

        data = {'bossdone':0,'bosserr':0}

        def bosserr(event):
            data['bosserr'] += 1

        def bossdone(event):
            data['bossdone'] += 1

        boss = s_async.AsyncBoss(pool=3)
        boss.on('job:err',bosserr)
        boss.on('job:done',bossdone)

        excpt = Exception()
        class Foo:
            def bar(self, x):
                return x + 20
            def baz(self, y):
                raise excpt

        foo = Foo()

        def jobdone(ret):
            data['ret'] = ret

        def joberr(exc):
            data['exc'] = exc

        job1 = boss.initAsyncJob()
        job1.ondone( jobdone )

        job2 = boss.initAsyncJob()
        job2.onerr( joberr )

        job1[foo].bar(10)
        job2[foo].baz(20)

        self.assertTrue( job1.wait(timeout=2) )
        self.assertTrue( job2.wait(timeout=2) )

        self.assertEqual( data.get('ret'), 30 )
        self.assertEqual( data.get('exc'), excpt)

        self.assertEqual( data.get('bosserr'), 1 )
        self.assertEqual( data.get('bossdone'), 1 )

    def test_async_job_sync(self):

        class Foo:
            def bar(self, x):
                return x + 20

        foo = Foo()
        boss = s_async.AsyncBoss(pool=3)
        self.assertEqual( boss[foo].bar(40).sync(), 60 )

    def test_async_api(self):
        class Foo:
            def bar(self, x):
                return x + 20

        foo = Foo()

        boss = s_async.AsyncBoss(pool=1)
        afoo = s_async.AsyncApi(boss,foo)

        job = afoo.bar(20)
        self.assertEqual( job.sync(), 40 )

