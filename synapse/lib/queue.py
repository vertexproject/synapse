import asyncio
import threading
import collections

import synapse.exc as s_exc
import synapse.common as s_common
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

class Queue:
    '''
    An asyncio Queue with batch methods and graceful close.
    '''
    def __init__(self, maxsize=None):
        self.q = asyncio.Queue(maxsize=maxsize)
        self.closed = False

    async def close(self):
        await self.q.put(s_common.novalu)
        self.closed = True

    async def put(self, item):

        if self.closed:
            mesg = 'The Queue has been closed.'
            raise s_exc.BadArg(mesg=mesg)

        await self.q.put(item)

    async def size(self):
        size = self.q.qsize()
        if self.closed:
            size -= 1
        return size

    async def puts(self, items):

        if self.closed:
            mesg = 'The Queue has been closed.'
            raise s_exc.BadArg(mesg=mesg)

        for item in items:
            await self.q.put(item)

    async def slice(self, size=1000):

        if self.closed and self.q.qsize() == 0:
            return None

        items = []

        item = await self.q.get()
        if item is s_common.novalu:
            return None

        items.append(item)

        size -= 1

        for i in range(min(size, self.q.qsize())):

            item = await self.q.get()
            if item is s_common.novalu:
                break

            items.append(item)

        return items

    async def slices(self, size=1000):

        while True:
            items = await self.slice(size=size)
            if items is None:
                return

            yield items

class Window(s_base.Base):
    '''
    A Queue like object which yields added items.  If the queue ever reaches
    its maxsize, it will be fini()d.  On fini(), the Window will continue to
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
