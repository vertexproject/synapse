import io
import time
import unittest

import synapse.lib.queue as s_queue
import synapse.lib.threads as s_threads

from synapse.tests.common import *

class QueueTest(SynTest):

    def test_queue_base(self):
        q = s_queue.Queue()

        self.len(0, q)
        self.eq(q.size(), 0)

        q.put('woot')

        self.len(1, q)
        self.eq(q.size(), 1)

        self.eq(q.get(), 'woot')
        self.none(q.get(timeout=0.1))

        self.len(0, q)
        self.eq(q.size(), 0)

        q.fini()

    def test_queue_slice(self):
        q = s_queue.Queue()

        q.put(1)
        q.put(2)
        q.put(3)
        q.put(4)

        q.done()

        retn = []

        for slic in q.slices(2):
            retn.append(tuple(slic))

        self.eq(tuple(retn), ((1, 2), (3, 4)))

    def test_queue_multislice(self):
        # run a queue for several items with a timeout.
        q = s_queue.Queue()
        retn = []

        q.put(1)
        q.put(2)
        q.put(3)
        q.put(4)

        for slic in q.slices(2, timeout=0.1):
            retn.append(tuple(slic))

        q.put(1)
        q.put(2)
        q.put(3)
        q.put(4)

        for slic in q.slices(2, timeout=0.1):
            retn.append(tuple(slic))

        self.eq(tuple(retn), ((1, 2), (3, 4), (1, 2), (3, 4)))

    def test_queue_timeout(self):
        q = s_queue.Queue()
        q.put(1)
        self.eq(q.slice(1, timeout=0.001), [1])
        self.eq(q.slice(1, timeout=0.001), None)
        q.put(1)
        self.eq(q.get(timeout=0.001), 1)
        self.eq(q.get(timeout=0.001), None)

    def test_queue_postfini(self):
        q = s_queue.Queue()
        q.put(1)
        q.put(2)
        q.put(3)
        q.done()
        self.eq(q.get(), 1)
        self.eq(q.slice(2), [2, 3])
        self.eq(q.get(), None)
        self.eq(q.slice(1), None)

        q = s_queue.Queue()
        q.put(1)
        q.fini()
        self.eq(q.get(), None)
        self.eq(q.slice(1), None)
