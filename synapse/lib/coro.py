'''
Async/Coroutine related utilities.
'''
import asyncio
import inspect
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.lib.base as s_base

# FIXME:  replace all instances of asyncio.iscoroutine with this function
def iscoro(item):
    return inspect.iscoroutine(item)

class Queue(s_base.Base):
    '''
    An async queue with chunk optimized sync compatible consumer.
    '''
    def __init__(self):

        s_base.Base.__init__(self)

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

class Genr(s_base.Base):
    '''
    Wrap an async generator for use by a potentially sync caller.
    '''
    def __init__(self, genr):
        s_base.Base.__init__(self)
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

def generator(f):
    def wrap(*args, **kwargs):
        return Genr(f(*args, **kwargs))
    return wrap
