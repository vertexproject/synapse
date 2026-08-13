'''
Process pool related utilities.

Importing this module has the side effect of creating a forkserver and should be done
early in the creation of a process which needs it.
'''
import os
import atexit
import signal
import asyncio
import logging
import multiprocessing
import concurrent.futures

# Bind BrokenProcessPool as a module-level name. concurrent.futures lazily binds
# only ProcessPoolExecutor/ThreadPoolExecutor via __getattr__, not the .process
# submodule; a process that never creates a pool (the pool is MainProcess-only,
# below) never imports it, so `except concurrent.futures.process.BrokenProcessPool`
# would raise AttributeError and mask the real exception.
from concurrent.futures.process import BrokenProcessPool

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.lib.logging as s_logging
import synapse.lib.process as s_process

forkpool = None
forkpool_sema = None
max_workers = None
def_max_workers = 8
reserved_workers = 2

_pool_logconf = None

def _initPoolSignals():  # pragma: no cover
    '''
    A pool worker exits when the process owning the pool shuts it down, so SIGINT is
    not this process's to handle: Ctrl-C reaches every process in the group, and a
    worker parked in call_queue.get() stays there until that shutdown closes the
    queue under it.

    This is the initializer a pool is built with, so it covers workers spawned
    before any logging config arrives; _setPoolLogging swaps in _initPoolWorker,
    which sets the same disposition.
    '''
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def initForkPool():
    '''
    Initialize the shared forkserver process pool for this process.

    Called automatically at import for the MainProcess. Child processes that
    run their own CPU-bound work must call it explicitly to get a pool;
    otherwise forked()/semafork() fall back to a per-call spawn. Idempotent.
    '''
    global forkpool, forkpool_sema, max_workers

    if forkpool is not None:
        return

    try:
        mpctx = multiprocessing.get_context('forkserver')
        max_workers = int(os.getenv('SYN_FORKED_WORKERS', 0)) or max(def_max_workers, os.cpu_count() or def_max_workers)
        forkpool = concurrent.futures.ProcessPoolExecutor(mp_context=mpctx, max_workers=max_workers,
                                                          initializer=_initPoolSignals)
        atexit.register(forkpool.shutdown)
        forkpool_sema = asyncio.Semaphore(max(1, max_workers - reserved_workers))
    except OSError as e:  # pragma: no cover
        max_workers = None
        logger.warning(f'Failed to init forkserver pool, fallback enabled: {e}', exc_info=True)
        return

    # re-apply logging config set before the pool existed
    if _pool_logconf is not None:
        _setPoolLogging(_pool_logconf)

def _isMainImport():
    '''
    True only in a real MainProcess, and not while a child re-imports the main module.

    A forkserver process is also named MainProcess and imports its parent's main
    module, so for any ``python -m synapse.servers.*`` this module is imported in
    there too. CPython sets ``_inheriting`` on the current process for the duration
    of that import, which is what separates it from a real MainProcess and keeps the
    auto-init below to one pool per process.
    '''
    proc = multiprocessing.current_process()

    if proc.name != 'MainProcess':
        return False

    return not getattr(proc, '_inheriting', False)

if _isMainImport():
    # only auto-create the forkpool in the MainProcess...
    initForkPool()

def finiForkPool():
    '''
    Release this process's forkserver pool: shut it down and drop the last
    reference to it, so its queues give up their five named semaphores. Idempotent.

    Call this from the teardown of a process that owns its pool, such as a read
    worker. It covers the signalled path, where SIGINT reaches the whole process
    group and atexit is never reached; the pool's own worker takes that signal at
    the same moment, so this stands up to a pool that is already broken.

    Do NOT call this from a Cell fini: the pool is per process and shared by every
    cell in it, so tearing it down for one cell breaks the others.
    '''
    global forkpool, forkpool_sema, max_workers

    pool = forkpool
    if pool is None:
        return

    forkpool = None
    forkpool_sema = None
    max_workers = None

    try:
        # this call owns the pool's last reference: its queues release their
        # semaphores once the executor is deallocated, so atexit gives up the bound
        # method it holds from initForkPool.
        atexit.unregister(pool.shutdown)

        # shutdown() waits by default, and that join is what releases the queues. It
        # returns even when a pool worker was signalled alongside us.
        pool.shutdown(cancel_futures=True)

    except Exception:  # pragma: no cover
        logger.exception('Error shutting down the forkserver pool')

def _runtodo(todo):  # pragma: no cover
    return todo[0](*todo[1], **todo[2])

def _initPoolWorker(logconf):
    s_logging.setup(**logconf)

    # the disposition _initPoolSignals explains: this worker leaves SIGINT to the
    # process that owns the pool, which drives it out of call_queue.get().
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    p = multiprocessing.current_process()
    logger.debug(f'Initialized new forkserver pool worker: name={p.name} pid={p.ident}')

def _setPoolLogging(logconf):
    # This must be called before any calls to forked() and _parserforked()
    global _pool_logconf
    _pool_logconf = logconf
    todo = (_initPoolWorker, (logconf,), {})
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
        except BrokenProcessPool as e:  # pragma: no cover
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
    except BrokenProcessPool as e:  # pragma: no cover
        logger.exception(f'Fatal error executing forked task: {func} {args} {kwargs}')
        raise s_exc.FatalErr(mesg=f'Fatal error encountered: {e}') from None
