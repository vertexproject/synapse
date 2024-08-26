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

bgtasks = set()
def create_task(coro):

    task = asyncio.get_running_loop().create_task(coro)
    bgtasks.add(task)

    def done(t):
        bgtasks.remove(t)

    task.add_done_callback(done)

    return task

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

def _exectodo(que, todo, logconf):
    # This is a new process: configure logging
    s_common.setlogging(logger, **logconf)
    func, args, kwargs = todo
    try:
        ret = func(*args, **kwargs)
        que.put(ret)
    except s_exc.SynErr as e:
        logger.exception(f'Error executing spawn function {func}')
        que.put(e)
    except Exception as e:
        # exceptions could be non-pickleable so wrap in SynErr
        logger.exception(f'Error executing spawn function {func}')
        name, info = s_common.err(e)
        mesg = f'Error executing spawn function: {name}: {info.get("mesg")}'
        exc = s_exc.SynErr(mesg=mesg, name=name, info=info)
        que.put(exc)

async def spawn(todo, timeout=None, ctx=None, log_conf=None):
    '''
    Run a todo (func, args, kwargs) tuple in a multiprocessing subprocess.

    Args:
        todo (tuple): A tuple of function, ``*args``, and ``**kwargs``.
        timeout (int): The timeout to wait for the todo function to finish.
        ctx (multiprocess.Context): A optional multiprocessing context object.
        log_conf (dict): An optional logging configuration for the spawned process.

    Notes:
        The contents of the todo tuple must be able to be pickled for execution.
        This means that locally bound functions are not eligible targets for spawn.

    Returns:
        The return value of executing the todo function.
    '''
    if ctx is None:
        ctx = multiprocessing.get_context('spawn')
    if log_conf is None:
        log_conf = {}

    que = ctx.Queue()
    proc = ctx.Process(target=_exectodo,
                       args=(que, todo, log_conf))

    def execspawn():

        proc.start()

        while True:
            try:
                # we have to block/wait on the queue because the sender
                # could need to stream the return value in multiple chunks
                retn = que.get(timeout=1)
                # now that we've retrieved the response, it should have exited.
                proc.join()
                return retn
            except queue.Empty:
                if not proc.is_alive():
                    proc.join()
                    mesg = f'Spawned process {proc} exited for {todo[0]} without a result.'
                    raise s_exc.SpawnExit(mesg=mesg, code=proc.exitcode)

    try:

        coro = executor(execspawn)

        retn = await s_common.wait_for(coro, timeout=timeout)
        if isinstance(retn, Exception):
            raise retn

        return retn

    except (asyncio.CancelledError, asyncio.TimeoutError):
        proc.terminate()
        raise

forkpool = None
forkpool_sema = None
max_workers = None
def_max_workers = 8
reserved_workers = 2
if multiprocessing.current_process().name == 'MainProcess':
    # only create the forkpools in the MainProcess...
    try:
        mpctx = multiprocessing.get_context('forkserver')
        max_workers = int(os.getenv('SYN_FORKED_WORKERS', 0)) or max(def_max_workers, os.cpu_count() or def_max_workers)
        forkpool = concurrent.futures.ProcessPoolExecutor(mp_context=mpctx, max_workers=max_workers)
        atexit.register(forkpool.shutdown)
        forkpool_sema = asyncio.Semaphore(max(1, max_workers - reserved_workers))
    except OSError as e:  # pragma: no cover
        max_workers = None
        logger.warning(f'Failed to init forkserver pool, fallback enabled: {e}', exc_info=True)

def _runtodo(todo):
    return todo[0](*todo[1], **todo[2])

def _init_pool_worker(logger_, logconf):
    s_common.setlogging(logger_, **logconf)
    p = multiprocessing.current_process()
    logger.debug(f'Initialized new forkserver pool worker: name={p.name} pid={p.ident}')

_pool_logconf = None
def set_pool_logging(logger_, logconf):
    # This must be called before any calls to forked() and _parserforked()
    global _pool_logconf
    _pool_logconf = logconf
    todo = s_common.todo(_init_pool_worker, logger_, logconf)
    if forkpool is not None:
        forkpool._initializer = _runtodo
        forkpool._initargs = (todo,)

async def forked(func, *args, **kwargs):
    '''
    Execute a target function in the shared forked process pool
    and fallback to running in a spawned process if the pool is unavailable.

    Args:
        func: The target function.
        *args: Function positional arguments.
        **kwargs: Function keyword arguments.

    Returns:
        The target function return.
    '''
    todo = (func, args, kwargs)

    if forkpool is not None:
        try:
            return await asyncio.get_running_loop().run_in_executor(forkpool, _runtodo, todo)
        except concurrent.futures.process.BrokenProcessPool as e:  # pragma: no cover
            logger.exception(f'Shared forkserver pool is broken, fallback enabled: {func}')

    logger.debug(f'Forkserver pool using spawn fallback: {func}')
    return await spawn(todo, log_conf=_pool_logconf)

async def semafork(func, *args, **kwargs):
    '''
    Execute a target function in the shared forked process pool
    gated by a semaphore to ensure there are workers reserved for the Storm parser.

    Args:
        func: The target function.
        *args: Function positional arguments.
        **kwargs: Function keyword arguments.

    Returns:
        The target function return.
    '''
    if forkpool_sema is None:
        return await forked(func, *args, **kwargs)

    async with forkpool_sema:
        return await forked(func, *args, **kwargs)

async def _parserforked(func, *args, **kwargs):
    '''
    Execute a target function in the shared forked process pool
    and fallback to running in the default executor if the pool is unavailable.

    NOTE: This function is intended to only be used by the Storm parser

    Args:
        func: The target function.
        *args: Function positional arguments.
        **kwargs: Function keyword arguments.

    Returns:
        The target function return.

    Raises:
        The function may raise from the target function, or raise an s_exc.FatalErr in the event of a broken forked
        process pool. The fatalerr represents an unrecoverable application state.
    '''
    todo = (func, args, kwargs)
    try:
        return await asyncio.get_running_loop().run_in_executor(forkpool, _runtodo, todo)
    except concurrent.futures.process.BrokenProcessPool as e:  # pragma: no cover
        logger.exception(f'Fatal error executing forked task: {func} {args} {kwargs}')
        raise s_exc.FatalErr(mesg=f'Fatal error encountered: {e}') from None
