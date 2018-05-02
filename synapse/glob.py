import threading

lock = threading.RLock()

plex = None     # s_net.Plex()
pool = None     # s_threads.Pool(maxsize=tmax)
sched = None    # s_sched.Sched(pool=pool)

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
    The synchelp decorator allows the transparant execution of
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
