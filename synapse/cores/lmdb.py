import sys
import uuid
import msgpack
import lmdb

import synapse.cores.common as s_cores_common
from synapse.common import genpath, msgenpack, msgunpack
import synapse.compat as s_compat


MAX_PK = sys.maxsize
MAX_PK_BYTES = 8 if sys.maxsize > 2**32 else 4
NEGATIVE_VAL_MARKER = -1
STRING_VAL_MARKER = -2
NEGATIVE_VAL_MARKER_ENC = msgenpack(NEGATIVE_VAL_MARKER)
STRING_VAL_MARKER_ENC = msgenpack(STRING_VAL_MARKER)
MAX_TIME_ENC = msgenpack(2 ** 64 - 1)


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
        if 0:

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

        # MAX DB Size.  Must be < 2 GiB for 32-bit.  Can be big for 64-bit systems.
        MAP_SIZE = 10485760

        # Maximum number of "databases", really namespaces.  We use 4 different tables (1 main plus
        # 3 indices)
        MAX_DBS = 4

        # flush system buffers to disk only once per transaction.  Can lead to last transaction
        # loss, but not corruption
        METASYNC = False

        # Write data directly to mapped memory
        WRITEMAP = True

        # Doesn't create a subdirectory for files
        SUBDIR = False

        # Disable locking DB.  We're single threaded, right?
        LOCK = False

        # Maximum simultaneous readers.  We're single threaded, right?
        MAX_READERS = 1

        self.dbenv = lmdb.Environment(dbname, map_size=MAP_SIZE, subdir=SUBDIR, metasync=METASYNC,
                                      writemap=WRITEMAP, max_readers=MAX_READERS, max_dbs=MAX_DBS,
                                      lock=LOCK)

        # LMDB has an optimization if all the keys in a namespace are unsigned size_ts.
        self.rows = self.dbenv.open_db(key=b"rows", integerkey=True)  # pk -> i,p,v,t
        self.index_ip = self.dbenv.open_db(key=b"ip")  # i,p -> pk
        self.index_pvt = self.dbenv.open_db(key=b"pvt")  # p,v,t -> pk
        self.index_pt = self.dbenv.open_db(key=b"pt")  # p, t -> pk

        largest_pk = self._get_largest_pk()
        if largest_pk == MAX_PK:
            raise Exception('Out of primary key values')

        self.next_pk = largest_pk + 1

        def onfini():
            self.dbenv.close()
        self.onfini(onfini)

    @staticmethod
    def _enc_val(v):
        if s_compat.isint(v):
            if v >= 0:
                return msgenpack(v)
            else:
                return NEGATIVE_VAL_MARKER_ENC + msgenpack(-v)
        else:
            return STRING_VAL_MARKER_ENC + msgenpack(v)

    @staticmethod
    def _dec_val(unpacker):
        v = unpacker.unpack()
        if v == NEGATIVE_VAL_MARKER:
            return -1 * unpacker.unpack()
        elif v == STRING_VAL_MARKER:
            return unpacker.unpack()
        return v

    @staticmethod
    def _enc_iden(iden: str) -> bytes:
        return uuid.UUID(hex=iden).bytes

    @staticmethod
    def _dec_iden(iden_enc: bytes) -> str:
        return uuid.UUID(bytes=iden_enc.tobytes()).hex

    @staticmethod
    def _enc_pk_key(pk):
        ''' Encode for integerkey row DB option '''
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
                    raise Exception('Out of primary key values')
                i_enc = self._enc_iden(i)
                p_enc = msgenpack(p)
                v_enc = self._enc_val(v)
                t_enc = msgenpack(t)
                pk_val_enc = msgenpack(next_pk)

                pk_key_enc = self._enc_pk_key(next_pk)

                next_pk += 1
                rv = txn.put(pk_key_enc, i_enc + p_enc + v_enc + t_enc, overwrite=False,
                             append=True, db=self.rows)
                # Will only fail if record already exists, which should never happen
                if not rv:
                    raise Exception('unexpected pk in DB')

                # Ignoring if already exists; emulating sqlite insert here
                txn.put(i_enc + p_enc, pk_val_enc, overwrite=False, db=self.index_ip)
                txn.put(p_enc + v_enc + t_enc, pk_val_enc, overwrite=False, db=self.index_pvt)
                txn.put(p_enc + t_enc, pk_val_enc, overwrite=False, db=self.index_pt)
            txn.commit()
            self.next_pk = next_pk
        except:
            if txn is not None:
                txn.abort()
                txn = None
            raise

    def _getRowByPkEnc(self, txn, pk_enc):
        UUID_SIZE = 16
        pk = msgunpack(pk_enc)
        row = txn.get(self._enc_pk_key(pk), db=self.rows)
        if row is None:
            raise Exception('Index val has no corresponding row')
        i = self._dec_iden(row[:UUID_SIZE])
        unpacker = msgpack.Unpacker(use_list=False, encoding='utf8')
        unpacker.feed(row[UUID_SIZE:])
        p = unpacker.unpack()
        v = self._dec_val(unpacker)
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
                    ret.append(self._getRowByPkEnc(txn, value))
        return ret

    def _getRowsByIdProp(self, iden, prop):
        # ??? Confused:  how can there ever be more than 1 row with a certain iden prop?
        iden_enc = self._enc_iden(iden)
        prop_enc = msgenpack(prop)

        key = iden_enc + prop_enc

        ret = []
        with self.dbenv.begin(buffers=True) as txn:
            value = txn.get(key, db=self.index_ip)
            if value is None:
                return ret
            ret.append(self._getRowByPkEnc(txn, value))
        return ret

    def _getSizeByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None):
        return self._getRowsByProp(prop, valu, limit, mintime, maxtime, do_count_only=True)

    def _getRowsByProp(self, prop, valu=None, limit=None, mintime=None, maxtime=None,
                       do_count_only=False):
        indx = self.index_pt if valu is None else self.index_pvt
        prop_enc = msgenpack(prop)
        valu_enc = b'' if valu is None else self._enc_val(valu)
        mintime_enc = b'' if mintime is None else msgenpack(mintime)
        maxtime_enc = MAX_TIME_ENC if maxtime is None else msgenpack(maxtime)

        first_key = prop_enc + valu_enc + mintime_enc
        last_key = prop_enc + valu_enc + maxtime_enc

        ret = []
        count = 0

        with self.dbenv.begin(buffers=True) as txn:
            with txn.cursor(indx) as cursor:
                if not cursor.set_range(first_key):
                    return 0 if do_count_only else []
                for key, value in cursor:
                    if key.tobytes() >= last_key:
                        break
                    if do_count_only:
                        count += 1
                    else:
                        ret.append(self._getRowByPkEnc(txn, value))
                    if limit is not None and limit >= len(ret):
                        break
        if do_count_only:
            return count
        else:
            return ret
