

import synapse.lib.queue as s_queue

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
