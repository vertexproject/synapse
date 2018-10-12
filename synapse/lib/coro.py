'''
Async/Coroutine related utilities.
'''
import asyncio
import inspect
import logging
import threading
import collections

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

class S2AQueue(s_base.Base):
    '''
    Sync single producer, async single consumer finite queue with blocking at empty and full.
    '''
    async def __anit__(self, max_entries, drain_level=None):
        '''
        Args:
            max_entries (int): the maximum number of entries that can be in the queue.

            drain_level (Optional[int]): once the queue is full, no more entries will be admitted until the number of
                entries falls below this parameter.  Defaults to half of max_entries.
        '''

        await s_base.Base.__anit__(self)
        self.deq = collections.deque()
        self.notdrainingevent = threading.Event()
        self.notdrainingevent.set()
        self.notemptyevent = asyncio.Event(loop=self.loop)
        self.max_entries = max_entries
        self.drain_level = max_entries // 2 if drain_level is None else drain_level
        assert self.drain_level

        async def _onfini():
            self.notemptyevent.set()
            self.notdrainingevent.set()
        self.onfini(_onfini)

    async def get(self):
        '''
        Async pend retrieve on the queue
        '''
        while not self.isfini:
            try:
                val = self.deq.popleft()
                break
            except IndexError:
                self.notemptyevent.clear()
                if len(self.deq):
                    continue
                await self.notemptyevent.wait()
        else:
            return None  # Raise fini?

        if not self.notdrainingevent.is_set() and len(self.deq) < self.drain_level:
            self.notdrainingevent.set()

        return val

    def put(self, item):
        '''
        Put onto the queue.  Pend if the queue is full or draining.
        '''
        while not self.isfini:
            if len(self.deq) >= self.max_entries:
                self.notdrainingevent.clear()
            if not self.notdrainingevent.is_set():
                self.notdrainingevent.wait()
                continue
            break
        else:
            return

        self.deq.append(item)

        # N.B. asyncio.Event.is_set is trivially threadsafe, though Event.set is not

        if not self.notemptyevent.is_set():
            self.loop.call_soon_threadsafe(self.notemptyevent.set)

    def __len__(self):
        return len(self.deq)

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

async def genr2agenr(func, *args, qsize=100, **kwargs):
    ''' Returns an async generator that receives a stream of messages from a sync generator func(*args, **kwargs) '''
    class SentinelClass:
        pass

    sentinel = SentinelClass()

    async with await S2AQueue.anit(qsize) as chan:

        def sync():
            try:
                for msg in func(*args, **kwargs):
                    chan.put(msg)
            finally:
                chan.put(sentinel)

        task = asyncio.get_running_loop().run_in_executor(None, sync)

        while True:
            msg = await chan.get()
            if msg is sentinel:
                break
            yield msg

        await task

async def event_wait(event: asyncio.Event, timeout=None):
    '''
    Wait on an an asyncio event with an optional timeout

    Returns:
        true if the event got set, None if timed out
    '''
    if timeout is None:
        await event.wait()
        return True

    try:
        await asyncio.wait_for(event.wait(), timeout)
    except asyncio.TimeoutError:
        return False
    return True

async def ornot(func, *args, **kwargs):
    '''
    Calls func and awaits it if a returns a coroutine.

    Note:
        This is useful for implementing a function that might take a telepath proxy object or a local object, and you
        must call a non-async method on that object.

        This is also useful when calling a callback that might either be a coroutine function or a regular function.
    Usage:
        ok = await s_coro.ornot(maybeproxy.allowed, 'path')
    '''

    retn = func(*args, **kwargs)
    if iscoro(retn):
        return await retn
    return retn
