import threading

lock = threading.RLock()

# A global / default PkiStor used by getUserPki()
pki = None

# A global Plex instance for managing socket i/o.
plex = None

# A global Sched instance for maint routines
sched = None

# A host info dictionary for "thishost" API
hostinfo = None
