'''
Async/Coroutine related utilities.
'''
import queue
import asyncio
import inspect
import logging
import functools
import multiprocessing

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob

def iscoro(item):
    return inspect.iscoroutine(item)

async def agen(item):
    '''
    Wrap an async_generator *or* generator in an async_generator.

    Notes:
        Do not use this for a synchronous generator which would cause
        none-blocking IO; otherwise that IO will block the ioloop.
    '''
    if getattr(item, '__aiter__', None) is not None:
        async for x in item:
            yield x
        return

    for x in item:
        yield x

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

def _exectodo(que, todo):
    func, args, kwargs = todo
    try:
        que.put(func(*args, **kwargs))
    except Exception as e:
        que.put(e)

async def spawn(todo, timeout=None, ctx=None):
    '''
    Run a todo (func, args, kwargs) tuple in a multiprocessing subprocess.

    Args:
        todo (tuple): A tuple of function, *args, and **kwargs.
        timeout (int): The timeout to wait for the todo function to finish.
        ctx (multiprocess.Context): A optional multiprocessing context object.

    Notes:
        The contents of the todo tuple must be able to be pickled for execution.
        This means that locally bound functions are not eligible targets for spawn.

    Returns:
        The return value of executing the todo function.
    '''
    if ctx is None:
        ctx = multiprocessing.get_context('spawn')

    que = ctx.Queue()
    proc = ctx.Process(target=_exectodo, args=(que, todo))

    def execspawn():
        proc.start()
        proc.join()
        try:
            return que.get(block=False)
        except queue.Empty:
            raise s_exc.SpawnExit(code=proc.exitcode)

    try:

        coro = executor(execspawn)

        retn = await asyncio.wait_for(coro, timeout=timeout)
        if isinstance(retn, Exception):
            raise retn

        return retn

    except (asyncio.CancelledError, asyncio.TimeoutError):
        proc.terminate()
        raise
