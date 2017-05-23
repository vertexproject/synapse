import unittest
import synapse.daemon as s_daemon
from synapse.tests.common import *
from synapse.dendrite.jobs import Jobs
import synapse.lib.service as s_service

class DendriteJobsTest(SynTest):

    def withoutIden(self, data):
        if data.__class__ == dict:
            data.pop('iden')
        return data

    @contextlib.contextmanager
    def setup(self):
        dmon = s_daemon.Daemon()
        sbus = s_service.SvcBus()
        dmon.share('syn.svcbus', sbus, fini=True)
        link = dmon.listen('tcp://127.0.0.1:0/')
        port = link[1].get('port')
        yield Jobs('ram://', 'tcp://127.0.0.1:%d/syn.svcbus' % port)
        dmon.fini()

    def test_put_and_get(self):
        with self.setup() as jobs:
            queue = 'fooqueue'
            data1 = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}
            jobs.put(queue, data1)

            data2 = {'some': 'thing', 'todo': 'wootastication'}
            jobs.put(queue, data2)

            data3 = {'some': 'thing', 'todo': 'shakababafication'}
            jobs.put(queue, data3)

            self.assertEqual(self.withoutIden(jobs.get(queue)), data1)
            self.assertEqual(self.withoutIden(jobs.get(queue)), data2)
            self.assertEqual(self.withoutIden(jobs.get(queue)), data3)
            self.assertEqual(self.withoutIden(jobs.get(queue)), None)

    def test_complete(self):
        with self.setup() as jobs:
            queue = 'wooties'
            data1 = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}
            jobs.put(queue, data1)

            data2 = {'some': 'thing', 'todo': 'wootastication'}
            jobs.put(queue, data2)

            self.assertEqual(jobs.qsize(queue, 'completed'), 0)

            job = jobs.get(queue)
            jobs.complete(job)
            self.assertEqual(jobs.qsize(queue, 'completed'), 1)

    def test_fail(self):
        with self.setup() as jobs:
            queue = 'wooties'
            self.assertTrue(jobs.isEmpty(queue))

            data1 = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}
            jobs.put(queue, data1)
            self.assertFalse(jobs.isEmpty(queue))

            job = jobs.get(queue)
            self.assertTrue(jobs.isEmpty(queue))
            self.assertEqual(jobs.qsize(queue, 'working'), 1)
            jobs.fail(job)
            self.assertTrue(jobs.isEmpty(queue))
            self.assertTrue(jobs.isEmpty(queue, 'working'))
            self.assertEqual(jobs.qsize(queue, 'failed'), 1)

    def test_clear(self):
        with self.setup() as jobs:
            data = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}

            queue1 = 'wooties'
            jobs.put(queue1, data)
            jobs.put(queue1, data)

            queue2 = 'shoobiedoobies'
            jobs.put(queue2, data)

            jobs.clear(queue1)
            self.assertEqual(jobs.qsize(queue1), 0)
            self.assertEqual(jobs.qsize(queue2), 1)

            jobs.clear(queue2)
            self.assertEqual(jobs.qsize(queue1), 0)
            self.assertEqual(jobs.qsize(queue2), 0)

    def test_qsize(self):
        with self.setup() as jobs:
            data = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}

            queue1 = 'wooties'
            jobs.put(queue1, data)
            jobs.put(queue1, data)

            queue2 = 'shoobiedoobies'
            jobs.put(queue2, data)

            self.assertEqual(jobs.qsize(queue1), 2)
            self.assertEqual(jobs.qsize(queue2), 1)

    def test_isEmpty(self):
        with self.setup() as jobs:
            queue = 'wooties'
            self.assertTrue(jobs.isEmpty(queue))
            self.assertTrue(jobs.isEmpty(queue, 'completed'))

            data1 = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}
            jobs.put(queue, data1)
            self.assertFalse(jobs.isEmpty(queue))
            self.assertTrue(jobs.isEmpty(queue, 'completed'))

            job = jobs.get(queue)
            jobs.complete(job)
            self.assertTrue(jobs.isEmpty(queue))
            self.assertFalse(jobs.isEmpty(queue, 'completed'))

    def test_stats(self):
        with self.setup() as jobs:
            data = {'some': 'thing', 'todo': 'shoobeedoobeedoo'}

            queue1 = 'wooties'
            jobs.put(queue1, data)
            jobs.put(queue1, data)
            job = jobs.get(queue1)

            queue2 = 'shoobiedoobies'
            jobs.put(queue2, data)

            stats = jobs.stats()
            self.assertEqual(stats[queue1], 2)
            self.assertEqual(stats[queue2], 1)

            stats = jobs.stats('queued')
            self.assertEqual(stats[queue1], 1)
            self.assertEqual(stats[queue2], 1)

            stats = jobs.stats('completed')
            self.assertEqual(stats[queue1], 0)
            self.assertEqual(stats[queue2], 0)

            jobs.complete(job)
            stats = jobs.stats('completed')
            self.assertEqual(stats[queue1], 1)
            self.assertEqual(stats[queue2], 0)
