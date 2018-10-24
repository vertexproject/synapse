'''
Async/Coroutine related utilities.
'''
import asyncio
import inspect
import logging

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.lib.base as s_base
import synapse.lib.queue as s_queue

def iscoro(item):
    return inspect.iscoroutine(item)

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

    async with await s_queue.S2AQueue.anit(qsize) as chan:

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
