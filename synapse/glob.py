import threading
import multiprocessing

lock = threading.RLock()

import synapse.lib.net as s_net
import synapse.lib.sched as s_sched
import synapse.lib.threads as s_threads

# go high since they will mostly be IO bound
tmax = multiprocessing.cpu_count() * 8

plex = s_net.Plex()
pool = s_threads.Pool(maxsize=tmax)
sched = s_sched.Sched(pool=pool)

def inpool(f):
    '''
    Wrap the given function to be called from the global thread pool.
    '''
    def wrap(*args, **kwargs):
        return pool.call(f, *args, **kwargs)
    return wrap
