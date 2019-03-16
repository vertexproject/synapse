import time
import asyncio
import threading

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.queue as s_queue
import synapse.lib.threads as s_threads

import synapse.tests.utils as s_t_utils

class QueueTest(s_t_utils.SynTest):

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

            t = self.worker(sync_worker)
            before = time.time()

            await waiter.wait()

            await q.put(6)

            self.lt(0.09, time.time() - before)
            await asyncio.sleep(0.1)
            self.eq(last_msg, 2)

            await asyncio.sleep(0.1)

            self.true(got_to_end)

            t.join()
