import asyncio
import collections

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

class Window(s_base.Base):
    '''
    A Queue like object which yields added items.  If the queue ever reaches
    it's maxsize, it will be fini()d.  On fini(), the Window will continue to
    yield results until empty and then return.
    '''
    async def __anit__(self, maxsize=None):
        await s_base.Base.__anit__(self)
        self.maxsize = maxsize
        self.event = asyncio.Event()

        self.linklist = collections.deque()

        async def fini():
            self.event.set()

        self.onfini(fini)

    async def __aiter__(self):

        while True:

            if self.linklist:
                yield self.linklist.popleft()
                continue

            if self.isfini:
                return

            self.event.clear()
            await self.event.wait()

    async def put(self, item):
        '''
        Add a single item to the Window.
        '''
        if self.isfini:
            return False

        self.linklist.append(item)
        self.event.set()

        if self.maxsize is not None and len(self.linklist) >= self.maxsize:
            await self.fini()

        return True

    async def puts(self, items):
        '''
        Add multiple items to the window.
        '''
        if self.isfini:
            return False

        self.linklist.extend(items)
        self.event.set()

        if self.maxsize is not None and len(self.linklist) >= self.maxsize:
            await self.fini()

        return True
