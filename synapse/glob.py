import asyncio
import threading

_glob_loop = None
_glob_thrd = None

def initloop():

    global _glob_loop
    global _glob_thrd

    # if there's no global loop....
    if _glob_loop is None:

        # check if it's us....
        try:
            _glob_loop = asyncio.get_running_loop()
            # if we get here, it's us!
            _glob_thrd = threading.currentThread()

        except RuntimeError as e:

            # otherwise, lets fire one...
            _glob_loop = asyncio.new_event_loop()

            _glob_thrd = threading.Thread(target=_glob_loop.run_forever)
            _glob_thrd.setDaemon(True)
            _glob_thrd.start()

    return _glob_loop

def iAmLoop():
    initloop()
    return threading.currentThread() == _glob_thrd

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

def coroToTask(coro):
    '''
    Schedule a coro to run on the global loop and return a task.

    Args:
        coro (coroutine): The coroutine instance.

    Notes:
        This API is thread safe.

    Returns:
        concurrent.futures.Future: A Future to wait on.
    '''
    loop = initloop()
    return asyncio.run_coroutine_threadsafe(coro, loop)

def synchelp(f):
    '''
    The synchelp decorator allows the transparent execution of
    a coroutine using the global loop from a thread other than
    the event loop:

    @s_glob.synchelp
    async def stuff(x, y):
        ...

    # From within the global event loop, the standard await:

    valu = await stuff(x, y)

    # From a worker thread, outside the event loop:

    valu = stuff(x, y)

    # In both cases, the actual work is done by the global loop.
    '''
    def wrap(*args, **kwargs):

        coro = f(*args, **kwargs)

        if not iAmLoop():
            return sync(coro)

        return coro

    return wrap
