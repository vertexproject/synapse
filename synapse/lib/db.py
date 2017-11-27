import threading

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.queue as s_queue
import synapse.lib.scope as s_scope

class Xact(s_eventbus.EventBus):
    '''
    A unified helper for managing db transaction behavior.
    '''
    def __init__(self, pool, db):
        s_eventbus.EventBus.__init__(self)

        self.db = db
        self.refs = 0
        self.pool = pool
        self.curs = None
        self.lockd = False

        self.onfini(self._onXactFini)

    def _onXactFini(self):
        self.db.commit()
        self.db.close()
        if self.lockd:
            self.pool.wlock.release()

    def wrlock(self):
        '''
        Acquire the pool write lock for the remainder of this transaction.
        '''
        while not self.lockd:
            if self.isfini:
                raise s_common.IsFini()

            self.lockd = self.pool.wlock.acquire(timeout=1)

    def execute(self, *args):
        '''
        Execute a query on the cursor for this xact.

        NOTE: This *will* acquire the write-lock for
              the db Pool() until your transaction is
              complete.  Use select() for read queries.

        Args:
            *args (list): The args to hand to cursor execute().

        Returns:
            Cursor: see DB API
        '''
        self.wrlock()
        return self.curs.execute(*args)

    def update(self, *args):
        self.wrlock()
        return self.execute(*args).rowcount

    def executemany(self, *args):
        self.wrlock()
        return self.curs.executemany(*args)

    def select(self, *args):
        '''
        Read-only optimized cursor execute method.

        Args:
            *args (list): The args to hand to cursor execute().

        Returns:
            Cursor: see DB API
        '''
        if self.isfini:
            raise s_common.IsFini()

        return self.curs.execute(*args)

    def commit(self):
        '''
        Perform an incremental commit().

        See DB API
        '''
        # on an incremental commit, release the wlock
        self.db.commit()
        if self.lockd:
            self.lockd = False
            self.pool.wlock.release()

    def __enter__(self):
        self.refs += 1

        if self.refs == 1:
            self.curs = self.db.cursor()

        return self

    def __exit__(self, exc, cls, tb):

        self.refs -= 1
        if self.refs == 0:

            if not self.isfini:
                self.curs.close()
                self.db.commit()

            if self.lockd:
                self.lockd = False
                self.pool.wlock.release()

            self.curs = None
            self.pool._put(self)

class Pool(s_eventbus.EventBus):
    '''
    The Pool allows generic db connection pooling using
    a factory/ctor method and a python queue.
    '''
    _xact_ctor = Xact

    def __init__(self, size, ctor):
        s_eventbus.EventBus.__init__(self)

        self.size = size
        self.iden = s_common.guid()

        self.dbque = s_queue.Queue()
        self.onfini(self.dbque.fini)

        self.wlock = threading.Lock()
        self.xacts = [self._initXact(ctor()) for i in range(size)]

    def _initXact(self, db):
        xact = self._xact_ctor(self, db)
        self.onfini(xact.fini)
        self.dbque.put(xact)
        return xact

    def _put(self, xact):
        s_scope.pop(self.iden)
        self.dbque.put(xact)

    def xact(self):

        xact = s_scope.get(self.iden)
        if xact is not None:
            return xact

        xact = self.dbque.get()
        s_scope.set(self.iden, xact)
        return xact

    def avail(self):
        return self.dbque.size()
