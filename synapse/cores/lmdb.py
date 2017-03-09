import sys
import msgpack
import lmdb
import typing
import xxhash

import synapse.cores.common as s_cores_common
from synapse.common import genpath, msgenpack, msgunpack
import synapse.compat as s_compat

ValueT = typing.Union[int, str]

# FIXME:  consider duplicate keys for everything

# File conventions:
# i, p, v, t: iden, prop, value, timestamp
# i_enc, p_enc, v_key_enc, t_enc: above encoded to be space efficient and fully-ordered when
# compared lexicographically (i.e. 'aaa' < 'ba')
# pk:  primary key, unique identifier of the row in the main table
# pk_val_enc:  space efficient encoding of pk for use as value in an index table
# pk_key_enc:  database-efficient encoding of pk for use as key in main table

# N.B.  LMDB calls the separate namespaces in a a file "databases" (e.g. db=).


# Largest primary key value.  No more rows than this
MAX_PK = sys.maxsize

# Bytes in MAX_PK
MAX_PK_BYTES = 8 if sys.maxsize > 2**32 else 4

# Prefix to indicate that a v is a negative value an not the defaault nonnegative value
NEGATIVE_VAL_MARKER = -1

# Prefix to indicate than a v is a string
STRING_VAL_MARKER = -2

# Prefix to indicate that a v is hash of a string
HASH_VAL_MARKER = -3

# The negative marker encoded
NEGATIVE_VAL_MARKER_ENC = msgenpack(NEGATIVE_VAL_MARKER)

# The string marker encoded
STRING_VAL_MARKER_ENC = msgenpack(STRING_VAL_MARKER)

HASH_VAL_MARKER_ENC = msgenpack(HASH_VAL_MARKER)

# The maximum possible timestamp.  Probably a bit overkill
MAX_TIME_ENC = msgenpack(2 ** 64 - 1)

# Number of bytes in an UUID
UUID_SIZE = 16

MAX_UUID_PLUS_1 = 2**(UUID_SIZE*8)

# An index key can't ever be larger (lexicographically) than this
MAX_INDEX_KEY = b'\xff\xff'

# String vals of this size or larger will be truncated and hashed in index
LARGE_STRING_SIZE = 128

# Largest length allowed for a prop
MAX_PROP_LEN = 350


class DatabaseInconsistent(Exception):
    ''' If you get this Exception, that means the database is corrupt '''
    pass


class DatabaseLimitReached(Exception):
    pass


class CoreXact(s_cores_common.CoreXact):

    def _coreXactInit(self):
        self.txn = None

    def _coreXactCommit(self):
        self.txn.commit()

    def _coreXactBegin(self):
        self.txn = self.core.dbenv.begin(buffers=True)  # how to handle writing?

    def _coreXactAcquire(self):
        pass

    def _coreXactRelease(self):
        self.txn = None


class Cortex(s_cores_common.Cortex):

    def _initCortex(self):
        self._initDbConn()

        self.initSizeBy('ge', self._sizeByGe)
        self.initRowsBy('ge', self._rowsByGe)

        self.initSizeBy('le', self._sizeByLe)
        self.initRowsBy('le', self._rowsByLe)

        self.initTufosBy('ge', self._tufosByGe)
        self.initTufosBy('le', self._tufosByLe)

        # use helpers from base class
        self.initRowsBy('gt', self._rowsByGt)
        self.initRowsBy('lt', self._rowsByLt)
        self.initTufosBy('gt', self._tufosByGt)
        self.initTufosBy('lt', self._tufosByLt)

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

    def _get_largest_pk(self):
        with self.dbenv.begin(buffers=True) as txn:
            with txn.cursor(self.rows) as cursor:
                rv = cursor.last()
                if not rv:
                    return 0  # db is empty
                return self._dec_pk_key(cursor.key())

    def _initDbConn(self):
        dbinfo = self._initDbInfo()
        dbname = dbinfo.get('name')

        # FIXME:  make some settings configurable?

        # MAX DB Size.  Must be < 2 GiB for 32-bit.  Can be big for 64-bit systems.
        MAP_SIZE = 2147483647 if MAX_PK_BYTES == 4 else 1099511627776  # a terabyte

        # Maximum number of "databases", really tables.  We use 4 different tables (1 main plus
        # 3 indices)
        MAX_DBS = 4

        # flush system buffers to disk only once per transaction.  Can lead to last transaction
        # loss, but not corruption
        METASYNC = False

        # Write data directly to mapped memory
        WRITEMAP = True

        # Doesn't create a subdirectory for storage files
        SUBDIR = False

        # If we don't have multiple threads, we can disable locking, but we have multiple threads
        LOCK = True

        # Maximum simultaneous readers.
        MAX_READERS = 4

        self.dbenv = lmdb.Environment(dbname, map_size=MAP_SIZE, subdir=SUBDIR, metasync=METASYNC,
                                      writemap=WRITEMAP, max_readers=MAX_READERS, max_dbs=MAX_DBS,
                                      lock=LOCK)

        # LMDB has an optimization (integerkey) if all the keys in a table are unsigned size_t.

        # Make the main storage table, keyed by an incrementing counter, pk
        self.rows = self.dbenv.open_db(key=b"rows", integerkey=True)  # pk -> i,p,v,t

        # Note there's another LMDB optimization ("dupfixed") we're not using that we could
        # in the index tables.  It would pay off if a large proportion of keys are duplicates.

        # Make the iden-prop index table, keyed by iden-prop, with value being a pk
        self.index_ip = self.dbenv.open_db(key=b"ip", dupsort=True)  # i,p -> pk

        # Make the iden-value-prop index table, keyed by iden-value-prop, with value being a pk
        self.index_pvt = self.dbenv.open_db(key=b"pvt", dupsort=True)  # p,v,t -> pk

        # Make the iden-timestamp index table, keyed by iden-timestamp, with value being a pk
        self.index_pt = self.dbenv.open_db(key=b"pt", dupsort=True)  # p, t -> pk

        # Put 1 max key sentinel at the end of each index table.  This avoids unfortunate behavior
        # where the cursor moves backwards after deleting the final record.
        with self.dbenv.begin(buffers=True, write=True) as txn:
            for db in (self.index_ip, self.index_pvt, self.index_pt):
                txn.put(MAX_INDEX_KEY, b'', db=db)

        # Find the largest stored pk.  We just track this in memory from now on.
        largest_pk = self._get_largest_pk()
        if largest_pk == MAX_PK:
            raise DatabaseLimitReached('Out of primary key values')

        self.next_pk = largest_pk + 1

        def onfini():
            self.dbenv.close()
        self.onfini(onfini)

    @staticmethod
    def _enc_val_key(v: ValueT) -> (bytes, bool):
        ''' Encode a v.  Non-negative numbers are msgpack encoded.  Negative numbers are encoded
            as a marker, then the encoded negative of that value, so that the ordering of the
            encodings is easily mapped to the ordering of the negative numbers.  Note that this
            scheme prevents interleaving of value types:  all string encodings compare larger than
            all negative number encodings compare larger than all nonnegative encodings.  '''
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

    @staticmethod
    def _enc_val_val(v: ValueT) -> (bytes):
        return msgenpack(v)

    @staticmethod
    def _dec_val_val(unpacker: msgpack.Unpacker) -> (ValueT):
        return unpacker.unpack()

    if 0:
        @staticmethod
        def _dec_val_key(unpacker):
            ''' Decode a v.'''
            v = unpacker.unpack()
            if v == NEGATIVE_VAL_MARKER:
                return -1 * unpacker.unpack()
            elif v == STRING_VAL_MARKER:
                return unpacker.unpack()
            elif v == HASH_VAL_MARKER:
                return unpacker.unpack()
            return v

    @staticmethod
    def _enc_iden(iden: str) -> bytes:
        return int(iden, UUID_SIZE).to_bytes(UUID_SIZE, byteorder='big')


    @staticmethod
    def _dec_iden(iden_enc: bytes) -> str:
        # We add a 1 as the MSBit and remove it at the end to always produce an even number of
        # hexdigits.
        return hex(MAX_UUID_PLUS_1 + int.from_bytes(iden_enc, byteorder='big'))[3:]

    @staticmethod
    def _enc_pk_key(pk):
        ''' Encode for integerkey row DB option:  as a native size_t '''
        return int.to_bytes(pk, MAX_PK_BYTES, byteorder=sys.byteorder)

    @staticmethod
    def _dec_pk_key(pk_enc):
        return int.from_bytes(pk_enc, byteorder=sys.byteorder)

    def _addRows(self, rows):
        next_pk = self.next_pk
        txn = None
        try:
            txn = self.dbenv.begin(write=True, buffers=True)
            for i, p, v, t in rows:
                if next_pk > MAX_PK:
                    raise DatabaseLimitReached('Out of primary key values')
                if len(p) > MAX_PROP_LEN:
                    raise DatabaseLimitReached('Property length too large')
                i_enc = self._enc_iden(i)
                p_enc = msgenpack(p)
                v_val_enc = self._enc_val_val(v)
                v_key_enc = self._enc_val_key(v)
                t_enc = msgenpack(t)
                pk_val_enc = msgenpack(next_pk)

                pk_key_enc = self._enc_pk_key(next_pk)

                next_pk += 1
                rv = txn.put(pk_key_enc, i_enc + p_enc + v_val_enc + t_enc, overwrite=False,
                             append=True, db=self.rows)
                # Will only fail if record already exists, which should never happen
                if not rv:
                    raise DatabaseInconsistent('unexpected pk in DB')

                txn.put(i_enc + p_enc, pk_val_enc, overwrite=False, db=self.index_ip)
                txn.put(p_enc + v_key_enc + t_enc, pk_val_enc, overwrite=False, db=self.index_pvt)
                txn.put(p_enc + t_enc, pk_val_enc, overwrite=False, db=self.index_pt)

            # self.next_pk should be protected from multiple writers. Luckily lmdb write lock does
            # that for us.
            self.next_pk = next_pk
            txn.commit()
        except:
            if txn is not None:
                txn.abort()
                txn = None
            raise

    def _getRowByPkValEnc(self, txn, pk_val_enc, do_delete=False):
        UUID_SIZE = 16
        pk = msgunpack(pk_val_enc)
        if do_delete:
            row = txn.pop(self._enc_pk_key(pk), db=self.rows)
        else:
            row = txn.get(self._enc_pk_key(pk), db=self.rows)
        if row is None:
            raise DatabaseInconsistent('Index val has no corresponding row')
        i = self._dec_iden(row[:UUID_SIZE])
        unpacker = msgpack.Unpacker(use_list=False, encoding='utf8')
        unpacker.feed(row[UUID_SIZE:])
        p = unpacker.unpack()
        v = self._dec_val_val(unpacker)
        t = unpacker.unpack()
        return (i, p, v, t)

    def _getRowsById(self, iden):
        ret = []
        iden_enc = self._enc_iden(iden)
        with self.dbenv.begin(buffers=True) as txn:
            with txn.cursor(self.index_ip) as cursor:
                if not cursor.set_range(iden_enc):
                    return ret
                for key, value in cursor:
                    if key[:len(iden_enc)] != iden_enc:
                        return ret

                    # FIXME: check if anything remaining in buffer?
                    ret.append(self._getRowByPkValEnc(txn, value))
        return ret

    def _delRowsById(self, iden):
        i_enc = self._enc_iden(iden)

        with self.dbenv.begin(buffers=True, write=True) as txn:
            with txn.cursor(self.index_ip) as cursor:

                # Get the first record => i_enc
                if not cursor.set_range(i_enc):
                    return
                while True:
                    # We don't use iterator here because the delete already advances to the next
                    # record
                    key, value = cursor.item()
                    if key[:len(i_enc)] != i_enc:
                        return
                    p_enc = key[len(i_enc):].tobytes()
                    # Need to copy out with tobytes because we're deleting
                    pk_val_enc = value.tobytes()

                    rv = cursor.delete()
                    if not rv:
                        raise Exception('Delete failure')
                    self._delRowAndIndices(txn, pk_val_enc, i_enc=i_enc, p_enc=p_enc,
                                           delete_ip=False)

    def _delRowsByIdProp(self, iden, prop):
        i_enc = self._enc_iden(iden)
        p_enc = msgenpack(prop)

        with self.dbenv.begin(buffers=True, write=True) as txn:
            # Retrieve and delete I-P index
            pk_val_enc = txn.pop(i_enc + p_enc, db=self.index_ip)

            if pk_val_enc is None:
                return

            # Delete the row and the other indices
            self._delRowAndIndices(txn, pk_val_enc, i_enc=i_enc, p_enc=p_enc, delete_ip=False)

    def _delRowAndIndices(self, txn, pk_val_enc, i_enc=None, p_enc=None, v_key_enc=None, t_enc=None,
                          delete_ip=True, delete_pvt=True, delete_pt=True, only_if_val=None):
        ''' Deletes the row corresponding to pk_val_enc and the indices pointing to it '''
        i, p, v, t = self._getRowByPkValEnc(txn, pk_val_enc, do_delete=True)

        if only_if_val is not None and only_if_val != v:
            return

        if delete_ip and i_enc is None:
            i_enc = self._enc_iden(i)

        if p_enc is None:
            p_enc = msgenpack(p)

        if delete_pvt and v_key_enc is None:
            v_key_enc = self._enc_val_key(v)

        if (delete_pvt or delete_pt) and t_enc is None:
            t_enc = msgenpack(t)

        if delete_ip:
            # Delete I-P index entry
            rv = txn.delete(i_enc + p_enc, db=self.index_ip)
            if not rv:
                raise DatabaseInconsistent("Missing I-P index")

        if delete_pvt:
            # Delete P-V-T index entry
            rv = txn.delete(p_enc + v_key_enc + t_enc, db=self.index_pvt)
            if not rv:
                raise DatabaseInconsistent("Missing P-V-T index")

        if delete_pt:
            # Delete P-T index entry
            rv = txn.delete(p_enc + t_enc, db=self.index_pt)
            if not rv:
                raise DatabaseInconsistent("Missing P-T index")

    def _getRowsByIdProp(self, iden, prop):
        # FIXME:  use cursor for dup keys
        iden_enc = self._enc_iden(iden)
        prop_enc = msgenpack(prop)

        key = iden_enc + prop_enc

        ret = []
        with self.dbenv.begin(buffers=True) as txn:
            value = txn.get(key, db=self.index_ip)
            if value is None:
                return ret
            ret.append(self._getRowByPkValEnc(txn, value))
        return ret

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        return self._getRowsByProp(prop, valu, limit, mintime, maxtime, do_count_only=True)

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        self._getRowsByProp(prop, valu, mintime=mintime, maxtime=maxtime, do_delete_only=True)

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None,
                       do_count_only=False, do_delete_only=False):

        assert(not (do_count_only and do_delete_only))
        indx = self.index_pt if valu is None else self.index_pvt
        p_enc = msgenpack(prop)
        v_key_enc = b'' if valu is None else self._enc_val_key(valu)
        v_is_hashed = valu is not None and (v_key_enc[0] == HASH_VAL_MARKER_ENC)
        mintime_enc = b'' if mintime is None else msgenpack(mintime)
        maxtime_enc = MAX_TIME_ENC if maxtime is None else msgenpack(maxtime)

        first_key = p_enc + v_key_enc + mintime_enc
        last_key = p_enc + v_key_enc + maxtime_enc

        ret = []
        count = 0

        with self.dbenv.begin(buffers=True, write=do_delete_only) as txn:
            with txn.cursor(indx) as cursor:
                if not cursor.set_range(first_key):
                    return 0 if do_count_only else []
                while True:
                    key, value = cursor.item()
                    if key.tobytes() >= last_key:
                        break
                    if do_delete_only:
                        pk_val_enc = value.tobytes()

                        rv = cursor.delete()
                        if not rv:
                            raise Exception('Delete failure')

                        self._delRowAndIndices(txn, pk_val_enc, p_enc=p_enc,
                                               delete_pt=(valu is not None),
                                               delete_pvt=(valu is None), only_if_val=valu)
                    elif not do_count_only or v_is_hashed:
                        # If we hashed, we must double check that val actually matches in row
                        row = self._getRowByPkValEnc(txn, value)
                        if v_is_hashed:
                            if valu != row[2]:
                                continue
                        if not do_count_only:
                            ret.append(row)
                    count += 1
                    if limit is not None and limit >= count:
                        break
                    if not do_delete_only:
                        rv = cursor.next()
                        if not rv:
                            # Sentinel record should prevent this
                            raise DatabaseInconsistent('Got to end of index')
        if do_count_only:
            return count
        elif not do_delete_only:
            return ret

    def _sizeByGe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _rowsByGe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _sizeByLe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _rowsByLe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _tufosByGe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _tufosByLe(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _sizeByRange(self, prop, valu, limit=None):
        raise Exception('Not done yet')

    def _rowsByRange(self, prop, valu, limit=None):
        raise Exception('Not done yet')
