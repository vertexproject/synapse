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
