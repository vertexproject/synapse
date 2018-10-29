'''
Async/Coroutine related utilities.
'''
import asyncio
import inspect
import logging
<< << << < HEAD
import functools
import threading
import collections
== == == =
>>>>>> > 010

logger = logging.getLogger(__name__)

import synapse.glob as s_glob
import synapse.common as s_common

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
    '''
    Returns an async generator that receives a stream of messages from a sync generator func(*args, **kwargs)
    '''
    class SentinelClass:
        pass

    sentinel = s_common.NoValu()

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

class GenrHelp:

    def __init__(self, genr):
        self.genr = genr

    def __aiter__(self):
        return self.genr

    async def spin(self):
        async for x in self.genr:
            pass

    async def list(self):
        return [x async for x in self.genr]

def genrhelp(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        return GenrHelp(f(*args, **kwargs))
    return func

class AsyncToSyncCMgr():
    '''
    Wraps an async context manager as a sync one
    '''
    def __init__(self, func, *args, **kwargs):
        self.amgr = func(*args, **kwargs)

    def __enter__(self):
        return s_glob.plex.coroToSync(self.amgr.__aenter__())

    def __exit__(self, *args):
        return s_glob.plex.coroToSync(self.amgr.__aexit__(*args))
