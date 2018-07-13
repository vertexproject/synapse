import threading
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    import synapse.lib.plex as s_plex  # NOQA
    import synapse.lib.threads as s_threads  # NOQA

lock = threading.RLock()

plex: Optional['s_plex.Plex'] = None     # s_plex.Plex()
pool: Optional['s_threads.Pool'] = None     # s_threads.Pool(maxsize=tmax)

def inpool(f):
    '''
    Wrap the given function to be called from the global thread pool.
    '''
    def wrap(*args, **kwargs):
        return pool.call(f, *args, **kwargs)
    return wrap

def sync(coro, timeout=None):
    '''
    A terse way to return a value from a coroutine
    via the global Plex() event loop.
    '''
    return plex.coroToSync(coro, timeout=timeout)

def synchelp(f):
    '''
    The synchelp decorator allows the transparent execution of
    a coroutine using the global plex from a thread other than
    the event loop:

    @s_glob.synchelp
    async def stuff(x, y):
        ...

    # From within the global plex event loop, the standard await:

    valu = await stuff(x, y)

    # From a worker thread, outside the plex event loop:

    valu = stuff(x, y)

    # In both cases, the actual work is done by the global loop.
    '''

    def wrap(*args, **kwargs):

        coro = f(*args, **kwargs)

        if not plex.iAmLoop():
            return sync(coro)

        return coro

    return wrap

async def executor(func, *args, **kwargs):
    '''
    Run the given function in an executor to the global loop.
    '''
    return await plex.executor(func, *args, **kwargs)
