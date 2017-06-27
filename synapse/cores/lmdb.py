from __future__ import absolute_import

import sys
import struct
from binascii import unhexlify
if sys.version_info > (3, 0):
    from functools import lru_cache
from contextlib import contextmanager
from threading import Lock

import synapse.compat as s_compat
import synapse.datamodel as s_datamodel
import synapse.lib.threads as s_threads
import synapse.cores.common as s_cores_common
from synapse.common import genpath, msgenpack, msgunpack

import xxhash
import lmdb

# File conventions:
# i, p, v, t: iden, prop, value, timestamp
# i_enc, p_enc, v_key_enc, t_enc: above encoded to be space efficient and fully-ordered when
#                                 compared lexicographically (i.e. 'aaa' < 'ba')
# pk:  primary key, unique identifier of the row in the main table
# pk_enc:  space efficient encoding of pk for use as value in an index table

# N.B.  LMDB calls the separate namespaces in a file "databases" (e.g. named parameter db=), just
# like Berkeley DB.

# Largest primary key value.  No more rows than this
MAX_PK = sys.maxsize

# Bytes in MAX_PK
MAX_PK_BYTES = 8 if sys.maxsize > 2**32 else 4

# Prefix to indicate that a v is a nonnegative value
NONNEGATIVE_VAL_MARKER = 0

# Prefix to indicate that a v is a negative value
NEGATIVE_VAL_MARKER = -1

# Prefix to indicate than a v is a string
STRING_VAL_MARKER = -2

# Prefix to indicate that a v is hash of a string
HASH_VAL_MARKER = -3

# The negative marker encoded
NEGATIVE_VAL_MARKER_ENC = msgenpack(NEGATIVE_VAL_MARKER)

# The string marker encoded
STRING_VAL_MARKER_ENC = msgenpack(STRING_VAL_MARKER)

# The hash marker encoded
HASH_VAL_MARKER_ENC = msgenpack(HASH_VAL_MARKER)

# Number of bytes in a UUID
UUID_SIZE = 16

# An index key can't ever be larger (lexicographically) than this
MAX_INDEX_KEY = b'\xff' * 20

# String vals of this size or larger will be truncated and hashed in index.  What this means is
# that comparison on large string vals require retrieving the row from the main table
LARGE_STRING_SIZE = 128

# Largest length allowed for a prop
MAX_PROP_LEN = 350

# Smallest and largest values for an integer value.  Matches sqlite3
MAX_INT_VAL = 2 ** 63 - 1
MIN_INT_VAL = -1 * (2 ** 63)

# The maximum possible timestamp.  Probably a bit overkill
MAX_TIME_ENC = msgenpack(MAX_INT_VAL)

def _round_up(val, modulus):
    return val - val % -modulus

class DatabaseInconsistent(Exception):
    ''' If you get this Exception, that means the database is corrupt '''
    pass

class DatabaseLimitReached(Exception):
    ''' You've reached some limit of the database '''
    pass

# Python 2.7 version of lmdb buffers=True functions return buffer objects.  Python 3 version returns
# memoryview objects
if sys.version_info > (3, 0):
    def _memToBytes(x):
        return x.tobytes()
else:
    def _memToBytes(x):
        return str(x)

    def lru_cache(maxsize):
        ''' A dumb passthrough.  Python 2 impl is just going to be a tad slower '''
        def actual_decorator(wrappee):
            return wrappee
        return actual_decorator

def _encValKey(v):
    '''
    Encode a value as used in a key.

    Non-negative numbers are msgpack encoded.  Negative numbers are encoded as a marker, then the
    encoded negative of that value, so that the ordering of the encodings is easily mapped to the
    ordering of the negative numbers.  Strings too long are hashed.  Note that this scheme prevents
    interleaving of value types: all string encodings compare larger than all negative number
    encodings compare larger than all nonnegative encodings.
    '''
    if s_compat.isint(v):
        if v >= 0:
            return msgenpack(v)
        else:
            return NEGATIVE_VAL_MARKER_ENC + msgenpack(-v)
    else:
        if len(v) >= LARGE_STRING_SIZE:
            return (HASH_VAL_MARKER_ENC + msgenpack(xxhash.xxh64(v).intdigest()))
        else:
            return STRING_VAL_MARKER_ENC + msgenpack(v)

# Really just want to memoize the last iden encoded, but there might be some multithreading, so keep
# a few more (8)
@lru_cache(maxsize=8)
def _encIden(iden):
    ''' Encode an iden '''
    return unhexlify(iden)

# Try to memoize most of the prop names we get
@lru_cache(maxsize=1024)
def _encProp(prop):
    return msgenpack(prop)

# The precompiled struct parser for native size_t
_SIZET_ST = struct.Struct('@Q' if sys.maxsize > 2**32 else '@L')

def _encPk(pk):
    ''' Encode for integerkey row DB option:  as a native size_t '''
    return _SIZET_ST.pack(pk)

def _decPk(pk_enc):
    ''' Inverse of above '''
    return _SIZET_ST.unpack(pk_enc)[0]

def _calcFirstLastKeys(prop, valu, mintime, maxtime):
    '''
    Returns the encoded bytes for the start and end keys to the pt or pvt
    index.  Helper function for _{get,del}RowsByProp
    '''
    p_enc = _encProp(prop)
    v_key_enc = b'' if valu is None else _encValKey(valu)
    v_is_hashed = valu is not None and (v_key_enc[0] == HASH_VAL_MARKER_ENC)
    if mintime is None and maxtime is None:
        return (p_enc + v_key_enc, None, v_is_hashed, True)
    mintime_enc = b'' if mintime is None else msgenpack(mintime)
    maxtime_enc = MAX_TIME_ENC if maxtime is None else msgenpack(maxtime)

    first_key = p_enc + v_key_enc + mintime_enc
    last_key = p_enc + v_key_enc + maxtime_enc
    return (first_key, last_key, v_is_hashed, False)

class CoreXact(s_cores_common.CoreXact):

    def _coreXactInit(self, size=None):
        self.txn = None

    def _coreXactCommit(self):
        self.txn.commit()

    def _coreXactBegin(self):
        self.core._ensure_map_slack()
        self.txn = self.core.dbenv.begin(buffers=True, write=True)

    def _coreXactAcquire(self):
        self.core._write_lock.acquire()

    def _coreXactRelease(self):
        self.core._write_lock.release()

class Cortex(s_cores_common.Cortex):

    def _initCortex(self):
        self._initDbConn()

        self.initSizeBy('ge', self._sizeByGe)
        self.initRowsBy('ge', self._rowsByGe)

        self.initSizeBy('le', self._sizeByLe)
        self.initRowsBy('le', self._rowsByLe)
        self.initSizeBy('lt', self._sizeByLt)

        # use helpers from base class
        self.initRowsBy('gt', self._rowsByGt)
        self.initRowsBy('lt', self._rowsByLt)

        self.initSizeBy('range', self._sizeByRange)
        self.initRowsBy('range', self._rowsByRange)

    def _initDbInfo(self):
        name = self._link[1].get('path')[1:]
        if not name:
            raise Exception('No Path Specified!')

        if name.find(':') == -1:
            name = genpath(name)

        return {'name': name}

    def _getCoreXact(self, size=None):
        return CoreXact(self, size=size)

    def _getLargestPk(self):
        with self._getTxn() as txn, txn.cursor(self.rows) as cursor:
            if not cursor.last():
                return 0  # db is empty
            return _decPk(cursor.key())

    @contextmanager
    def _getTxn(self, write=False):
        '''
        Acquires a transaction.

        LMDB doesn't have the concept of store access without a transaction, so figure out
        whether there's already one open and use that, else make one.  If we found an existing
        transaction, this doesn't close it after leaving the context.  If we made one and the
        context is exited without exception, the transaction is committed.
        '''
        existing_xact = self._core_xacts.get(s_threads.iden())
        if existing_xact is not None:
            yield existing_xact.txn
        else:
            if write:
                with self._write_lock:
                    self._ensure_map_slack()
                    with self.dbenv.begin(buffers=True, write=True) as txn:
                        yield txn
            else:
                with self.dbenv.begin(buffers=True, write=False) as txn:
                    yield txn

    def _ensure_map_slack(self):
        '''
        Checks if there's enough extra space in the map to accomodate a commit of at least
        self._slack_space size and increase it if not.
        '''
        # Figure how how much space the DB is using
        used = 4096 * self.dbenv.info()['last_pgno']

        # Round up to the next multiple of _map_slack
        target_size = min(self._max_map_size, _round_up(used + self._map_slack, self._map_slack))

        # Increase map size if necessary
        if target_size > self._map_size:
            self.dbenv.set_mapsize(target_size)
            self._map_size = target_size

    def _initDbConn(self):
        dbinfo = self._initDbInfo()
        dbname = dbinfo.get('name')

        # Initial DB Size.  Must be < 2 GiB for 32-bit.  Can be big for 64-bit systems.  Will create
        # a file of that size.  On MacOS/Windows, will actually immediately take up that much
        # disk space.
        DEFAULT_MAP_SIZE = 256 * 1024 * 1024

        # _write_lock exists solely to hold off other threads' write transactions long enough to
        # potentially increase the map size.
        self._write_lock = Lock()

        map_size = self._link[1].get('lmdb:mapsize', DEFAULT_MAP_SIZE)
        self._map_size, _ = s_datamodel.getTypeNorm('int', map_size)
        self._max_map_size = 2**48 if sys.maxsize > 2**32 else 2**31

        map_slack = self._link[1].get('lmdb:mapslack', 2 ** 30)
        self._map_slack, _ = s_datamodel.getTypeNorm('int', map_slack)

        # Maximum number of "databases", really tables.  We use 4 different tables (1 main plus
        # 3 indices)
        MAX_DBS = 4

        # flush system buffers to disk only once per transaction.  Set to False can lead to last
        # transaction loss, but not corruption

        metasync_val = self._link[1].get('lmdb:metasync', False)
        metasync, _ = s_datamodel.getTypeNorm('bool', metasync_val)

        # If sync is False, could lead to database corruption on power loss
        sync_val = self._link[1].get('lmdb:sync', True)
        sync, _ = s_datamodel.getTypeNorm('bool', sync_val)

        # Write data directly to mapped memory
        WRITEMAP = True

        # Doesn't create a subdirectory for storage files
        SUBDIR = False

        # We can disable locking, but bad things might happen if we have multiple threads
        DEFAULT_LOCK = True
        lock_val = self._link[1].get('lmdb:lock', DEFAULT_LOCK)
        lock, _ = s_datamodel.getTypeNorm('bool', lock_val)

        # Maximum simultaneous readers.
        MAX_READERS = 4
        max_readers = self._link[1].get('lmdb:maxreaders', MAX_READERS)
        max_readers, _ = s_datamodel.getTypeNorm('int', max_readers)
        if max_readers == 1:
            lock = False

        self.dbenv = lmdb.Environment(dbname, map_size=self._map_size, subdir=SUBDIR,
                                      metasync=metasync, writemap=WRITEMAP, max_readers=max_readers,
                                      max_dbs=MAX_DBS, sync=sync, lock=lock)

        # Check we're not running a weird version of LMDB
        assert(self.dbenv.stat()['psize'] == 4096)

        # Ensure we have enough room in the map for expansion
        self._ensure_map_slack()

        # Make the main storage table, keyed by an incrementing counter, pk
        # LMDB has an optimization (integerkey) if all the keys in a table are unsigned size_t.
        self.rows = self.dbenv.open_db(key=b"rows", integerkey=True)  # pk -> i,p,v,t

        # Note there's another LMDB optimization ("dupfixed") we're not using that we could
        # in the index tables.  It would pay off if a large proportion of keys are duplicates.

        # Make the iden-prop index table, keyed by iden-prop, with value being a pk
        self.index_ip = self.dbenv.open_db(key=b"ip", dupsort=True)  # i,p -> pk

        # Make the prop-val-timestamp index table, with value being a pk
        self.index_pvt = self.dbenv.open_db(key=b"pvt", dupsort=True)  # p,v,t -> pk

        # Make the prop-timestamp index table, with value being a pk
        self.index_pt = self.dbenv.open_db(key=b"pt", dupsort=True)  # p, t -> pk

        # Put 1 max key sentinel at the end of each index table.  This avoids unfortunate behavior
        # where the cursor moves backwards after deleting the final record.
        with self._getTxn(write=True) as txn:
            for db in (self.index_ip, self.index_pvt, self.index_pt):
                txn.put(MAX_INDEX_KEY, b'', db=db)
                # One more sentinel for going backwards through the pvt table.
                txn.put(b'\x00', b'', db=self.index_pvt)

        # Find the largest stored pk.  We just track this in memory from now on.
        largest_pk = self._getLargestPk()
        if largest_pk == MAX_PK:
            raise DatabaseLimitReached('Out of primary key values')

        self.next_pk = largest_pk + 1

        def onfini():
            self.dbenv.close()
        self.onfini(onfini)

    def _addRows(self, rows):
        '''
        Adds a bunch of rows to the database

        Take care:  this was written this way for performance, in particular when len(rows) is
        large.
        '''
        encs = []

        with self._getTxn(write=True) as txn:
            next_pk = self.next_pk

            # First, we encode all the i, p, v, t for all rows
            for i, p, v, t in rows:
                if next_pk > MAX_PK:
                    raise DatabaseLimitReached('Out of primary key values')
                if len(p) > MAX_PROP_LEN:
                    raise DatabaseLimitReached('Property length too large')
                i_enc = _encIden(i)
                p_enc = _encProp(p)
                v_key_enc = _encValKey(v)
                t_enc = msgenpack(t)
                pk_enc = _encPk(next_pk)
                row_enc = msgenpack((i, p, v, t))

                # idx          0      1       2       3       4          5
                encs.append((i_enc, p_enc, row_enc, t_enc, v_key_enc, pk_enc))
                next_pk += 1

            # An iterator of what goes into the main table: key=pk_enc, val=encoded(i, p, v, t)
            kvs = ((x[5], x[2]) for x in encs)

            # Shove it all in at once
            consumed, added = txn.cursor(db=self.rows).putmulti(kvs, overwrite=False, append=True)
            if consumed != added or consumed != len(encs):
                # Will only fail if record already exists, which should never happen
                raise DatabaseInconsistent('unexpected pk in DB')

            # Update the indices for all rows
            kvs = ((x[0] + x[1], x[5]) for x in encs)
            txn.cursor(db=self.index_ip).putmulti(kvs, dupdata=True)
            kvs = ((x[1] + x[4] + x[3], x[5]) for x in encs)
            txn.cursor(db=self.index_pvt).putmulti(kvs, dupdata=True)
            kvs = ((x[1] + x[3], x[5]) for x in encs)
            txn.cursor(db=self.index_pt).putmulti(kvs, dupdata=True)

            # self.next_pk should be protected from multiple writers. Luckily lmdb write lock does
            # that for us.
            self.next_pk = next_pk

    def _getRowByPkValEnc(self, txn, pk_enc):
        row = txn.get(pk_enc, db=self.rows)
        if row is None:
            raise DatabaseInconsistent('Index val has no corresponding row')
        return msgunpack(row)

    def _getRowsById(self, iden):
        iden_enc = _encIden(iden)
        rows = []
        with self._getTxn() as txn, txn.cursor(self.index_ip) as cursor:
            if not cursor.set_range(iden_enc):
                raise DatabaseInconsistent("Missing sentinel")
            for key, pk_enc in cursor:
                if key[:len(iden_enc)] != iden_enc:
                    break
                rows.append(self._getRowByPkValEnc(txn, pk_enc))

            return rows

    def _delRowsById(self, iden):
        i_enc = _encIden(iden)

        with self._getTxn(write=True) as txn, txn.cursor(self.index_ip) as cursor:
            # Get the first record >= i_enc
            if not cursor.set_range(i_enc):
                raise DatabaseInconsistent("Missing sentinel")
            while True:
                # We don't use iterator here because the delete already advances to the next
                # record
                key, value = cursor.item()
                if key[:len(i_enc)] != i_enc:
                    return
                p_enc = _memToBytes(key[len(i_enc):])
                # Need to copy out with tobytes because we're deleting
                pk_enc = _memToBytes(value)

                if not cursor.delete():
                    raise Exception('Delete failure')
                self._delRowAndIndices(txn, pk_enc, i_enc=i_enc, p_enc=p_enc,
                                       delete_ip=False)

    def _delRowsByIdProp(self, iden, prop, valu=None):
        i_enc = _encIden(iden)
        p_enc = _encProp(prop)
        first_key = i_enc + p_enc

        with self._getTxn(write=True) as txn, txn.cursor(self.index_ip) as cursor:
            # Retrieve and delete I-P index
            if not cursor.set_range(first_key):
                raise DatabaseInconsistent("Missing sentinel")
            while True:
                # We don't use iterator here because the delete already advances to the next
                # record
                key, value = cursor.item()
                if key[:len(first_key)] != first_key:
                    return
                # Need to copy out with tobytes because we're deleting
                pk_enc = _memToBytes(value)

                # Delete the row and the other indices
                if not self._delRowAndIndices(txn, pk_enc, i_enc=i_enc, p_enc=p_enc,
                                              delete_ip=False, only_if_val=valu):
                    if not cursor.next():
                        raise DatabaseInconsistent("Missing sentinel")
                else:
                    if not cursor.delete():
                        raise Exception('Delete failure')

    def _delRowAndIndices(self, txn, pk_enc, i_enc=None, p_enc=None, v_key_enc=None, t_enc=None,
                          delete_ip=True, delete_pvt=True, delete_pt=True, only_if_val=None):
        ''' Deletes the row corresponding to pk_enc and the indices pointing to it '''
        with txn.cursor(db=self.rows) as cursor:
            if not cursor.set_key(pk_enc):
                raise DatabaseInconsistent("Missing PK")
            i, p, v, t = msgunpack(cursor.value())

            if only_if_val is not None and only_if_val != v:
                return False
            cursor.delete()

        if delete_ip and i_enc is None:
            i_enc = _encIden(i)

        if p_enc is None:
            p_enc = _encProp(p)

        if delete_pvt and v_key_enc is None:
            v_key_enc = _encValKey(v)

        if (delete_pvt or delete_pt) and t_enc is None:
            t_enc = msgenpack(t)

        if delete_ip:
            # Delete I-P index entry
            if not txn.delete(i_enc + p_enc, value=pk_enc, db=self.index_ip):
                raise DatabaseInconsistent("Missing I-P index")

        if delete_pvt:
            # Delete P-V-T index entry
            if not txn.delete(p_enc + v_key_enc + t_enc, value=pk_enc, db=self.index_pvt):
                raise DatabaseInconsistent("Missing P-V-T index")

        if delete_pt:
            # Delete P-T index entry
            if not txn.delete(p_enc + t_enc, value=pk_enc, db=self.index_pt):
                raise DatabaseInconsistent("Missing P-T index")

        return True

    def _getRowsByIdProp(self, iden, prop, valu=None):
        # For now not making a ipv index because multiple v for a given i,p are probably rare
        iden_enc = _encIden(iden)
        prop_enc = _encProp(prop)

        first_key = iden_enc + prop_enc

        ret = []

        with self._getTxn() as txn, txn.cursor(self.index_ip) as cursor:
            if not cursor.set_range(first_key):
                raise DatabaseInconsistent("Missing sentinel")
            for key, value in cursor:
                if _memToBytes(key) != first_key:
                    return ret
                row = self._getRowByPkValEnc(txn, value)
                if valu is not None and row[2] != valu:
                    continue
                ret.append(row)
        raise DatabaseInconsistent("Missing sentinel")

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        return self._getRowsByProp(prop, valu, limit, mintime, maxtime, do_count_only=True)

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None,
                       do_count_only=False):
        indx = self.index_pt if valu is None else self.index_pvt
        first_key, last_key, v_is_hashed, do_fast_compare = _calcFirstLastKeys(prop, valu,
                                                                               mintime, maxtime)

        count = 0
        rows = []

        with self._getTxn() as txn, txn.cursor(indx) as cursor:
            if not cursor.set_range(first_key):
                raise DatabaseInconsistent("Missing sentinel")
            while True:
                key, pk_enc = cursor.item()
                if do_fast_compare:
                    if key[:len(first_key)] != first_key:
                        break
                else:
                    if _memToBytes(key) >= last_key:
                        break
                if v_is_hashed or not do_count_only:
                    row = self._getRowByPkValEnc(txn, pk_enc)
                    if v_is_hashed:
                        if row[2] != valu:
                            continue
                    if not do_count_only:
                        rows.append(row)
                count += 1
                if limit is not None and count >= limit:
                    break
                if not cursor.next():
                    raise DatabaseInconsistent('Missing sentinel')

        return count if do_count_only else rows

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        indx = self.index_pt if valu is None else self.index_pvt
        first_key, last_key, v_is_hashed, do_fast_compare = _calcFirstLastKeys(prop, valu,
                                                                               mintime, maxtime)
        with self._getTxn(write=True) as txn, txn.cursor(indx) as cursor:
            if not cursor.set_range(first_key):
                raise DatabaseInconsistent("Missing sentinel")
            while True:
                key, pk_enc = cursor.item()
                if do_fast_compare:
                    if key[:len(first_key)] != first_key:
                        break
                else:
                    if _memToBytes(key) >= last_key:
                        break

                if self._delRowAndIndices(txn, pk_enc,
                                          delete_pt=(valu is not None),
                                          delete_pvt=(valu is None),
                                          only_if_val=(valu if v_is_hashed else None)):
                    # Delete did go through: delete entry at cursor
                    if not cursor.delete():
                        raise Exception('Delete failure')
                else:
                    # Delete didn't go through:  advance to next
                    if not cursor.next():
                        raise DatabaseInconsistent('Missing sentinel')

    def _sizeByGe(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, valu, MAX_INT_VAL, limit, right_closed=True,
                                  do_count_only=True)

    def _rowsByGe(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, valu, MAX_INT_VAL, limit, right_closed=True)

    def _sizeByLe(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, MIN_INT_VAL, valu, limit, right_closed=True,
                                  do_count_only=True)

    def _sizeByLt(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, MIN_INT_VAL, valu, limit, right_closed=False,
                                  do_count_only=True)

    def _rowsByLe(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, MIN_INT_VAL, valu, limit, right_closed=True)

    def _sizeByRange(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, valu[0], valu[1], limit, do_count_only=True)

    def _rowsByRange(self, prop, valu, limit=None):
        return self._rowsByMinmax(prop, valu[0], valu[1], limit)

    def _rowsByMinmax(self, prop, minval, maxval, limit, right_closed=False, do_count_only=False):
        ''' Returns either count or actual rows for a range of prop vals where both min and max
            may be closed (included) or open (not included) '''
        if minval > maxval:
            return 0
        do_neg_search = (minval < 0)
        do_pos_search = (maxval >= 0)
        ret = 0 if do_count_only else []

        p_enc = _encProp(prop)

        # The encodings of negative integers and positive integers are not continuous, so we split
        # into two queries.  Also, the ordering of the encoding of negative integers is backwards.
        if do_neg_search:
            # We include the right boundary (-1) if we're searching through to the positives
            this_right_closed = do_pos_search or right_closed
            first_val = minval
            last_val = min(-1, maxval)
            ret += self._subrangeRows(p_enc, first_val, last_val, limit, this_right_closed,
                                      do_count_only)
            if limit is not None:
                limit -= ret if do_count_only else len(ret)
                if limit == 0:
                    return ret

        if do_pos_search:
            first_val = max(0, minval)
            last_val = maxval
            ret += self._subrangeRows(p_enc, first_val, last_val, limit, right_closed,
                                      do_count_only)
        return ret

    def _subrangeRows(self, p_enc, first_val, last_val, limit, right_closed, do_count_only):
        ''' Performs part of a range query, either completely negative or non-negative '''
        first_key = p_enc + _encValKey(first_val)

        am_going_backwards = (first_val < 0)

        last_key = p_enc + _encValKey(last_val)

        ret = []
        count = 0

        # Figure out the terminating condition of the loop
        if am_going_backwards:
            term_cmp = bytes.__lt__ if right_closed else bytes.__le__
        else:
            term_cmp = bytes.__gt__ if right_closed else bytes.__ge__

        with self._getTxn() as txn, txn.cursor(self.index_pvt) as cursor:
            if not cursor.set_range(first_key):
                raise DatabaseInconsistent("Missing sentinel")
            if am_going_backwards:
                # set_range sets the cursor at the first key >= first_key, if we're going backwards
                # we actually want the first key <= first_key
                if _memToBytes(cursor.key()[:len(first_key)]) > first_key:
                    if not cursor.prev():
                        raise DatabaseInconsistent("Missing sentinel")
                it = cursor.iterprev(keys=True, values=True)
            else:
                it = cursor.iternext(keys=True, values=True)

            for key, value in it:
                if term_cmp(_memToBytes(key[:len(last_key)]), last_key):
                    break
                count += 1
                if not do_count_only:
                    ret.append(self._getRowByPkValEnc(txn, value))
                if limit is not None and count >= limit:
                    break
        return count if do_count_only else ret
