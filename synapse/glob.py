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
