'''
Async/Coroutine related utilities.
'''
import os
import math
import queue
import atexit
import asyncio
import inspect
import logging
import functools
import contextlib
import multiprocessing
import concurrent.futures

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

def iscoro(item):
    return inspect.iscoroutine(item)

async def agen(item):
    '''
    Wrap an async_generator *or* generator in an async_generator.

    Notes:
        Do not use this for a synchronous generator which would cause
        non-blocking IO; otherwise that IO will block the ioloop.
    '''
    if getattr(item, '__aiter__', None) is not None:
        async with contextlib.aclosing(item) as agen:
            async for x in agen:
                yield x
        return

    for x in item:
        yield x

async def chunks(genr, size=100):

    retn = []
    async for item in genr:

        retn.append(item)

        if len(retn) == size:
            yield retn
            retn = []

    if retn:
        yield retn

async def pause(genr, iterations=10):
    idx = 0

    async for out in agen(genr):
        yield out
        idx += 1

        if idx % iterations == 0:
            await asyncio.sleep(0)

    return

def executor(func, *args, **kwargs):
    '''
    Execute a non-coroutine function in the ioloop executor pool.

    Args:
        func: Function to execute.
        *args: Args for the function.
        **kwargs: Kwargs for the function.

    Examples:

        Execute a blocking API call in the executor pool::

            import requests

            def block(url, params=None):
                return requests.get(url, params=params).json()

            fut = s_coro.executor(block, 'http://some.tld/thign')
            resp = await fut

    Returns:
        asyncio.Future: An asyncio future.
    '''

    def real():
        return func(*args, **kwargs)

    return asyncio.get_running_loop().run_in_executor(None, real)

class Event(asyncio.Event):

    async def timewait(self, timeout=None):

        if timeout is None:
            await self.wait()
            return True

        try:
            await s_common.wait_for(self.wait(), timeout)
        except asyncio.TimeoutError:
            return False

        return True

async def event_wait(event: asyncio.Event, timeout=None):
    '''
    Wait on an an asyncio event with an optional timeout

    Returns:
        true if the event got set, False if timed out
    '''
    if timeout is None:
        await event.wait()
        return True

    try:
        await s_common.wait_for(event.wait(), timeout)
    except asyncio.TimeoutError:
        return False
    return True

async def waittask(task, timeout=None):
    '''
    Await a task without cancelling it when you time out.

    Returns:
        boolean: True if the task completed before the timeout.
    '''
    futu = asyncio.get_running_loop().create_future()
    task.add_done_callback(futu.set_result)
    try:
        await s_common.wait_for(futu, timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        task.remove_done_callback(futu.set_result)

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

def has_running_loop():
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False

bgtasks = set()
def create_task(coro):

    task = asyncio.get_running_loop().create_task(coro)
    bgtasks.add(task)

    def done(t):
        bgtasks.remove(t)

    task.add_done_callback(done)

    return task

async def await_bg_tasks(timeout=None):

    if not bgtasks:
        return []

    coro = asyncio.gather(*tuple(bgtasks), return_exceptions=True)
    try:
        return await s_common.wait_for(coro, timeout)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        return []

class GenrHelp:

    def __init__(self, genr):
        assert genr is not None
        self.genr = genr

    def __aiter__(self):
        return self.genr

    def __iter__(self):

        try:

            while True:
                item = s_glob.sync(self.genr.__anext__())
                yield item

        except StopAsyncIteration:
            return

        except GeneratorExit:
            # Raised if a synchronous consumer exited an iterator early.
            # Signal the generator to close down.
            s_glob.sync(self.genr.aclose())
            raise

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
