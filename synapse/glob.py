import threading

lock = threading.Lock()

# A global Plex instance for managing socket i/o.
plex = None

# A global Sched instance for maint routines
sched = None

# A host info dictionary for "thishost" API
hostinfo = None
