import time
import asyncio
import threading

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.queue as s_queue
import synapse.lib.threads as s_threads

import synapse.tests.utils as s_t_utils

class QueueTest(s_t_utils.SynTest):

    def test_queue_base(self):
        q = s_queue.Queue()

        self.len(0, q)
        self.eq(q.size(), 0)

        q.put('woot')

        self.len(1, q)
        self.eq(q.size(), 1)

        self.eq(q.get(), 'woot')
        self.raises(s_exc.TimeOut, q.get, timeout=0.1)

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

        try:

            for slic in q.slices(2, timeout=0.1):
                retn.append(tuple(slic))

        except s_exc.TimeOut as e:
            pass

        q.put(1)
        q.put(2)
        q.put(3)
        q.put(4)

        try:

            for slic in q.slices(2, timeout=0.1):
                retn.append(tuple(slic))

        except s_exc.TimeOut as e:
            pass

        self.eq(tuple(retn), ((1, 2), (3, 4), (1, 2), (3, 4)))

    def test_queue_timeout(self):
        q = s_queue.Queue()
        q.put(1)

        self.eq(q.slice(1, timeout=0.001), [1])
        self.raises(s_exc.TimeOut, q.slice, 1, timeout=0.001)

        q.put(1)

        self.eq(q.get(timeout=0.001), 1)
        self.raises(s_exc.TimeOut, q.slice, 1, timeout=0.001)

    def test_queue_postfini(self):
        q = s_queue.Queue()
        q.put(1)
        q.put(2)
        q.put(3)
        q.done()
        q.put(4)

        self.eq(q.get(), 1)
        self.eq(q.slice(2), [2, 3])

        self.raises(s_exc.IsFini, q.get)
        self.raises(s_exc.IsFini, q.slice, 1)

        q = s_queue.Queue()
        q.put(1)
        q.fini()
        q.put(2)

        deqdata = []

        [deqdata.append(item) for item in q.deq]

        self.raises(s_exc.IsFini, q.get)
        self.raises(s_exc.IsFini, q.slice, 1)

        self.eq(deqdata, [1])

    def test_queue_iter(self):
        results = []
        data = [1, 2, 3, 4, 5]
        evt = threading.Event()

        q = s_queue.Queue()
        [q.put(item) for item in data]

        @s_common.firethread
        def finisoon():
            evt.wait()
            q.fini()

        thr = finisoon()
        for i, item in enumerate(q, 1):
            results.append(item)
            if i == len(data):
                evt.set()
        thr.join()

        self.true(q.isfini)
        self.eq(data, results)

    def test_queue_exit(self):
        q = s_queue.Queue()
        evt = threading.Event()
        data = [1, 2, 3, 4, 5]
        results = []

        @s_common.firethread
        def nommer():
            evt.wait()
            try:

                while True:
                    results.append(q.get(timeout=1))

            except s_exc.IsFini as e:
                return

        thr = nommer()
        with q:
            [q.put(item) for item in data]
            evt.set()

        thr.join()

        self.true(q.isfini)
        self.eq(data, results)

    async def test_queue_aqueue(self):

        queue = await s_queue.AQueue.anit()
        queue.put('foo')

        async def poke():
            queue.put('bar')

        self.eq(['foo'], await queue.slice())

        queue.schedCoro(poke())

        self.eq(['bar'], await queue.slice())

    async def test_queu_s2aqueue(self):

        async with await s_queue.S2AQueue.anit(10) as q:

            def sync():
                for i in range(10):
                    q.put(i)

            task = asyncio.get_running_loop().run_in_executor(None, sync)

            for i in range(10):
                await q.get()

            self.len(0, q)

        await task

class AsyncQueueTest(s_t_utils.SynTest):
    async def test_asyncqueue(self):

        # The axon tests test most of the asyncqueue functionality.  We just need to test the
        # draining part

        async with await s_queue.AsyncQueue.anit(5, drain_level=3) as q:
            [await q.put(i) for i in range(5)]
            got_to_end = False
            waiter = asyncio.Event()
            last_msg = 0

            def sync_worker():

                nonlocal got_to_end
                nonlocal last_msg

                time.sleep(0.1)

                last_msg = q.get()  # got 0
                last_msg = q.get()  # got 1
                q.schedCallSafe(waiter.set)
                time.sleep(0.1)
                last_msg = q.get()  # got 2
                got_to_end = True

            t = s_threads.worker(sync_worker)
            before = time.time()

            await waiter.wait()

            await q.put(6)

            self.lt(0.1, time.time() - before)
            await asyncio.sleep(0.1)
            self.eq(last_msg, 2)

            await asyncio.sleep(0.1)

            self.true(got_to_end)

            t.join()
