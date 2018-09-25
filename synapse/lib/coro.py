'''
Async/Coroutine related utilities.
'''
import asyncio
import inspect
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.lib.base as s_base

def iscoro(item):
    return inspect.iscoroutine(item)

class Queue(s_base.Base):
    '''
    An async queue with chunk optimized sync compatible consumer.
    '''
    async def __anit__(self):
        await s_base.Base.__anit__(self)

        self.fifo = []
        self.event = asyncio.Event(loop=self.loop)
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

class Genr(s_base.Base):
    '''
    Wrap an async generator for use by a potentially sync caller.
    '''
    async def __anit__(self, genr):
        await s_base.Base.__anit__(self)
        self.genr = genr

    def __len__(self):
        return sum(1 for n in self)

    def __iter__(self):

        while not self.isfini:
            try:
                yield s_glob.sync(self.genr.__anext__())
            except StopAsyncIteration as e:
                return

    async def __aiter__(self):

        while not self.isfini:
            try:
                yield await self.genr.__anext__()
            except StopAsyncIteration as e:
                return

# FIXME This isn't going to work.  Still used?
# def generator(f):
#     def wrap(*args, **kwargs):
#         return Genr(f(*args, **kwargs))
#     return wrap
