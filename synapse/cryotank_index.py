import struct
import logging
import threading
from collections import namedtuple, defaultdict
from typing import List, Dict, Union, Iterable, Tuple, Any, Optional  # NOQA

import lmdb  # type: ignore
import msgpack  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.synasync as s_async
import synapse.lib.const as s_const
import synapse.datamodel as s_datamodel
import synapse.lib.msgpack as s_msgpack
import synapse.lib.datapath as s_datapath
import synapse.lib.lmdb as s_lmdb

logger = logging.getLogger(__name__)

# N.B.  To harmonize with LMDB requirements, writing only occurs on the worker thread, while reading indices takes
# place in the caller's thread.  Both reading and writing index metadata (that is, information about which indices
# are running) take place on the worker's thread.


# TODO: could index faster if ingest/normalize is separate thread from writing
# FIXME:  what to do with subprops returned from getTypeNorm
# FIXME:  need a way to specify/load custom types

BE_UINT_ST = struct.Struct('>Q')

# Describes a single index in the system.

_MetaEntry = namedtuple('_MetaEntry', ('ver', 'syntype', 'datapath', 'awake'))

class _IndexMeta:
    '''
    Manages persistence of index metadata with an in-memory copy

    "Schema":
    b'indices' key has msgpack encoded dict of
    { 'present': [propname: {'ver': 0, 'syntype': type, 'datapath': datapath}, ...],
      'deleting': [{propname: ver}, ...]
    }
    b'progress' key has mesgpack encoded dict of
    { propname: next_offset, ... }

    '''

    def __init__(self, dbenv: lmdb.Environment, metatbl: lmdb._Database) -> None:
        with dbenv.begin(db=metatbl, buffers=True) as txn:
            indices_enc = txn.get(b'indices')
            progress_enc = txn.get(b'progress')
        if indices_enc is None or progress_enc is None:
            if indices_enc is None and progress_enc is None:
                is_new_db = True
                indices_enc = s_msgpack.en({'meta': {}, 'delete': {}})
                progress_enc = s_msgpack.en({})
            else:
                raise s_exc.CorruptDatabase('missing meta information in index meta')
        indices = s_msgpack.un(indices_enc)

        self._indices = {k: _MetaEntry(**v) for k, v in indices['present']}
        self._deleting = indices['deleting']
        self._metatbl = metatbl
        self._dbenv = dbenv
        self._progresses = defaultdict(msgpack.un(progress_enc), int)  # type: ignore
        if not all(p in self._indices for p in self._deleting):
            raise s_exc.CorruptDatabase('index meta table: delete entry with unrecognized property name')
        if is_new_db:
            self.dump()
            self.updateProgress(0)

    def dump(self) -> None:
        '''
        Persists the rarely-changed meta information
        '''
        d = {'delete': self._deleting,
             'present': {k: v._asdict() for k, v in self._indices.items()}}

        with self._dbenv.begin(db=self._metatbl, buffers=True, write=True) as txn:
            txn.put(b'indices', s_msgpack.en(d))

    def updateProgress(self, nextoff: int) -> None:
        '''
        Update in memory then persist the frequently-changed progress (i.e. one after the last offset an index has
        gotten.
        '''

        for p in self._progresses:
            if self._indices[p].awake:
                self._progresses[p] = max(self._progresses[p], nextoff)

        with self._dbenv.begin(db=self._metatbl, buffers=True, write=True) as txn:
            txn.put(b'progress', s_msgpack.en(self._progresses))

    def addIndex(self, prop: str, syntype: str, datapath: str) -> None:
        if prop in self._indices:
            raise s_exc.IndexAlreadyPresent

        s_datamodel.tlib.reqDataType(syntype)
        # If we're in the middle of deleting an index with the same property name, make sure the new one has a new
        # version
        propver = self._deleting.get(prop, 0) + 1
        with self._dbenv.begin(db=self._metatbl, buffers=True, write=True) as txn:
            val = s_msgpack.en({'ver': propver, 'syntype': syntype, 'datapath': datapath})
            rv = txn.put(s_msgpack.en(prop), val, overwrite=False)
            if not rv:
                raise s_exc.BadCoreStore('failure to write index metadata')
            rv = txn.put(msgpack.en(('progress', prop)), msgpack.en(0), overwrite=False)
            if not rv:
                raise s_exc.BadCoreStore('failure to write index metadata')
        self.dump()

    def delIndex(self, prop: str) -> None:
        if prop not in self._indices:
            raise s_exc.IndexNotPresent
        with self._dbenv.begin(db=self._metatbl, buffers=True, write=True) as txn:
            rv = txn.delete(s_msgpack.en(prop))
            if not rv:
                raise s_exc.BadCoreStore('missing index metadata')
            rv = txn.delete(s_msgpack.en(('progress', prop)))
            if not rv:
                raise s_exc.BadCoreStore('missing index metadata')
            rv = txn.put(s_msgpack.en(('delete', self._indices[prop].ver)))
            if not rv:
                raise s_exc.BadCoreStore('missing index metadata')

        # Make sure to remove the progress entry in case a new index with the same propname gets added later
        del self._progresses[prop]
        self.dump()
        self.updateProgress(0)

    def markDeleteComplete(self, prop: str) -> None:
        del self._deleting[prop]
        self.dump()

    def deletes(self) -> Iterable[Tuple[str, int]]:
        return ((k, self._deleting[k]) for k in sorted(self._deleting))

    def activeIndices(self) -> Iterable[Tuple[str, _MetaEntry]]:
        return ((k, self._indices[k]) for k in sorted(self._indices) if self._indices[k].awake)

    def latestIndexVersion(self, prop: str) -> Optional[int]:
        try:
            return self._indices[prop].ver
        except KeyError:
            return None

class CryoTankIndexer:
    '''
    Manages indexing of a single cryotank's records
    '''
    MAX_WAIT_S = 10

    def __init__(self, cryotank):
        self.cryotank = cryotank
        self._going_down = threading.Event()
        self._worker = threading.Thread(target=self._loop)
        path = s_common.gendir(self.path, 'cryo_index.lmdb')
        cryotank_map_size = cryotank.lmdb.info()['map_size']
        self._dbenv = lmdb.open(path, writemap=True, metasync=False, max_readers=2, max_dbs=4,
                                map_size=cryotank_map_size)
        lmdb._ensure_map_slack(self._dbenv, s_const.gibibyte)
        self._meta_table = self._dbenv.open_db(b'meta')
        # pv -> offset table
        self._idxtbl = self._dbenv.open_db(b'indices')
        # offset -> normalized records
        self._normtbl = self._dbenv.open_db(b'norms')
        self._to_delete = {}  # type: Dict[str, int]
        self._boss = s_async.Boss()
        self._need_to_parse_meta = True
        # A dict of propname -> version, type, datapath dict
        self._meta = _IndexMeta.load(self._dbenv, self._meta_table)
        self._next_offset = self._meta.lowest_progress()
        # Just the propnames (in sorted order)
        self._chunk_sz = 1000  # How many records to read at a time
        self._worker.start()
        self._remove_chunk_sz = 1000

    def _removeSome(self):
        # Make some progress on removing deleted indices
        left = self._remove_chunk_sz
        for prop, ver in self._meta.deletes():
            if not left:
                break
            key_enc = s_msgpack.en((prop, ver))
            with self._dbenv.begin(db=self._indextbl, buffers=True, write=True) as txn, txn.cursor() as curs:
                if not curs.set_range(key_enc):
                    break
                for k in curs.iternext(values=False):
                    if k != key_enc:
                        break
                    if not curs.delete():
                        raise s_exc.CorruptDatabase('delete failure')
                    left += 1

            self._meta.markDeleteComplete(prop)

    def _normalize_records(self, raw_records: Iterable[Tuple[int, Dict[str, Any]]]):
        for offset, record in raw_records:
            norm_record: Dict[str, Any] = {}
            dp = s_datapath.initelem(record)
            pvs = []
            for prop, idx in self._meta.ActiveIndices():
                try:
                    field = dp.value(idx.datapath)
                    if field is None:
                        logger.info('indexing: offset %d yielded no value in indexing %s', offset, prop)
                        continue
                    # FIXME: what to do with subprops?
                    norm_record[prop], _ = s_datamodel.getTypeNorm(idx.syntype, field)
                except s_exc.NoSuchType:
                    logger.exception('missing type: %s', idx.syntype)
                    continue
                pvs.append((prop, idx.ver))
            if len(pvs):
                yield pvs, offset, norm_record

    def _writeIndices(self, rows: Iterable[Tuple[List[Tuple[str, int]], int, Dict[str, Union[str, int]]]]):
        with self._dbenv.begin(db=self._idxtbl, buffers=True, write=True) as txn:
            for pvs, offset, norm_record in rows:
                offset_enc = BE_UINT_ST.pack(offset)
                txn.put(offset_enc, s_msgpack.en(norm_record), db=self._normtbl)
                writes = ((s_msgpack.en((v, p)) + s_lmdb.encodeValAsKey(norm_record[p]), offset_enc) for p, v in pvs)
                txn.putmulti(writes)

    def _loop(self):
        busy = True

        while True:
            # Run the outstanding commands
            for job in self._boss:
                self._boss._runJob(job)
            if self._going_down.is_set():
                break
            if self._need_to_parse_meta:
                self._parse_index_meta()

            # loop_start_t = time.time()
            record_tuples = self.cryotank.rows(self._next_offset, self._chunk_sz)
            if record_tuples is not None:
                index_rows = self._normalize_records(record_tuples)
                self._next_offset = self._writeIndices(index_rows) + 1
                self.meta.updateProgress(self, self._next_offset)
            self._removeSome()
            if record_tuples is None and not self._am_deleting_indices:
                if busy is True:
                    logger.info('Completely caught up with indexing')
                    busy = False
                self._going_down.wait(self.MAX_WAIT_S)
                continue
            else:
                busy = True
            # loop_end_t = loop_start_t + self.MAX_WAIT_S

    def _inWorker(callback):
        '''
        Gives the decorated function to the boss to run in his thread.

        (Just like inpool for the worker)
        '''
        def wrap(self, *args, **kwargs):
            task = s_async.newtask(callback, args, kwargs)
            job = self._boss.initJob(task)
            return job.sync(self.MAX_WAIT_S)
        return wrap

    @_inWorker
    def addIndex(self, prop, syntype, datapath):
        return self.metaIndex.addIndex(prop, syntype, datapath)

    @_inWorker
    def delIndex(self, prop):
        return self.metaIndex.delIndex(prop)

    @_inWorker
    def resumeIndex(self, prop):
        # FIXME
        pass

    @_inWorker
    def suspendIndex(self, prop):
        # FIXME
        pass

    # ???: do we care about remote chance of hash collisions (with first 128-bytes identical?)

    def rowsByPropVal(self, prop: str, valu: Optional[Union[int, str]]=None, *,
                      retoffset=True, retraw=False, retnorm=True, exact=False) -> Iterable[Tuple[Any, ...]]:
        ''' N.B. ordering of the parts of string values after the first UTF-8-encoded 128 bytes are arbitrary. '''
        if not any((retraw, retnorm, retoffset)):
            raise ValueError('At least one of retRaw, retNorm, retOffset must be True')

        propver = self._meta.latestIndexVersion(prop)
        if propver is None:
            raise ValueError("%s isn't being indexed")

        propenc = s_msgpack.en((propver, prop))

        is_large = valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE
        if is_large and exact:
            key = propenc + s_lmdb.encodeValAsKey(valu)
        elif valu is None:
            key = propenc
        else:
            key = propenc + s_lmdb.encodeValAsKey(valu)[:s_lmdb.LARGE_STRING_SIZE]
        with self._dbenv.begin(db=self._idxtbl, buffers=True) as txn, txn.cursor() as curs:
            if exact:
                rv = curs.set_key(key)
            else:
                rv = curs.set_range(key)
            if not rv:
                return
            while True:
                rv = []
                offset_enc = curs.value()
                offset = BE_UINT_ST.unpack(offset_enc)
                if retoffset:
                    rv.append(offset)
                if retraw:
                    _, raw = next(self.cryotank.rows(offset, 1))
                    rv.append(raw)
                if retnorm:
                    norm_enc = txn.get(offset_enc, db=self._normtbl)
                    if norm_enc is None:
                        return
                    norm = s_msgpack.un(norm_enc)
                    rv.append(norm)
                yield tuple(rv)

    def fini(self):
        self._going_down.set()
        self.join(self.MAX_WAIT_S + 1)

        del self.cryotank
