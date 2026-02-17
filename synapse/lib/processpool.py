'''
Process pool related utilities.

Importing this module has the side effect of creating a forkserver and should be done
early in the creation of a process which needs it.
'''
import os
import atexit
import asyncio
import logging
import multiprocessing
import concurrent.futures

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.lib.logging as s_logging
import synapse.lib.process as s_process

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

def _runtodo(todo):  # pragma: no cover
    return todo[0](*todo[1], **todo[2])


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
    return await s_process.spawn(todo, logconf=s_logging.getLogConf())

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
