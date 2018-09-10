import os
import sys
import struct
import logging
import contextlib

logger = logging.getLogger(__name__)

import lmdb

import xxhash  # type: ignore

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

STOR_FLAG_NOINDEX = 0x0001      # there is no byprop index for this prop
STOR_FLAG_MULTIVAL = 0x0002     # this is a multi-value prop
STOR_FLAG_DEFVAL = 0x0004       # Only set this if it doesn't exist

if sys.platform == 'linux':
    DEFAULT_MAP_SIZE = s_const.tebibyte
    DEFAULT_SMALL_MAP_SIZE = s_const.gibibyte
else:
    # For non-Linux system, use a smaller DB since one can't guarantee sparse file support
    DEFAULT_MAP_SIZE = s_const.gibibyte
    DEFAULT_SMALL_MAP_SIZE = s_const.mebibyte * 100

# String vals of this size or larger will be truncated and hashed in index.  What this means is
# that comparison on large string vals require retrieving the row from the main table
LARGE_STRING_SIZE = 128

# Smallest and largest values for an integer value.  Matches sqlite3
MAX_INT_VAL = 2 ** 63 - 1
MIN_INT_VAL = -1 * (2 ** 63)

# Precompiled struct of a big-endian 64-bit int
_IntStruct = struct.Struct('>Q')

class Seqn:
    '''
    An append optimized sequence of byte blobs.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the sequence.
    '''
    def __init__(self, lenv, name):

        self.lenv = lenv
        self.db = lenv.open_db(name)

        with lenv.begin() as xact:
            self.indx = self.nextindx(xact)

    def save(self, xact, items):
        '''
        Save a series of items to a sequence.

        Args:
            xact (lmdb.Transaction): An LMDB write transaction.
            items (tuple): The series of items to save into the sequence.

        Returns:
            None
        '''
        rows = []
        indx = self.indx

        for item in items:

            byts = s_msgpack.en(item)

            lkey = struct.pack('>Q', indx)
            indx += 1

            rows.append((lkey, byts))

        with xact.cursor(db=self.db) as curs:
            curs.putmulti(rows, append=True)

        self.indx = indx

    def index(self):
        '''
        Return the current index to be used
        '''
        return self.indx

    def nextindx(self, xact):
        '''
        Determine the next insert offset according to storage.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.

        Returns:
            int: The next insert offset.
        '''
        indx = 0
        with xact.cursor(db=self.db) as curs:
            if curs.last():
                indx = struct.unpack('>Q', curs.key())[0] + 1
        return indx

    def iter(self, xact, offs):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        lkey = struct.pack('>Q', offs)
        with xact.cursor(db=self.db) as curs:

            if not curs.set_key(lkey):
                return

            for lkey, lval in curs.iternext():
                indx = struct.unpack('>Q', lkey)[0]
                valu = s_msgpack.un(lval)
                yield indx, valu

    def slice(self, xact, offs, size):

        imax = size - 1

        for i, item in enumerate(self.iter(xact, offs)):

            yield item

            if i == imax:
                break

class Offs:

    def __init__(self, lenv, db):
        self.db = db
        self.lenv = lenv

    def get(self, iden):
        with self.lenv.begin() as xact:
            return self.xget(xact, iden)

    def set(self, iden, offs):
        with self.lenv.begin(write=True) as xact:
            return self.xset(xact, iden, offs)

    def xget(self, xact, iden):

        buid = s_common.uhex(iden)

        byts = xact.get(buid, db=self.db)
        if byts is None:
            return 0

        return int.from_bytes(byts, byteorder='big')

    def xset(self, xact, iden, offs):
        buid = s_common.uhex(iden)
        byts = offs.to_bytes(length=8, byteorder='big')
        xact.put(buid, byts, db=self.db)

class Metrics:
    '''
    A helper for recording metrics about an Environment.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the metrics instance.
    '''
    def __init__(self, lenv, name=b'metrics'):

        self.lenv = lenv

        self._db_history = lenv.open_db(name + b':history')
        self._db_current = lenv.open_db(name + b':current')

        self.info = {}

        with lenv.begin() as xact:

            for lkey, lval in xact.cursor(db=self._db_current):

                name = lkey.decode('utf8')
                valu = struct.unpack('>Q', lval)[0]

                self.info[name] = valu

            self.indx = 0

            curs = xact.cursor(db=self._db_history)
            if curs.last():
                self.indx = struct.unpack('>Q', curs.key())[0] + 1

    def inc(self, xact, prop, step=1):
        '''
        Increment the value of a global metric.

        Args:
            xact (lmdb.Transaction): An LMDB write transaction.
            prop (str): The property to increment.
            step (int): The value by which to increment the property.

        Returns:
            None
        '''
        valu = self.info.get(prop, 0)
        valu += step

        self.info[prop] = valu

        penc = prop.encode('utf8')
        pval = struct.pack('>Q', valu)

        xact.put(penc, pval, db=self._db_current)

    def stat(self):
        '''
        Return the metrics info.

        Returns:
            dict: The dictionary of recorded metrics.
        '''
        return self.info

    def iter(self, xact, offs):
        '''
        Iterate over metrics items from a given offset.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            offs (int): The offset to begin iterating from.

        Yields:
            ((indx, object)): The index and sample.
        '''

        lkey = struct.pack('>Q', offs)

        with xact.cursor(db=self._db_history) as curs:

            if not curs.set_key(lkey):
                return

            for lkey, lval in curs.iternext():

                indx = struct.unpack('>Q', lkey)[0]
                sample = s_msgpack.un(lval)

                yield indx, sample

    def record(self, xact, info):
        '''
        Record metrics info.

        Args:
            xact (Transaction): An LMDB write transaction.
            info (dict): A dictionary of sample info to save.

        Returns:
            None
        '''
        indx = struct.pack('>Q', self.indx)
        self.indx += 1
        sample = s_msgpack.en(info)
        xact.put(indx, sample, db=self._db_history, append=True)

class PropSetr:
    '''
    A helper for setting properties. Most to cache cursors.

    Args:
        ptso (PropStor): The PropStore.
        xact (lmdb.Transaction): An LMDB write transaction.
    '''
    def __init__(self, psto, xact):

        self.xact = xact
        self.psto = psto

        self.purs = xact.cursor(db=psto.props)
        self.burs = xact.cursor(db=psto.byprop)

    #def rem(self, buid):
    #def addtag(self, buid, tag, times):
    #def deltag(self, buid, tag):

    def has(self, penc, byts):
        '''
        Check for the existence of an encoded prop, valu pair in a PropStor.

        Args:
            penc (bytes): The encoded property name.
            byts (bytes): The valu bytes.

        Returns:
            bool: True if the pair exists, False otherwise.
        '''
        return self.burs.set_key(penc + b'\x00' + byts)

    def set(self, buid, penc, lval, flags=0):
        '''
        Set a row in a PropStor.

        Args:
            buid (bytes): The binary GUID like sequence of 32 bytes.
            penc (bytes): The encoded property name.
            lval (bytes): The valu bytes.

        Returns:
            bool: True if the row was set, False otherwise.
        '''
        pkey = buid + penc

        noindex = flags & STOR_FLAG_NOINDEX
        multival = flags & STOR_FLAG_MULTIVAL

        if self.purs.set_key(pkey):

            # At a minimum, we have the key...
            if flags & STOR_FLAG_DEFVAL:
                return False

            # if this is a multi-val, iter to check for valu
            if multival:

                # if a multival prop=valu exists, skip adding
                for mval in self.purs.iternext_dup():
                    if mval == lval:
                        return False

            else:

                # if it's exactly what we want, skip...
                oldb = self.purs.value()
                if oldb == lval:
                    return False

                okey = penc + b'\x00' + oldb
                if self.burs.set_key(okey):
                    self.burs.delete()

        # we are now free and clear to set and index
        self.purs.put(pkey, lval, dupdata=multival)
        if not noindex:
            self.burs.put(penc + b'\x00' + lval, buid)

        return True

    def put(self, items):
        '''
        Put a list of items into the PropStor.

        Args:
            items (list): A list of (buid, ((penv, lval, flags),...)) tuples to put.

        Yields:
            ((int, (bytes, list))): Yields the item number, buid and list of changed props.
        '''
        for i, (buid, props) in enumerate(items):

            edits = []

            for penc, lval, flags in props:

                if self.set(buid, penc, lval, flags=flags):
                    edits.append((penc, lval, flags))

            if edits:
                yield (i, (buid, edits))

class PropStor:
    '''
    A property store.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of property store.
    '''
    def __init__(self, lenv, name=b'stor'):

        self.lenv = lenv
        self.props = self.lenv.open_db(name + b':props', dupsort=True)      # <buid><pkey>=<pval>
        self.byprop = self.lenv.open_db(name + b':byprop', dupsort=True)    # <pkey>00<pval> = <buid>

    def getPropSetr(self, xact):
        '''
        Return a new PropSetr helper.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.

        Returns:
            PropSetr: The property setter helper.
        '''
        return PropSetr(self, xact)

    def has(self, xact, penc, byts):
        '''
        Check for the existence of an encoded prop, valu pair in a PropStor.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            penc (bytes): The encoded property name.
            byts (bytes): The valu bytes.

        Returns:
            bool: True if the pair exists, False otherwise.
        '''
        with xact.cursor(db=self.byprop) as burs:
            return burs.set_key(penc + b'\x00' + byts)

    def pref(self, xact, penc, byts):
        '''
        Perform a prefix search and yield (buid, penc, pval) rows.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            penc (bytes): The encoded property name.
            byts (bytes): The valu bytes.

        Yields:
            ((bytes, bytes, bytes)): A buid, penc, pval row.
        '''
        bkey = penc + b'\x00' + byts

        blen = len(bkey)
        with xact.cursor(db=self.byprop) as burs:

            if not burs.set_range(bkey):
                return

            for lkey, buid in burs.iternext():

                if lkey[:blen] != bkey:
                    return

                renc, rval = lkey.split(b'\x00', 1)
                yield (buid, renc, rval)

    def range(self, xact, penc, bval, nval):
        '''
        Perform a range search and yield (buid, penc, pval) rows.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            penc (bytes): The encoded property name.
            bval (bytes): The lower bound to search.
            nval (bytes): The upper bound to search.

        Yields:
            ((bytes, bytes, bytes)): A buid, penc, pval row.
        '''
        bkey = penc + b'\x00' + bval
        nkey = penc + b'\x00' + nval

        blen = len(bkey)
        with xact.cursor(db=self.byprop) as burs:

            if not burs.set_range(bkey):
                return

            for lkey, buid in burs.iternext():

                if lkey >= nkey:
                    break

                renc, rval = lkey.split(b'\x00', 1)
                yield (buid, renc, rval)

    def recs(self, xact, rows):
        '''
        Yields full (buid, (props..)) records from rows.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            rows (list): A list of ((buid, penc, pval)) rows.

        Yields:
            ((bytes, list)): A set of (buid, (props...)) for the rows.
        '''
        with xact.cursor(db=self.props) as purs:

            for buid, penc, pval in rows:

                # props: <buid><prop>=<valu>
                if not purs.set_range(buid):
                    # yield empty results for iterator alignment..
                    yield (buid, ())
                    continue

                props = []

                for lkey, lval in purs.iternext():
                    props.append((lkey[32:], lval))

                yield (buid, props)

    def eq(self, xact, penc, pval):
        '''
        Yield (buid, pkey, pval) rows by prop=valu.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            penc (bytes): The encoded property name.
            pval (bytes): The encoded property value.

        Yields:
            ((bytes, bytes, bytes)): A buid, penc, pval row.
        '''
        lkey = penc + b'\x00' + pval
        with xact.cursor(db=self.byprop) as burs:
            if not burs.set_key(lkey):
                return

            for buid in burs.iternext_dup():
                yield buid, penc, pval


# Prefix to indicate that a v is an integer
_INT_VAL_MARKER = 0

# Prefix to indicate than a v is a string
_STR_VAL_MARKER = b'\x01'

# Precompiled struct of a byte then a big-endian 64-bit int
_LeMarkerUintST = struct.Struct('>BQ')

def encodeValAsKey(v, isprefix=False):
    '''
    Encode a value (int or str) as used in a key into bytes so that prefix searches on strings and range searches
    on ints work.  The first encoded byte indicates

    Integers are 8-byte little endian - MIN_INT_VAL (this ensures that all negative values sort before all nonnegative
    values)

    Strings are UTF-8 encoded NULL-terminated unless isprefix is True.  If string length > LARGE_STRING_SIZE, just the
    first 128 bytes are written and a non-cryptographically hash is appended, and isprefix is disregarded.

    Note that this scheme prevents interleaving of value types: all string encodings compare larger than all integer
    encodings.

    Args:
        v (Union[str, int]: the value.
        isprefix: whether to interpret v as a prefix.  If true, strings will not be appended with a NULL.
    '''
    if isinstance(v, int):
        return _LeMarkerUintST.pack(_INT_VAL_MARKER, v - MIN_INT_VAL)
    else:
        v_enc = v.encode('utf8', errors='surrogatepass')
        if len(v_enc) >= LARGE_STRING_SIZE:
            if isprefix:
                return _STR_VAL_MARKER + v_enc[:LARGE_STRING_SIZE] + b'\x00'
            else:
                return _STR_VAL_MARKER + v_enc[:LARGE_STRING_SIZE] + b'\x00' + xxhash.xxh64(v_enc).digest()

        elif isprefix:
            return _STR_VAL_MARKER + v_enc
        else:
            return _STR_VAL_MARKER + v_enc + b'\x00'

class Slab(s_coro.Fini):
    '''
    A "monolithic" LMDB instance for use in a asyncio loop thread.
    '''

    def __init__(self, path, **opts):

        s_coro.Fini.__init__(self)

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

        # if growsize is not set, we double...
        self.maxsize = opts.pop('maxsize', None)
        self.growsize = opts.pop('growsize', None)

        opts.setdefault('max_dbs', 128)
        opts.setdefault('writemap', True)

        self.lenv = lmdb.open(path, **opts)

        self.scans = set()

        # there is only ever 1 xact...
        self.tick = s_common.now()

        self.dirty = False
        self.holders = 0

        self.xact = self.lenv.begin(write=True)

        self.onfini(self._onCoFini)

        self._runSyncLoop()

    def _saveOptsFile(self):
        opts = {'map_size': self.mapsize, 'growsize': self.growsize}
        s_common.jssave(opts, self.optspath)

    def _runSyncLoop(self):

        if self.isfini:
            return

        self.commit()

        s_glob.plex.loop.call_later(1, self._runSyncLoop)

    async def _onCoFini(self):
        self._finiCoXact()
        self.lenv.close()

    def _finiCoXact(self):

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

        if size is not None:
            self.mapsize += size

        elif self.growsize is not None:
            self.mapsize += self.growsize

        else:
            self.mapsize *= 2

        logger.warning('growing map size to: %d' % (self.mapsize,))

        self.lenv.set_mapsize(self.mapsize)
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

    def _bumpXactScans(self):
        [scan.bump() for scan in self.scans]

    def get(self, lkey, db=None):
        return self.xact.get(lkey, db=db)

    # non-scan ("atomic") interface.
    #def getByDup(self, lkey, db=None):
    #def getByPref(self, lkey, db=None):
    #def getByRange(self, lkey, db=None):

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

    #def keysByRange():
    #def valsByRange():

    def _initCoXact(self):
        self.xact = self.lenv.begin(write=True)
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

        self.xact = self.lenv.begin(write=True)

        self.recovering = True
        self._runXactOpers()
        self.recovering = False

    # FIXME:  refactor delete/put/replace/pop common code
    def pop(self, lkey, db=None):

        try:

            # if this is the first write for this xact, reset tick.
            if not self.dirty:
                self.tick = s_common.now()
                self.dirty = True

            if not self.recovering:
                self._logXactOper(self.pop, lkey, db=db)

            retn = self.xact.pop(lkey, db=db)

            # give the commit a chance...
            if not self.holders:
                self.commit()

            return retn

        except lmdb.MapFullError as e:

            with self.aborted():
                self._growMapSize()

            self.commit(force=True)

    def delete(self, lkey, dupdata=False, db=None):

        try:

            # if this is the first write for this xact, reset tick.
            if not self.dirty:
                self.tick = s_common.now()
                self.dirty = True

            if not self.recovering:
                self._logXactOper(self.delete, lkey, dupdata=dupdata, db=db)

            self.xact.delete(lkey, dupdata=dupdata, db=db)

            # give the commit a chance...
            if not self.holders:
                self.commit()

            return

        except lmdb.MapFullError as e:

            with self.aborted():
                self._growMapSize()

            self.commit(force=True)

    def put(self, lkey, lval, dupdata=False, db=None):

        try:

            # if this is the first write for this xact, reset tick.
            if not self.dirty:
                self.tick = s_common.now()
                self.dirty = True

            if not self.recovering:
                self._logXactOper(self.put, lkey, lval, dupdata=dupdata, db=db)

            self.xact.put(lkey, lval, dupdata=dupdata, db=db)

            # give the commit a chance...
            if not self.holders:
                self.commit()

            return

        except lmdb.MapFullError as e:

            with self.aborted():
                self._growMapSize()

            self.commit(force=True)

    def replace(self, lkey, lval, db=None):
        '''
        Like put, but returns the previous value if existed
        '''

        try:

            # if this is the first write for this xact, reset tick.
            if not self.dirty:
                self.tick = s_common.now()
                self.dirty = True

            if not self.recovering:
                self._logXactOper(self.replace, lkey, lval, db=db)

            retn = self.xact.put(lkey, lval, db=db)

            # give the commit a chance...
            if not self.holders:
                self.commit()

            return retn

        except lmdb.MapFullError as e:

            with self.aborted():
                self._growMapSize()

            self.commit(force=True)

    def putmulti(self, kvpairs, dupdata=False, append=False, db=None):

        try:

            # if this is the first write for this xact, reset tick.
            if not self.dirty:
                self.tick = s_common.now()
                self.dirty = True

            if not self.recovering:
                self._logXactOper(self.putmulti, kvpairs, dupdata=dupdata, append=True, db=db)

            with self.xact.cursor(db=db) as curs:
                curs.putmulti(kvpairs, dupdata=dupdata, append=append)

            # give the commit a chance...
            if not self.holders:
                self.commit()

            return

        except lmdb.MapFullError as e:

            with self.aborted():
                self._growMapSize()

            self.commit(force=True)

    @contextlib.contextmanager
    def synchold(self):
        '''
        Hold this across small/fast multi-writes to delay commit evaluation.
        This allows commit() boundaries to occur when the underlying db is coherent.

        Example:

            with SHIT.writer():
                shit.put(foo, bar)
                shit.put(baz, faz)

        '''
        self.holders += 1
        yield None
        self.holders -= 1

        if self.holders == 0:
            self.commit()

    def commit(self, force=False):
        '''
        '''
        if not self.dirty:
            return False

        if not force:

            if self.holders:
                return False

            # these are in millis...
            took = s_common.now() - self.tick

            # commit once per second... for now.
            if took < 1000:
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

        self.curs = self.slab.xact.cursor(db=db)

        self.atitem = None
        self.bumped = False

        #self.within = False

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
        self.genr = self.curs.iternext_dup()
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

                    self.genr = self.curs.iternext_dup()

                    if self.curs.item() == self.atitem:
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration as e:
            return

    def bump(self):
        if not self.bumped:
            self.curs.close()
            self.bumped = True
