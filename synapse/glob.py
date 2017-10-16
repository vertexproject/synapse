import threading
import multiprocessing

lock = threading.RLock()

import synapse.lib.sched as s_sched
import synapse.lib.threads as s_threads

# go high since they will mostly be IO bound
tmax = multiprocessing.cpu_count() * 8

pool = s_threads.Pool(maxsize=tmax)
sched = s_sched.Sched(pool=pool)
