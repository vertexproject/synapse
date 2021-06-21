'''
Async/Coroutine related utilities.
'''
import queue
import atexit
import asyncio
import inspect
import logging
import functools
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

async def waittask(task, timeout=None):
    '''
    Await a task without cancelling it when you time out.

    Returns:
        boolean: True if the task completed before the timeout.
    '''
    futu = asyncio.get_running_loop().create_future()
    task.add_done_callback(futu.set_result)
    try:
        await asyncio.wait_for(futu, timeout=timeout)
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
        todo (tuple): A tuple of function, ``*args``, and ``**kwargs``.
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

class ProcPool:
    '''
    Instantiate a forkserver process pool once for the application.

    Forkserver will spawn the main process when anit() is called.
    When the first job is submitted, processes are forked from the spawned process.

    NOTE: When the first job is submitted all max_workers processes will be spun up.
    Starting in 3.9 processes will be spun up on demand when there are no idle processes.
    '''

    _ctx = None
    _pool = None

    @classmethod
    async def anit(cls, max_workers=None, logconf=None):
        # NOTE: Making this async for future flexibility

        if cls._pool is not None:
            return cls()

        _initializer = None
        if logconf is not None:
            _initializer = functools.partial(s_common.setlogging, logger, **logconf)

        # add this here so we are ahead of ProcessPoolExecutor atexit (see bpo-39098 fixed in 3.9)
        atexit.register(cls._shutdown)

        _ctx = multiprocessing.get_context('forkserver')
        cls._pool = concurrent.futures.ProcessPoolExecutor(
            mp_context=_ctx,
            max_workers=max_workers,
            initializer=_initializer
        )
        cls._ctx = _ctx

        return cls()

    @classmethod
    def _shutdown(cls):
        if cls._pool is not None:
            cls._pool.shutdown(wait=True)
            cls._pool = None

    @staticmethod
    def _run_coro(func, *args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    async def execute(self, func, *args, **kwargs):

        if self._pool is None:
            raise s_exc.SynErr(mesg='Process pool is not running!')

        if inspect.iscoroutinefunction(func):
            real = functools.partial(self._run_coro, func, *args, **kwargs)
        else:
            real = functools.partial(func, *args, **kwargs)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, real)
