import os
import pathlib
import functools
import contextlib

import logging
logger = logging.getLogger(__name__)

import lmdb

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

COPY_CHUNKSIZE = 512
PROGRESS_PERIOD = COPY_CHUNKSIZE * 1024

# By default, double the map size each time we run out of space, until this amount, and then we only increase by that
MAX_DOUBLE_SIZE = 100 * s_const.gibibyte

class LmdbDatabase():
    def __init__(self, db, dupsort):
        self.db = db
        self.dupsort = dupsort

_DefaultDB = LmdbDatabase(None, False)

class Hist:
    '''
    A class for storing items in a slab by time.

    Each added item is inserted into the specified db within
    the slab using the current epoch-millis time stamp as the key.
    '''

    def __init__(self, slab, name):
        self.slab = slab
        self.db = slab.initdb(name, dupsort=True)

    def add(self, item):
        tick = s_common.now()
        lkey = tick.to_bytes(8, 'big')
        self.slab.put(lkey, s_msgpack.en(item), dupdata=True, db=self.db)

    def carve(self, tick, tock=None):

        lmax = None
        lmin = tick.to_bytes(8, 'big')
        if tock is not None:
            lmax = tock.to_bytes(8, 'big')

        for lkey, byts in self.slab.scanByRange(lmin, lmax=lmax, db=self.db):
            tick = int.from_bytes(lkey, 'big')
            yield tick, s_msgpack.un(byts)

class Offs:
    '''

    A helper for storing offset integers by iden. ( ported from synapse/lib/lmdb.py )

    As with all slab objects, this is meant for single-thread async loop use.
    '''
    def __init__(self, slab, name):
        self.slab = slab
        self.db = slab.initdb(name)

    def get(self, iden):

        buid = s_common.uhex(iden)
        byts = self.slab.get(buid, db=self.db)
        if byts is None:
            return 0

        return int.from_bytes(byts, byteorder='big')

    def set(self, iden, offs):
        buid = s_common.uhex(iden)
        byts = offs.to_bytes(length=8, byteorder='big')
        self.slab.put(buid, byts, db=self.db)

class SlabDict:
    '''
    A dictionary-like object which stores it's props in a slab via a prefix.

    It is assumed that only one SlabDict with a given prefix exists at any given
    time, but it is up to the caller to cache them.
    '''
    def __init__(self, slab, db=None, pref=b''):
        self.db = db
        self.slab = slab
        self.pref = pref
        self.info = self._getPrefProps(pref)

    def _getPrefProps(self, bidn):

        size = len(bidn)

        props = {}
        for lkey, lval in self.slab.scanByPref(bidn, db=self.db):
            name = lkey[size:].decode('utf8')
            props[name] = s_msgpack.un(lval)

        return props

    def items(self):
        '''
        Return a tuple of (prop, valu) tuples from the SlabDict.

        Returns:
            (((str, object), ...)): Tuple of (name, valu) tuples.
        '''
        return tuple(self.info.items())

    def get(self, name, defval=None):
        '''
        Get a name from the SlabDict.

        Args:
            name (str): The key name.
            defval (obj): The default value to return.

        Returns:
            (obj): The return value, or None.
        '''
        return self.info.get(name, defval)

    def set(self, name, valu):
        '''
        Set a name in the SlabDict.

        Args:
            name (str): The key name.
            valu (obj): A msgpack compatible value.

        Returns:
            None
        '''
        byts = s_msgpack.en(valu)
        lkey = self.pref + name.encode('utf8')
        self.slab.put(lkey, byts, db=self.db)
        self.info[name] = valu

    def pop(self, name, defval=None):
        '''
        Pop a name from the SlabDict.

        Args:
            name (str): The name to remove.
            defval (obj): The default value to return if the name is not present.

        Returns:
            object: The object stored in the SlabDict, or defval if the object was not present.
        '''
        valu = self.info.pop(name, defval)
        lkey = self.pref + name.encode('utf8')
        self.slab.pop(lkey, db=self.db)
        return valu

class GuidStor:

    def __init__(self, slab, name):

        self.slab = slab
        self.name = name

        self.db = self.slab.initdb(name)

    def gen(self, iden):
        bidn = s_common.uhex(iden)
        return SlabDict(self.slab, db=self.db, pref=bidn)

def _ispo2(i):
    return not (i & (i - 1)) and i

def _florpo2(i):
    '''
    Return largest power of 2 equal to or less than i
    '''
    if _ispo2(i):
        return i
    return 1 << (i.bit_length() - 1)

def _ceilpo2(i):
    '''
    Return smallest power of 2 equal to or greater than i
    '''
    if _ispo2(i):
        return i
    return 1 << i.bit_length()

def _roundup(i, multiple):
    return ((i + multiple - 1) // multiple) * multiple

def _mapsizeround(size):
    cutoff = _florpo2(MAX_DOUBLE_SIZE)

    if size < cutoff:
        return _ceilpo2(size)

    if size == cutoff:  # We're already the largest power of 2
        return size

    return _roundup(size, MAX_DOUBLE_SIZE)

class Slab(s_base.Base):
    '''
    A "monolithic" LMDB instance for use in a asyncio loop thread.
    '''
    COMMIT_PERIOD = 1.0  # time between commits

    async def __anit__(self, path, **kwargs):

        await s_base.Base.__anit__(self)

        kwargs.setdefault('map_size', s_const.gibibyte)

        opts = kwargs

        self.path = pathlib.Path(path)

        self.optspath = self.path.with_suffix('.opts.yaml')

        if self.optspath.exists():
            opts.update(s_common.yamlload(self.optspath))

        initial_mapsize = opts.get('map_size')
        if initial_mapsize is None:
            raise s_exc.BadArg('Slab requires map_size')

        mdbpath = self.path / 'data.mdb'
        if mdbpath.exists():
            mapsize = max(initial_mapsize, os.path.getsize(mdbpath))
        else:
            mapsize = initial_mapsize

        # save the transaction deltas in case of error...
        self.xactops = []
        self.recovering = False

        opts.setdefault('max_dbs', 128)
        opts.setdefault('writemap', True)

        self.maxsize = opts.pop('maxsize', None)
        self.growsize = opts.pop('growsize', None)

        self.readonly = opts.get('readonly', False)

        self.mapsize = _mapsizeround(mapsize)
        if self.maxsize is not None:
            self.mapsize = min(self.mapsize, self.maxsize)

        self._saveOptsFile()

        self.lenv = lmdb.open(path, **opts)

        self.scans = set()

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
        opts = {}
        if self.growsize is not None:
            opts['growsize'] = self.growsize
        if self.maxsize is not None:
            opts['maxsize'] = self.maxsize
        s_common.yamlmod(opts, self.optspath)

    async def _runSyncLoop(self):
        while not self.isfini:
            await self.waitfini(timeout=self.COMMIT_PERIOD)
            if self.isfini:
                # There's no reason to forcecommit on fini, because there's a separate handler to already do that
                break

            try:
                self.forcecommit()

            except lmdb.MapFullError:
                self._handle_mapfull()
                # There's no need to re-try self.forcecommit as _growMapSize does it

    async def _onCoFini(self):
        assert s_glob.iAmLoop()
        while True:
            try:
                self._finiCoXact()
            except lmdb.MapFullError:
                self._handle_mapfull()
                continue
            break
        self.lenv.close()
        del self.lenv

    def _finiCoXact(self):
        '''
        Note:
            This method may raise a MapFullError
        '''

        assert s_glob.iAmLoop()

        [scan.bump() for scan in self.scans]

        # Readonly or self.xact has already been closed
        if self.xact is None:
            return

        self.xact.commit()

        self.xactops.clear()

        del self.xact
        self.xact = None

    def _growMapSize(self, size=None):
        mapsize = self.mapsize

        if size is not None:
            mapsize += size

        elif self.growsize is not None:
            mapsize += self.growsize

        else:
            mapsize = _mapsizeround(mapsize + 1)

        if self.maxsize is not None:
            mapsize = min(mapsize, self.maxsize)
            if mapsize == self.mapsize:
                raise s_exc.DbOutOfSpace(
                    mesg=f'DB at {self.path} is at specified max capacity of {self.maxsize} and is out of space')

        logger.warning('lmdbslab %s growing map size to: %d MiB', self.path, mapsize // s_const.mebibyte)

        self.lenv.set_mapsize(mapsize)
        self.mapsize = mapsize

        return self.mapsize

    def initdb(self, name, dupsort=False):
        while True:
            try:
                db = self.lenv.open_db(name.encode('utf8'), txn=self.xact, dupsort=dupsort)
                self.dirty = True
                self.forcecommit()
                return LmdbDatabase(db, dupsort)
            except lmdb.MapFullError:
                self._handle_mapfull()

    def dropdb(self, name):
        '''
        Deletes an **entire database** (i.e. a table), losing all data.
        '''
        if self.readonly:
            raise s_exc.IsReadOnly()

        while True:
            try:
                if not self.dbexists(name):
                    return
                db = self.initdb(name)
                self.dirty = True
                self.xact.drop(db.db, delete=True)
                self.forcecommit()
                return

            except lmdb.MapFullError:
                self._handle_mapfull()

    def dbexists(self, name):
        '''
        The DB exists already if there's a key in the default DB with the name of the database
        '''
        valu = self.get(name.encode())
        return valu is not None

    def get(self, lkey, db=_DefaultDB):
        self._acqXactForReading()
        try:
            return self.xact.get(lkey, db=db.db)
        finally:
            self._relXactForReading()

    def last(self, db=_DefaultDB):
        '''
        Return the last key/value pair from the given db.
        '''
        self._acqXactForReading()
        try:
            with self.xact.cursor(db=db.db) as curs:
                if not curs.last():
                    return None
                return curs.key(), curs.value()
        finally:
            self._relXactForReading()

    def stat(self, db=_DefaultDB):
        self._acqXactForReading()
        try:
            return self.xact.stat(db=db.db)
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

    def scanByFull(self, db=None):

        with Scan(self, db) as scan:

            if not scan.first():
                return

            for lkey, lval in scan.iternext():
                yield lkey, lval

    # def keysByRange():
    # def valsByRange():

    def _initCoXact(self):
        try:
            self.xact = self.lenv.begin(write=not self.readonly)
        except lmdb.MapResizedError:
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

    def _handle_mapfull(self):
        [scan.bump() for scan in self.scans]

        while True:
            try:
                self.xact.abort()

                del self.xact
                self.xact = None  # Note: it is possible for us to be fini'd in _growMapSize

                self._growMapSize()

                self.xact = self.lenv.begin(write=not self.readonly)

                self.recovering = True
                self.last_retn = self._runXactOpers()
                self.recovering = False

                self.forcecommit()

            except lmdb.MapFullError:
                continue

            break

        retn, self.last_retn = self.last_retn, None
        return retn

    def _xact_action(self, calling_func, xact_func, lkey, *args, db=None, **kwargs):
        if self.readonly:
            raise s_exc.IsReadOnly()

        if db is None:
            db = _DefaultDB

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(calling_func, lkey, *args, db=db, **kwargs)

            return xact_func(self.xact, lkey, *args, db=db.db, **kwargs)

        except lmdb.MapFullError:
            return self._handle_mapfull()

    def putmulti(self, kvpairs, dupdata=False, append=False, db=_DefaultDB):
        '''
        Returns:
            Tuple of number of items consumed, number of items added
        '''
        if self.readonly:
            raise s_exc.IsReadOnly()

        # Log playback isn't compatible with generators
        if not isinstance(kvpairs, list):
            kvpairs = list(kvpairs)

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.putmulti, kvpairs, dupdata=dupdata, append=append, db=db)

            with self.xact.cursor(db=db.db) as curs:
                return curs.putmulti(kvpairs, dupdata=dupdata, append=append)

        except lmdb.MapFullError:
            return self._handle_mapfull()

    def copydb(self, sourcedb, destslab, destdbname=None, progresscb=None):
        '''
        Copy an entire database in this slab to a new database in potentially another slab.

        Args:
            sourcedb (LmdbDatabase): which database in this slab to copy rows from
            destslab (LmdbSlab): which slab to copy rows to
            destdbname (str): the name of the database to copy rows to in destslab
            progresscb (Callable[int]):  if not None, this function will be periodically called with the number of rows
                                         completed

        Returns:
            (int): the number of rows copied

        Note:
            If any rows already exist in the target database, this method returns an error.  This means that one cannot
            use destdbname=None unless there are no explicit databases in the destination slab.
        '''
        destdb = destslab.initdb(destdbname, sourcedb.dupsort)

        statdict = destslab.stat(db=destdb)
        if statdict['entries'] > 0:
            raise s_exc.DataAlreadyExists()

        rowcount = 0

        for chunk in s_common.chunks(self.scanByFull(db=sourcedb), COPY_CHUNKSIZE):
            ccount, acount = destslab.putmulti(chunk, dupdata=True, append=True, db=destdb)
            if ccount != len(chunk) or acount != len(chunk):
                raise s_exc.BadCoreStore(mesg='Unexpected number of values written')  # pragma: no cover

            rowcount += len(chunk)
            if progresscb is not None and 0 == (rowcount % PROGRESS_PERIOD):
                progresscb(rowcount)

        return rowcount

    def pop(self, lkey, db=None):
        return self._xact_action(self.pop, lmdb.Transaction.pop, lkey, db=db)

    def delete(self, lkey, val=None, db=None):
        return self._xact_action(self.delete, lmdb.Transaction.delete, lkey, val, db=db)

    def put(self, lkey, lval, dupdata=False, overwrite=True, db=None):
        return self._xact_action(self.put, lmdb.Transaction.put, lkey, lval, dupdata=dupdata, overwrite=overwrite,
                                 db=db)

    def replace(self, lkey, lval, db=None):
        '''
        Like put, but returns the previous value if existed
        '''
        return self._xact_action(self.replace, lmdb.Transaction.replace, lkey, lval, db=db)

    def forcecommit(self):
        '''
        Note:
            This method may raise a MapFullError
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
        if db is None:
            db = _DefaultDB
        self.slab = slab
        self.db = db.db
        self.dupsort = db.dupsort

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
        '''
        Return the last key in the database.  Returns none if database is empty.
        '''
        if not self.curs.last():
            return None

        return self.curs.key()

    def first(self):

        if not self.curs.first():
            return False

        if self.dupsort:
            self.iterfunc = functools.partial(lmdb.Cursor.iternext_dup, keys=True)
        else:
            self.iterfunc = lmdb.Cursor.iternext

        self.genr = self.curs.iternext()
        self.atitem = next(self.genr)
        return True

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        # set_key for a scan is only logical if it's a dup scan
        if self.dupsort:
            self.iterfunc = functools.partial(lmdb.Cursor.iternext_dup, keys=True)
        else:
            self.iterfunc = lmdb.Cursor.iternext

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
                    if self.dupsort:
                        self.curs.set_range_dup(*self.atitem)
                    else:
                        self.curs.set_range(self.atitem[0])

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
