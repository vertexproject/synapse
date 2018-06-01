import sqlite3

import synapse.lib.db as s_db

'''
Integration utilities for sqlite db pools.
'''

# turn on db cache sharing
try:
    sqlite3.enable_shared_cache(1)
except:
    # Doesn't work on MacOS
    pass

def pool(size, path, **kwargs):
    '''
    Create an sqlite connection pool.

    Args:
        size (int): Number of connections in the pool.
        path (str): Path to the sqlite file.

    Returns:
        s_db.Pool: A DB Pool for sqlite connections.
    '''
    def ctor():
        db = sqlite3.connect(path, check_same_thread=False)
        db.cursor().execute('PRAGMA read_uncommitted=1').close()
        return db

    return s_db.Pool(size, ctor=ctor)
