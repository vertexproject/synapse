import os
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

    async def __anit__(self, path, **opts):
        await s_base.Base.__anit__(self)

        self.path = path
        self.optspath = os.path.join(path, 'opts.json')

        if os.path.isfile(self.optspath):
            opts.update(s_common.jsload(self.optspath))

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

        self._initCoXact()

        self.onfini(self._onCoFini)
        self.schedCoro(self._runSyncLoop())

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

        self.xact.commit()

        self.xactops.clear()

        del self.xact

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
        self._finiCoXact()
        yield None
        self._initCoXact()

    def get(self, lkey, db=None):
        return self.xact.get(lkey, db=db)

    # non-scan ("atomic") interface.
    # def getByDup(self, lkey, db=None):
    # def getByPref(self, lkey, db=None):
    # def getByRange(self, lkey, db=None):

    def scanByDups(self, lkey, db=None):

        with Scan(self, db) as scan:

            if not scan.set_key(lkey):
                return

            yield from scan.iternext_dup()

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
        self.xact = self.lenv.begin(write=not self.readonly)
        self.dirty = False

    def _logXactOper(self, func, *args, **kwargs):
        self.xactops.append((func, args, kwargs))

    def _runXactOpers(self):
        # re-run transaction operations in the event of an abort
        [f(*a, **k) for (f, a, k) in self.xactops]

    @contextlib.contextmanager
    def aborted(self):

        [scan.bump() for scan in self.scans]

        self.xact.abort()

        del self.xact

        yield

        self.xact = self.lenv.begin(write=not self.readonly)

        self.recovering = True
        self._runXactOpers()
        self.recovering = False

    def _handle_mapfull(self):
        with self.aborted():
            self._growMapSize()

        self.forcecommit()

    # FIXME:  refactor delete/put/replace/pop common code
    def pop(self, lkey, db=None):

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.pop, lkey, db=db)

            retn = self.xact.pop(lkey, db=db)

            return retn

        except lmdb.MapFullError as e:
            self._handle_mapfull()

    def delete(self, lkey, val=None, db=None):

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.delete, lkey, val, db=db)

            self.xact.delete(lkey, val, db=db)

            return

        except lmdb.MapFullError as e:
            self._handle_mapfull()

    def put(self, lkey, lval, dupdata=False, db=None):

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.put, lkey, lval, dupdata=dupdata, db=db)

            self.xact.put(lkey, lval, dupdata=dupdata, db=db)

            return

        except lmdb.MapFullError as e:
            self._handle_mapfull()

    def replace(self, lkey, lval, db=None):
        '''
        Like put, but returns the previous value if existed
        '''

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.replace, lkey, lval, db=db)

            retn = self.xact.replace(lkey, lval, db=db)

            return retn

        except lmdb.MapFullError as e:
            self._handle_mapfull()

    def putmulti(self, kvpairs, dupdata=False, append=False, db=None):

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.putmulti, kvpairs, dupdata=dupdata, append=True, db=db)

            with self.xact.cursor(db=db) as curs:
                curs.putmulti(kvpairs, dupdata=dupdata, append=append)

            return

        except lmdb.MapFullError as e:
            self._handle_mapfull()

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

        self.curs = self.slab.xact.cursor(db=db)

        self.atitem = None
        self.bumped = False

    def __enter__(self):
        self.slab.scans.add(self)
        return self

    def __exit__(self, exc, cls, tb):

        self.bump()

        self.slab.scans.discard(self)

    def last_key(self):
        ''' Return the last key in the database.  Returns none if database is empty. '''
        if not self.curs.last():
            return None
        return self.curs.key()

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        # set_key for a scan is only logical if it's a dup scan
        self.genr = self.curs.iternext_dup(keys=True)
        self.atitem = next(self.genr)
        return True

    def set_range(self, lkey):

        if not self.curs.set_range(lkey):
            return False

        self.genr = self.curs.iternext()
        self.atitem = next(self.genr)

        return True

    def iternext(self):

        try:

            while True:

                yield self.atitem

                if self.bumped:

                    if self.slab.isfini:
                        raise s_exc.IsFini()

                    self.curs = self.slab.xact.cursor(db=self.db)
                    self.curs.set_range(self.atitem[0])

                    self.genr = self.curs.iternext()

                    if self.curs.item() == self.atitem:
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration as e:
            return

    def iternext_dup(self):

        try:

            while True:

                yield self.atitem

                if self.bumped:

                    if self.slab.isfini:
                        raise s_exc.IsFini()

                    self.curs = self.slab.xact.cursor(db=self.db)
                    self.curs.set_range_dup(*self.atitem)

                    self.genr = self.curs.iternext_dup(keys=True)

                    if self.curs.item() == self.atitem:
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration as e:
            return

    def bump(self):
        if not self.bumped:
            self.curs.close()
            self.bumped = True
