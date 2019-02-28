import os
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

class _LmdbDatabase():
    def __init__(self, db, dupsort):
        self.db = db
        self.dupsort = dupsort

_DefaultDB = _LmdbDatabase(None, False)

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

class Slab(s_base.Base):
    '''
    A "monolithic" LMDB instance for use in a asyncio loop thread.
    '''
    COMMIT_PERIOD = 1.0  # time between commits

    async def __anit__(self, path, **kwargs):

        await s_base.Base.__anit__(self)

        kwargs.setdefault('map_size', s_const.gibibyte)

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
            self.forcecommit()

    async def _onCoFini(self):
        assert s_glob.iAmLoop()
        self._finiCoXact()
        self.lenv.close()
        del self.lenv

    def _finiCoXact(self):

        assert s_glob.iAmLoop()

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
            db = self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)

        return _LmdbDatabase(db, dupsort)

    @contextlib.contextmanager
    def _noCoXact(self):
        if not self.readonly or self.txnrefcount:
            self._finiCoXact()
        yield None
        if not self.readonly or self.txnrefcount:
            self._initCoXact()

    def get(self, lkey, db=_DefaultDB):
        self._acqXactForReading()
        try:
            return self.xact.get(lkey, db=db.db)
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

    @contextlib.contextmanager
    def aborted(self):

        [scan.bump() for scan in self.scans]

        self.xact.abort()

        del self.xact
        self.xact = None  # Note: it is possible for us to be fini'd in the following yield

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
                retn = curs.putmulti(kvpairs, dupdata=dupdata, append=append)

            return retn

        except lmdb.MapFullError:
            return self._handle_mapfull()

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
