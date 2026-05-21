

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

    async def test_queue_window(self):

        wind = await s_queue.Window.anit(maxsize=3)

        self.true(await wind.put('asdf'))
        self.false(wind.isfini)

        self.true(await wind.puts(('hehe', 'haha')))

        self.true(wind.isfini)

        self.false(await wind.put('asdf'))
        self.false(await wind.puts(('hehe', 'haha')))

        self.eq(('asdf', 'hehe', 'haha'), [x async for x in wind])
