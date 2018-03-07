import os
import struct
import logging
# import threading
from collections import namedtuple, defaultdict
from typing import List, Dict, Union, Iterable, Tuple, Any, Optional  # NOQA

import lmdb  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.synasync as s_async
import synapse.lib.const as s_const
import synapse.cryotank as s_cryotank
import synapse.datamodel as s_datamodel
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads
import synapse.lib.datapath as s_datapath
import synapse.lib.lmdb as s_lmdb

logger = logging.getLogger(__name__)

# Cryotank indexing.  This implements a lazy indexer that indexes a cryotank in a separate thread.
#
# Cryotank entries are json-compatible dictionaries with arbitrary nestign.  An index consists of a property name, a
# datapath (a specified portion of the entry), and a synapse type.   The type specifies the function that normalizes
# the output of the datapath query into a string or integer.

# Indices can be added and deleted asynchronously from the indexing thread via CryotankIndexer.addIndex and
# CryotankIndexer.delIndex.

# Indexes can be queried with rowsByPropVal.


# To harmonize with LMDB requirements, writing only occurs on the worker thread, while reading indices takes
# place in the caller's thread.  Both reading and writing index metadata (that is, information about which indices
# are running) take place on the worker's thread.

# N.B. The indexer cannot realistically detect when a type has changed from underneath itself.   Operators must
# explicitly delete and re-add the index to avoid mixed normalized data.

# ----
# TODO: could index faster if ingest/normalize is separate thread from writing
# TODO:  what to do with subprops returned from getTypeNorm
# TODO:  need a way to specify/load custom types

# FIXME: filter retrieved data by active props
# FIXME: add multiple datapaths
# FIXME: improve datapath perf by precompile
# FIXME: add to progress stats on successful rows, norm failures
# FIXME: suspend/resume individual/all indices

# Describes a single index in the system.
_MetaEntry = namedtuple('_MetaEntry', ('id', 'syntype', 'datapath', 'awake'))

class _IndexMeta:
    '''
    Manages persistence of index metadata with an in-memory copy

    "Schema":
    b'indices' key has msgpack encoded dict of
    { 'present': [8238483: {'propname': 'foo:bar', 'syntype': type, 'datapath': datapath}, ...],
      'deleting': [8238483, ...]
    }
    b'progress' key has mesgpack encoded dict of
    { 8328483: {nextoffset, ngood, nnormfail}, ...

    _present_ contains the encoding information about the current indices
    _deleting_ contains the indices currently being deleted (but aren't done)
    _progress_ contains how far each index has gotten, how many sucessful props were indexed (which might be different
    because of missing properties), and how many normalizations failed and is separate because it gets updated a lot
    more

    '''

    def __init__(self, dbenv: lmdb.Environment) -> None:
        self._dbenv = dbenv
        self._metatbl = dbenv.open_db(b'meta')
        with dbenv.begin(db=self._metatbl, buffers=True) as txn:
            indices_enc = txn.get(b'indices')
            progress_enc = txn.get(b'progress')
        if indices_enc is None or progress_enc is None:
            if indices_enc is None and progress_enc is None:
                is_new_db = True
                indices_enc = s_msgpack.en({'present': {}, 'deleting': {}})
                progress_enc = s_msgpack.en({})
            else:
                raise s_exc.CorruptDatabase('missing meta information in index meta')
        indices = s_msgpack.un(indices_enc)
        self._meta_table = self._dbenv.open_db(b'meta')
        self._indices = {k: _MetaEntry(**v) for k, v in indices.get('present', ())}
        self.deleting = indices.get('deleting', ())

        self.progresses = defaultdict(s_msgpack.un(progress_enc), lambda: {'nextoffset': 0, 'ngood': 0, 'nnormfail': 0})  # type: ignore  # NOQA
        if not all(p in self._indices for p in self.deleting):
            raise s_exc.CorruptDatabase('index meta table: deleting entry with unrecognized property name')
        if not all(p in self._indices for p in self.progresses):
            raise s_exc.CorruptDatabase('index meta table: progress entry with unrecognized property name')
        if is_new_db:
            self.persist()

    def persist(self, progressonly=False) -> None:
        '''
        Persists the index info
        '''
        d = {'delete': self.deleting,
             'present': {k: v._asdict() for k, v in self._indices.items()}}

        with self._dbenv.begin(db=self._metatbl, buffers=True, write=True) as txn:
            if not progressonly:
                txn.put(b'indices', s_msgpack.en(d))
            txn.put(b'progress', s_msgpack.en(self.progresses))

    # def updateProgress(self, nextoff: int) -> None:
    #     '''
    #     Update in memory frequently-changed progress (i.e. one after the last offset an index has
    #     gotten.
    #     '''
    #     for p in self._progresses:
    #         if self._indices[p].awake:
    #             self._progresses[p]. = max(self._progresses[p], nextoff)

    def lowestProgress(self) -> int:
        return min(p['nextoffset'] for p in self.progresses.values()) if self.progresses else s_lmdb.MAX_INT_VAL

    def iidFromProp(self, prop):
        '''
        Returns the index id for the propname, None if not found
        '''
        return next((k for k, idx in self._indices if idx.propname == prop), None)

    def addIndex(self, prop: str, syntype: str, datapath: str) -> None:
        if self.iidFromProp(prop) is not None:
            raise s_exc.IndexAlreadyPresent

        s_datamodel.tlib.reqDataType(syntype)
        iid = int.from_bytes(os.urandom(8), 'little')
        self._indices[prop] = _MetaEntry(id=iid, syntype=syntype, datapath=datapath, awake=True)
        self.persist()

    def delIndex(self, prop: str) -> None:
        iid = self.iidFromProp(prop)
        if iid is None:
            raise s_exc.IndexNotPresent
        del self._indices[iid]
        self.deleting.add(iid)

        # remove the progress entry in case a new index with the same propname gets added later
        del self.progresses[iid]
        self.persist()

    def markDeleteComplete(self, iid: int) -> None:
        del self.deleting[iid]
        self.persist()

    def activeIndices(self) -> Iterable[Tuple[str, _MetaEntry]]:
        return ((k, self._indices[k]) for k in sorted(self._indices) if self._indices[k].awake)


int64le = struct.Struct('<Q')
def _iid_en(iid):
    return int64le.pack(iid)

def _iid_un(iid):
    return int64le.pack(iid)

class CryoTankIndexer:
    '''
    Manages indexing of a single cryotank's records
    '''
    MAX_WAIT_S = 10

    def __init__(self, cryotank):
        self.cryotank = cryotank
        ebus = cryotank
        self._going_down = False
        self._worker = s_threads.Thread(ebus)
        path = s_common.gendir(cryotank.path, 'cryo_index.lmdb')
        cryotank_map_size = cryotank.lmdb.info()['map_size']
        self._dbenv = lmdb.open(path, writemap=True, metasync=False, max_readers=2, max_dbs=4,
                                map_size=cryotank_map_size)
        s_lmdb.ensureMapSlack(self._dbenv, s_const.gibibyte)
        # iid, v -> offset table
        self._idxtbl = self._dbenv.open_db(b'indices', dupsort=True)
        # offset, iid -> normalized prop
        self._normtbl = self._dbenv.open_db(b'norms')
        self._to_delete = {}  # type: Dict[str, int]
        self._boss = s_async.Boss()
        # A dict of propname -> version, type, datapath dict
        self._meta = _IndexMeta(self._dbenv)
        self._next_offset = self._meta.lowestProgress()
        self._chunk_sz = 1000  # < How many records to read at a time
        self._worker.run(self._workerloop)
        self._remove_chunk_sz = 1000  # < How many index entries to remove at a time

        def fini():
            self._boss.fini()
            self._worker.join(self.MAX_WAIT_S)

        ebus.onfini(fini)

    def _removeSome(self) -> None:
        # Make some progress on removing deleted indices
        left = self._remove_chunk_sz
        for iid in self._meta.deleting:
            if not left:
                break
            iid_enc = _iid_en(iid)
            with self._dbenv.begin(db=self._idxtbl, buffers=True, write=True) as txn, txn.cursor() as curs:
                if curs.set_range(iid_enc):
                    for k, offset_enc in curs.iternext():
                        if k[:len(iid_enc)] != iid_enc:
                            break
                        if not curs.delete():
                            raise s_exc.CorruptDatabase('delete failure')

                        txn.delete(offset_enc, iid_enc, db=self._normtbl)
                        left -= 1
                        if not left:
                            break
                if not left:
                    break

            self._meta.markDeleteComplete(iid)

    def _normalize_records(self, raw_records: Iterable[Tuple[int, Dict[int, str]]]) -> \
            Iterable[Tuple[int, int, Union[str, int]]]:
        '''
        Yields a stream of normalized fields
        '''
        for offset, record in raw_records:
            dp = s_datapath.initelem(record)

            for iid, idx in self._meta.activeIndices():
                if self._meta.progress[iid]['nextoffset'] > offset:
                    continue
                try:
                    self._meta.progress[iid]['nextoffset'] = offset + 1
                    field = dp.value(idx.datapath)
                    if field is None:
                        continue
                    # TODO : what to do with subprops?
                    normprop, _ = s_datamodel.getTypeNorm(idx.syntype, field)
                except (s_exc.NoSuchType, s_exc.BadTypeValu):
                    logger.exception('', idx.syntype)
                    self._meta.progress[iid]['nsuc'] += 1
                    continue
                self._meta.progress[iid]['ngood'] += 1
                yield offset, iid, normprop

    def _writeIndices(self, rows: Iterable[Tuple[int, int, Union[str, int]]]) -> None:
        with self._dbenv.begin(db=self._idxtbl, buffers=True, write=True) as txn:

            for offset, iid, normprop in rows:

                offset_enc = s_cryotank.int64be.pack(offset)
                iid_enc = _iid_en(iid)
                normprop_enc = s_lmdb.encodeValAsKey(normprop)

                txn.put(iid_enc + normprop_enc, offset_enc)
                txn.put(offset_enc + iid_enc, normprop_enc, db=self._normtbl)

            self._meta.persist(progressonly=True, txn=txn)

    def _workerloop(self):
        busy = True
        waiter = self.cryotank(1, 'job:init', 'job:done')

        while True:
            # Run the outstanding commands
            for job in self._boss:
                self._boss._runJob(job)
            if self._going_down:
                break

            # loop_start_t = time.time()
            record_tuples = self.cryotank.rows(self._next_offset, self._chunk_sz)
            if record_tuples is not None:
                norm_gen = self._normalize_records(record_tuples)
            self._writeIndices(norm_gen)

            self._removeSome()
            if record_tuples is None and not self._meta.deleting:
                if busy is True:
                    logger.info('Completely caught up with indexing')
                    busy = False
                if not busy:
                    waiter.wait(timeout=self.MAX_WAIT_S)
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
        return self._meta.addIndex(prop, syntype, datapath)

    @_inWorker
    def delIndex(self, prop):
        return self._meta.delIndex(prop)

    @_inWorker
    def resumeIndex(self, prop):
        # FIXME
        pass

    @_inWorker
    def suspendIndex(self, prop):
        # FIXME
        pass

    def _getnorm(self, offset_enc: bytes, txn: lmdb.Transaction) -> Dict[str, Union[str, int]]:
        '''
        Retrieves all the normalized fields for an offset
        '''
        norm: Dict[str, Union[int, str]] = {}
        olen = len(offset_enc)
        with txn.cursor(db=self._normtbl) as curs:
            if not curs.set_range(offset_enc):
                logger.warning('Missing normalized fields')
                return norm
            while True:
                curkey, norm_enc = curs.item()
                if curkey[:olen] != offset_enc:
                    break
                iid = _iid_un(curkey[olen:])
                # this is racy with the worker, but it is still safe
                idx = self._meta.indices.get(iid)
                if idx is None:
                    # Could be a deleted index
                    continue
                norm[idx.propname] = s_msgpack.un(norm_enc)
        return norm

    def rowsByPropVal(self, prop: str, valu: Optional[Union[int, str]]=None, *,
                      retoffset=True, retraw=False, retnorm=True, exact=False) -> Iterable[Tuple[Any, ...]]:
        '''
        Query against an index.

        Args;
            prop:  The name of the indexed property
            valu:  The value.  If not present, all records with prop present, sorted by prop will be returned.
            If valu is a string, it may be a prefix.
            retoffset: Includes the cryotank offset in the returned tuples
            retraw: Includes the cryotank entry in the returned tuples
            retnorm: Includes a dictionary of all the indexed properties and normalized values in the return tuples
            exact: The result must match exactly

        Returns:
            A iterable of tuples of the requested entries.

        N.B. ordering of the parts of string values after the first UTF-8-encoded 128 bytes are arbitrary.
        '''
        if not any((retraw, retnorm, retoffset)):
            raise ValueError('At least one of retRaw, retNorm, retOffset must be True')

        iid = self._meta.iidFromProp(prop)
        if iid is None:
            raise ValueError("%s isn't being indexed")
        iidenc = _iid_en(iid)

        islarge = valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE
        # Unless we're looking for an exist
        if islarge and exact:
            key = iidenc + s_lmdb.encodeValAsKey(valu)
        elif valu is None:
            key = iidenc
        else:
            key = iidenc + s_lmdb.encodeValAsKey(valu)[:s_lmdb.LARGE_STRING_SIZE]
        with self._dbenv.begin(db=self._idxtbl, buffers=True) as txn, txn.cursor() as curs:
            if exact:
                rv = curs.set_key(key)
            else:
                rv = curs.set_range(key)
            if not rv:
                return
            while True:
                rv = []
                curkey, offset_enc = curs.item()
                if (not exact and not curkey[:len(key)] == key) or (exact and curkey == key):
                    return
                offset = s_cryotank.int64be.unpack(offset_enc)
                if retoffset:
                    rv.append(offset)
                if retraw:
                    _, raw = next(self.cryotank.rows(offset, 1))
                    rv.append(raw)
                if retnorm:
                    rv.append(self._getnorm(offset_enc, txn))
                yield tuple(rv)
                if not curs.next():
                    return

    def fini(self):
        self._going_down.set()
