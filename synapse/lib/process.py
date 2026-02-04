'''
Process pool related utilities.

Importing this module has the side effect of creating a forkserver and should be done
early in the creation of a process which needs it.
'''
import os
import queue
import atexit
import asyncio
import logging
import multiprocessing
import concurrent.futures

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro

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

        coro = s_coro.executor(execspawn)

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
