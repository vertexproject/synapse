import os
import functools
import contextlib

import logging
logger = logging.getLogger(__name__)

import lmdb  # type: ignore

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.base as s_base

class Slab(s_base.Base):
    '''
    A "monolithic" LMDB instance for use in a asyncio loop thread.
    '''
    COMMIT_PERIOD = 1.0  # time between commits

    async def __anit__(self, path, **kwargs):
        await s_base.Base.__anit__(self)

        opts = kwargs

        self.path = path
        self.optspath = os.path.join(path, 'opts.yaml')

        if os.path.isfile(self.optspath):
            opts.update(s_common.yamlload(self.optspath))

        self.mapsize = opts.get('map_size')
        if self.mapsize is None:
            raise Exception('Slab requires map_size!')

        # save the transaction deltas in case of error...
        self.xactops = []
        self.recovering = False

        opts.setdefault('max_dbs', 128)
        opts.setdefault('writemap', True)

        # if growsize is not set, we double...
        self.maxsize = opts.pop('maxsize', None)
        self.growsize = opts.pop('growsize', None)

        self.readonly = opts.get('readonly', False)

        self.lenv = lmdb.open(path, **opts)

        self.scans = set()

        self.holders = 0

        self.dirty = False
        if self.readonly:
            self.xact = None
            self.txnrefcount = 0
        else:
            self._initCoXact()

        self.onfini(self._onCoFini)
        self.schedCoro(self._runSyncLoop())

    def _acqXactForReading(self):
        if not self.readonly:
            return self.xact
        if not self.txnrefcount:
            self._initCoXact()

        self.txnrefcount += 1
        return self.xact

    def _relXactForReading(self):
        if not self.readonly:
            return
        self.txnrefcount -= 1
        if not self.txnrefcount:
            self._finiCoXact()

    def _saveOptsFile(self):
        opts = {'map_size': self.mapsize, 'growsize': self.growsize}
        s_common.jssave(opts, self.optspath)

    async def _runSyncLoop(self):
        while not self.isfini:
            await self.waitfini(timeout=self.COMMIT_PERIOD)
            if self.isfini:
                # There's no reason to forcecommit on fini, because there's a separate handler to already do that
                break
            if self.holders == 0:
                self.forcecommit()

    async def _onCoFini(self):
        assert s_glob.plex.iAmLoop()
        self._finiCoXact()
        self.lenv.close()
        del self.lenv

    def _finiCoXact(self):

        assert s_glob.plex.iAmLoop()

        [scan.bump() for scan in self.scans]

        # Readonly or self.xact has already been closed
        if self.xact is None:
            return

        self.xact.commit()

        self.xactops.clear()

        del self.xact
        self.xact = None

    def grow(self, size=None):
        '''
        Close out the current transaction and resize the memory map.
        '''
        with self._noCoXact():
            self._growMapSize(size=size)

    def _growMapSize(self, size=None):

        mapsize = self.mapsize

        if size is not None:
            mapsize += size

        elif self.growsize is not None:
            mapsize += self.growsize

        else:
            mapsize *= 2

        if self.maxsize is not None:
            mapsize = min(mapsize, self.maxsize)
            if mapsize == self.mapsize:
                raise s_exc.DbOutOfSpace(
                    mesg=f'DB at {self.path} is at specified max capacity of {self.maxsize} and is out of space')

        logger.warning('growing map size to: %d' % (mapsize,))

        self.lenv.set_mapsize(mapsize)
        self.mapsize = mapsize
        self._saveOptsFile()

        return self.mapsize

    def initdb(self, name, dupsort=False):
        with self._noCoXact():
            return self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)

    @contextlib.contextmanager
    def _noCoXact(self):
        if not self.readonly or self.txnrefcount:
            self._finiCoXact()
        yield None
        if not self.readonly or self.txnrefcount:
            self._initCoXact()

    def get(self, lkey, db=None):
        self._acqXactForReading()
        try:
            return self.xact.get(lkey, db=db)
        finally:
            self._relXactForReading()

    # non-scan ("atomic") interface.
    # def getByDup(self, lkey, db=None):
    # def getByPref(self, lkey, db=None):
    # def getByRange(self, lkey, db=None):

    def scanByDups(self, lkey, db=None):

        with Scan(self, db) as scan:

            if not scan.set_key(lkey):
                return

            yield from scan.iternext()

    def scanByPref(self, byts, db=None):

        with Scan(self, db) as scan:

            if not scan.set_range(byts):
                return

            size = len(byts)
            for lkey, lval in scan.iternext():

                if lkey[:size] != byts:
                    return

                yield lkey, lval

    def scanByRange(self, lmin, lmax=None, db=None):

        with Scan(self, db) as scan:

            if not scan.set_range(lmin):
                return

            size = len(lmax) if lmax is not None else None

            for lkey, lval in scan.iternext():

                if lmax is not None and lkey[:size] > lmax:
                    return

                yield lkey, lval

    # def keysByRange():
    # def valsByRange():

    def _initCoXact(self):
        try:
            self.xact = self.lenv.begin(write=not self.readonly)
        except lmdb.MapResizedError as e:
            # This is what happens when some *other* process increased the mapsize.  setting mapsize to 0 should
            # set my mapsize to whatever the other process raised it to
            self.lenv.set_mapsize(0)
            self.mapsize = self.lenv.info()['map_size']
            self.xact = self.lenv.begin(write=not self.readonly)
        self.dirty = False

    def _logXactOper(self, func, *args, **kwargs):
        self.xactops.append((func, args, kwargs))

    def _runXactOpers(self):
        # re-run transaction operations in the event of an abort.  Return the last operation's return value.
        retn = None
        for (f, a, k) in self.xactops:
            retn = f(*a, **k)
        return retn

    @contextlib.contextmanager
    def aborted(self):

        [scan.bump() for scan in self.scans]

        self.xact.abort()

        del self.xact

        yield

        self.xact = self.lenv.begin(write=not self.readonly)

        self.recovering = True
        self.last_retn = self._runXactOpers()
        self.recovering = False
        return self.last_retn

    def _handle_mapfull(self):
        with self.aborted():
            self._growMapSize()

        self.forcecommit()

        retn, self.last_retn = self.last_retn, None
        return retn

    def _xact_action(self, calling_func, xact_func, lkey, *args, db=None, **kwargs):
        if self.readonly:
            raise s_exc.IsReadOnly()

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(calling_func, lkey, *args, db=db, **kwargs)

            return xact_func(self.xact, lkey, *args, db=db, **kwargs)

        except lmdb.MapFullError as e:
            return self._handle_mapfull()

    def putmulti(self, kvpairs, dupdata=False, append=False, db=None):
        if self.readonly:
            raise s_exc.IsReadOnly()

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.putmulti, kvpairs, dupdata=dupdata, append=True, db=db)

            with self.xact.cursor(db=db) as curs:
                retn = curs.putmulti(kvpairs, dupdata=dupdata, append=append)

            return retn

        except lmdb.MapFullError as e:
            return self._handle_mapfull()

    def pop(self, lkey, db=None):
        return self._xact_action(self.pop, lmdb.Transaction.pop, lkey, db=db)

    def delete(self, lkey, val=None, db=None):
        return self._xact_action(self.delete, lmdb.Transaction.delete, lkey, val, db=db)

    def put(self, lkey, lval, dupdata=False, db=None):
        return self._xact_action(self.put, lmdb.Transaction.put, lkey, lval, dupdata=dupdata, db=db)

    def replace(self, lkey, lval, db=None):
        '''
        Like put, but returns the previous value if existed
        '''
        return self._xact_action(self.replace, lmdb.Transaction.replace, lkey, lval, db=db)

    @contextlib.contextmanager
    def synchold(self):
        '''
        Hold this across small/fast multi-writes to delay commit evaluation.
        This allows commit() boundaries to occur when the underlying db is coherent.

        Example:

            with dude.writer():
                dude.put(foo, bar)
                dude.put(baz, faz)

        '''
        self.holders += 1
        yield None
        self.holders -= 1

    def forcecommit(self):
        '''
        '''
        if not self.dirty:
            return False

        # ok... lets commit and re-open
        self._finiCoXact()
        self._initCoXact()
        return True

class Scan:
    '''
    A state-object used by Slab.  Not to be instantiated directly.
    '''
    def __init__(self, slab, db):

        self.slab = slab
        self.db = db

        self.atitem = None
        self.bumped = False
        self.iterfunc = None

    def __enter__(self):
        self.slab._acqXactForReading()
        self.curs = self.slab.xact.cursor(db=self.db)
        self.slab.scans.add(self)
        return self

    def __exit__(self, exc, cls, tb):
        self.bump()
        self.slab.scans.discard(self)
        self.slab._relXactForReading()

    def last_key(self):
        ''' Return the last key in the database.  Returns none if database is empty. '''
        if not self.curs.last():
            return None
        return self.curs.key()

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        # set_key for a scan is only logical if it's a dup scan
        self.iterfunc = functools.partial(lmdb.Cursor.iternext_dup, keys=True)
        self.genr = self.iterfunc(self.curs)
        self.atitem = next(self.genr)
        return True

    def set_range(self, lkey):

        if not self.curs.set_range(lkey):
            return False

        self.iterfunc = lmdb.Cursor.iternext
        self.genr = self.iterfunc(self.curs)
        self.atitem = next(self.genr)

        return True

    def iternext(self):

        try:

            while True:

                yield self.atitem

                if self.bumped:

                    if self.slab.isfini:
                        raise s_exc.IsFini()

                    self.bumped = False

                    self.curs = self.slab.xact.cursor(db=self.db)
                    self.curs.set_range_dup(*self.atitem)

                    self.genr = self.iterfunc(self.curs)

                    if self.curs.item() == self.atitem:
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration:
            return

    def bump(self):
        if not self.bumped:
            self.curs.close()
            self.bumped = True
