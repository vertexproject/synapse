import sqlite3

import synapse.lib.db as s_db

'''
Integration utilities for sqlite db pools.
'''

# turn on db cache sharing
sqlite3.enable_shared_cache(1)

def pool(size, path, **kwargs):
    '''
    Create an sqlite connection pool.

    Args:
        size (int): Number of connections in the pool
    '''
    def ctor():
        db = sqlite3.connect(path, check_same_thread=False)
        db.cursor().execute('PRAGMA read_uncommitted=1').close()
        return db

    return s_db.Pool(size, ctor=ctor)
