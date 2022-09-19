import os
import signal
import asyncio
import logging
import threading
import faulthandler

logger = logging.getLogger(__name__)

_glob_loop = None
_glob_thrd = None


def _asynciostacks(*args, **kwargs):  # pragma: no cover
    '''
    A signal handler used to print asyncio task stacks and thread stacks.
    '''
    print(80 * '*')
    print('Asyncio tasks stacks:')
    tasks = asyncio.all_tasks(_glob_loop)
    for task in tasks:
        task.print_stack()
    print(80 * '*')
    print('Faulthandler stack frames per thread:')
    faulthandler.dump_traceback()
    print(80 * '*')

def _threadstacks(*args, **kwargs):  # pragma: no cover
    '''
    A signal handler used to print thread stacks.
    '''
    print(80 * '*')
    print('Faulthandler stack frames per thread:')
    faulthandler.dump_traceback()
    print(80 * '*')

signal.signal(signal.SIGUSR1, _threadstacks)
signal.signal(signal.SIGUSR2, _asynciostacks)

def initloop():

    global _glob_loop
    global _glob_thrd

    # if there's no global loop....
    if _glob_loop is None:

        # check if it's us....
        try:
            _glob_loop = asyncio.get_running_loop()
            # if we get here, it's us!
            _glob_thrd = threading.current_thread()
            # Enable debug and greedy coro collection
            setGreedCoro(_glob_loop)

        except RuntimeError:
            _glob_loop = asyncio.new_event_loop()
            setGreedCoro(_glob_loop)

            _glob_thrd = threading.Thread(target=_glob_loop.run_forever, name='SynLoop', daemon=True)
            _glob_thrd.start()

    return _glob_loop

def setGreedCoro(loop: asyncio.AbstractEventLoop):
    greedy_threshold = os.environ.get('SYN_GREEDY_CORO')
    if greedy_threshold is not None:  # pragma: no cover
        logger.info(f'Setting ioloop.slow_callback_duration to {greedy_threshold}')
        loop.set_debug(True)
        loop.slow_callback_duration = float(greedy_threshold)

def iAmLoop():
    initloop()
    return threading.current_thread() == _glob_thrd

def sync(coro, timeout=None):
    '''
    Schedule a coroutine to run on the global loop and return it's result.

    Args:
        coro (coroutine): The coroutine instance.

    Notes:
        This API is thread safe and should only be called by non-loop threads.
    '''
    loop = initloop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout)

def synchelp(f):
    '''
    The synchelp decorator allows the transparent execution of
    a coroutine using the global loop from a thread other than
    the event loop.  In both use cases, the actual work is done
    by the global event loop.

    Examples:

        Use as a decorator::

            @s_glob.synchelp
            async def stuff(x, y):
                await dostuff()

        Calling the stuff function as regular async code using the standard await syntax::

            valu = await stuff(x, y)

        Calling the stuff function as regular sync code outside of the event loop thread::

            valu = stuff(x, y)

    '''
    def wrap(*args, **kwargs):

        coro = f(*args, **kwargs)

        if not iAmLoop():
            return sync(coro)

        return coro

    return wrap
