'''
Process spawning utilities.
'''
import queue
import asyncio
import logging
import multiprocessing

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
