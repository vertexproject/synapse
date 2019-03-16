import asyncio

import synapse.lib.base as s_base

class AQueue(s_base.Base):
    '''
    An async queue with chunk optimized sync compatible consumer.
    '''
    async def __anit__(self):

        await s_base.Base.__anit__(self)

        self.fifo = []
        self.event = asyncio.Event()
        self.onfini(self.event.set)

    def put(self, item):
        '''
        Add an item to the queue.
        '''
        if self.isfini:
            return False

        self.fifo.append(item)

        if len(self.fifo) == 1:
            self.event.set()

        return True

    async def slice(self):

        # sync interface to the async queue
        if len(self.fifo) == 0:
            await self.event.wait()

        retn = list(self.fifo)
        self.fifo.clear()
        self.event.clear()
        return retn
