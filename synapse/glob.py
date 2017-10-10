import threading

lock = threading.RLock()

import synapse.lib.sched as s_sched
import synapse.lib.threads as s_threads

pool = s_threads.Pool()
sched = s_sched.Sched(pool=pool)
