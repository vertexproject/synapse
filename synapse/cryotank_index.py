import os
import struct
import logging
import threading
import contextlib
from collections import namedtuple, defaultdict
from typing import List, Dict, Union, Iterable, Tuple, Any, Optional, DefaultDict  # NOQA

import lmdb  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.lmdb as s_lmdb
import synapse.lib.queue as s_queue
import synapse.datamodel as s_datamodel
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads
import synapse.lib.datapath as s_datapath

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Cryotank indexing.  This implements a lazy indexer that indexes a cryotank in a separate thread.
#
# Cryotank entries are msgpack-encoded json-compatible dictionaries with arbitrary nesting.  An index consists of a
# property name, a datapath (a specified portion of the entry), and a synapse type.   The type specifies the function
# that normalizes the output of the datapath query into a string or integer.

# Indices can be added and deleted asynchronously from the indexing thread via CryotankIndexer.addIndex and
# CryotankIndexer.delIndex.

# Indexes can be queried with rowsByPropVal.


# To harmonize with LMDB requirements, writing only occurs on the worker thread, while reading indices takes
# place in the caller's thread.  Both reading and writing index metadata (that is, information about which indices
# are running) take place on the worker's thread.

# N.B. The indexer cannot realistically detect when a type has changed from underneath itself.   Operators must
# explicitly delete and re-add the index to avoid mixed normalized data.

# ----
# TODO: could index faster maybe if ingest/normalize is separate thread from writing
# TODO:  what to do with subprops returned from getTypeNorm
# TODO:  need a way to specify/load custom types

# FIXME: improve datapath perf by precompile
# FIXME: rip out typing
# FIXME: move this file into cryotank.py

# Describes a single index in the system.
_MetaEntry = namedtuple('_MetaEntry', ('propname', 'syntype', 'datapath'))

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
        is_new_db = False
        with dbenv.begin(db=self._metatbl, buffers=True) as txn:
            indices_enc = txn.get(b'indices')
            progress_enc = txn.get(b'progress')
        if indices_enc is None or progress_enc is None:
            if indices_enc is None and progress_enc is None:
                is_new_db = True
                indices_enc = s_msgpack.en({'present': {}, 'deleting': []})
                progress_enc = s_msgpack.en({})
            else:
                raise s_exc.CorruptDatabase('missing meta information in index meta')
        indices = s_msgpack.un(indices_enc)
        self._meta_table = self._dbenv.open_db(b'meta')
        self.indices = {k: _MetaEntry(**v) for k, v in indices.get('present', {}).items()}
        self.deleting = list(indices.get('deleting', ()))
        self.asleep: DefaultDict[int, bool] = defaultdict(bool)

        self.progresses = s_msgpack.un(progress_enc)
        if not all(p in self.indices for p in self.deleting):
            raise s_exc.CorruptDatabase('index meta table: deleting entry with unrecognized property name')
        if not all(p in self.indices for p in self.progresses):
            raise s_exc.CorruptDatabase('index meta table: progress entry with unrecognized property name')
        if is_new_db:
            self.persist()

    def persist(self, progressonly=False, txn: Optional[lmdb.Transaction]=None) -> None:
        '''
        Persists the index info
        '''
        d = {'delete': self.deleting,
             'present': {k: v._asdict() for k, v in self.indices.items()}}

        with contextlib.ExitStack() as stack:
            if txn is None:
                txn = stack.enter_context(self._dbenv.begin(db=self._metatbl, buffers=True, write=True))
            if not progressonly:
                txn.put(b'indices', s_msgpack.en(d))
            txn.put(b'progress', s_msgpack.en(self.progresses))

    def lowestProgress(self) -> int:
        if self.progresses:
            return min(p['nextoffset'] for iid, p in self.progresses.items() if not self.asleep[iid])
        return s_lmdb.MAX_INT_VAL

    def iidFromProp(self, prop):
        '''
        Returns the index id for the propname, None if not found
        '''
        return next((k for k, idx in self.indices.items() if idx.propname == prop), None)

    def addIndex(self, prop: str, syntype: str, datapath: str, *args: str) -> None:
        '''
        Adds an index to the cryotank.

        Args:
        - datapath:  the datapath spec against which the raw record is run to extract a single field
        that is passed to the type normalizer.
        - *args:  additional datapaths that will be tried in order if the first isn't present.

        N.B.  additional datapaths will be tried iff the prior datapath is not present, and *not* if
        the normalization fails.

        '''
        if self.iidFromProp(prop) is not None:
            raise ValueError('index already added')

        s_datamodel.tlib.reqDataType(syntype)
        iid = int.from_bytes(os.urandom(8), 'little')
        self.indices[iid] = _MetaEntry(propname=prop, syntype=syntype, datapath=(datapath, *args))
        self.progresses[iid] = {'nextoffset': 0, 'ngood': 0, 'nnormfail': 0}
        self.persist()

    def delIndex(self, prop: str) -> None:
        iid = self.iidFromProp(prop)
        if iid is None:
            raise ValueError('Index not present')
        del self.indices[iid]
        self.deleting.append(iid)

        # remove the progress entry in case a new index with the same propname gets added later
        del self.progresses[iid]
        self.persist()

    def pauseIndex(self, prop: Optional[str]) -> None:
        for iid, idx in self.indices.items():
            if prop is None or prop == idx.propname:
                self.asleep[iid] = True

    def resumeIndex(self, prop: Optional[str]) -> None:
        for iid, idx in self.indices.items():
            if prop is None or prop == idx.propname:
                self.asleep[iid] = False

    def markDeleteComplete(self, iid: int) -> None:
        self.deleting.remove(iid)
        self.persist()

    def activeIndices(self) -> Iterable[Tuple[str, _MetaEntry]]:
        return ((k, self.indices[k]) for k in sorted(self.indices) if not self.asleep[k])


int64le = struct.Struct('<Q')
def _iid_en(iid):
    return int64le.pack(iid)

def _iid_un(iid):
    return int64le.unpack(iid)[0]

def _inWorker(callback):
    '''
    Gives the decorated function to the worker to run in his thread.

    (Just like inpool for the worker)
    '''
    def wrap(self, *args, **kwargs):
        with s_threads.RetnWait() as retn:
            self._workq.put((retn, callback, (self, ) + args, kwargs))
            succ, rv = retn.wait(timeout=self.MAX_WAIT_S)
            if succ:
                if isinstance(rv, Exception):
                    raise rv
                return rv
            raise s_exc.Timeout()

    return wrap

class CryoTankIndexer:
    '''
    Manages indexing of a single cryotank's records
    '''
    MAX_WAIT_S = 10

    def __init__(self, cryotank):
        self.cryotank = cryotank
        ebus = cryotank
        self._going_down = False
        self._worker = threading.Thread(target=self._workerloop, name='CryoTankIndexer')
        path = s_common.gendir(cryotank.path, 'cryo_index.lmdb')
        cryotank_map_size = cryotank.lmdb.info()['map_size']
        self._dbenv = lmdb.open(path, writemap=True, metasync=False, max_readers=2, max_dbs=4,
                                map_size=cryotank_map_size)
        # iid, v -> offset table
        self._idxtbl = self._dbenv.open_db(b'indices', dupsort=True)
        # offset, iid -> normalized prop
        self._normtbl = self._dbenv.open_db(b'norms')
        self._to_delete = {}  # type: Dict[str, int]
        self._workq = s_queue.Queue()
        # A dict of propname -> version, type, datapath dict
        self._meta = _IndexMeta(self._dbenv)
        self._next_offset = self._meta.lowestProgress()
        self._chunk_sz = 1000  # < How many records to read at a time
        self._remove_chunk_sz = 1000  # < How many index entries to remove at a time
        ebus.on('cryotank:puts', self._onData)

        self._worker.start()

        def _onfini():
            self._going_down = True
            self._workq.done()
            self._worker.join(self.MAX_WAIT_S)

        ebus.onfini(_onfini)

    def _onData(self, unused):
        '''
        Wake up the worker if he already doesn't have a reason to be awake
        '''
        if 0 == len(self._workq):
            self._workq.put((None, lambda: None, None, None))

    def _removeSome(self) -> None:
        '''
        Make some progress on removing deleted indices
        '''
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
        Yields stream of normalized fields
        '''
        for offset, record in raw_records:
            self._next_offset = offset + 1
            dp = s_datapath.initelem(s_msgpack.un(record))

            for iid, idx in self._meta.activeIndices():
                if self._meta.progresses[iid]['nextoffset'] > offset:
                    continue
                try:
                    self._meta.progresses[iid]['nextoffset'] = offset + 1
                    for datapath in idx.datapath:
                        field = dp.valu(datapath)
                        if field is None:
                            continue
                        # TODO : what to do with subprops?
                        break
                    else:
                        logger.debug('Datapaths %s yield nothing for offset %d', idx.datapath, offset)
                        continue
                    normval, _ = s_datamodel.getTypeNorm(idx.syntype, field)
                except (s_exc.NoSuchType, s_exc.BadTypeValu):
                    logger.debug('Norm fail')
                    self._meta.progresses[iid]['nnormfail'] += 1
                    continue
                self._meta.progresses[iid]['ngood'] += 1
                yield offset, iid, normval

    def _writeIndices(self, rows: Iterable[Tuple[int, int, Union[str, int]]]) -> int:
        count = -1
        with self._dbenv.begin(db=self._idxtbl, buffers=True, write=True) as txn:
            for count, (offset, iid, normval) in enumerate(rows):

                offset_enc = s_lmdb.int64be.pack(offset)
                iid_enc = _iid_en(iid)
                valkey_enc = s_lmdb.encodeValAsKey(normval)

                txn.put(iid_enc + valkey_enc, offset_enc)
                txn.put(offset_enc + iid_enc, s_msgpack.en(normval), db=self._normtbl)

            self._meta.persist(progressonly=True, txn=txn)
        return count + 1

    def _workerloop(self):
        stillworktodo = True

        while True:
            # Run the outstanding commands
            recalc = False
            while True:
                try:
                    job = self._workq.get(timeout=0 if stillworktodo else None)
                    stillworktodo = True
                    retn, callback, args, kwargs = job
                    try:
                        if retn is not None:
                            retn.retn(callback(*args, **kwargs))
                            recalc = True
                    except Exception as e:
                        if retn is None:
                            raise
                        else:
                            # Not using errx because I want the exception object itself
                            retn.retn(e)
                except s_exc.IsFini:
                    return
                except s_exc.TimeOut:
                    break
            if recalc:
                self._next_offset = self._meta.lowestProgress()

            # loop_start_t = time.time()
            import itertools
            record_tuples = self.cryotank.rows(self._next_offset, self._chunk_sz)
            rt_copy1, rt_copy2 = itertools.tee(record_tuples)
            # logger.debug('got: next_offset=%d, data=%s', self._next_offset, list(rt_copy1))
            norm_gen = self._normalize_records(rt_copy2)
            rowcount = self._writeIndices(norm_gen)

            self._removeSome()
            # logger.debug('Processed %d rows', rowcount)
            if not rowcount and not self._meta.deleting:
                if stillworktodo is True:
                    # logger.info('Completely caught up with indexing')
                    stillworktodo = False
            else:
                stillworktodo = True
            # loop_end_t = loop_start_t + self.MAX_WAIT_S

    @_inWorker
    def addIndex(self, prop: str, syntype: str, datapath: str, *args: str) -> None:
        return self._meta.addIndex(prop, syntype, datapath, args)

    @_inWorker
    def delIndex(self, prop: str) -> None:
        return self._meta.delIndex(prop)

    @_inWorker
    def resumeIndex(self, prop: Optional[str]=None) -> None:
        '''
        Unpauses a single index.  As a special case, setting prop to none will wake up all indexing.
        '''
        return self._meta.resumeIndex(prop)

    @_inWorker
    def pauseIndex(self, prop=None):
        return self._meta.pauseIndex(prop)

    @_inWorker
    def getIndices(self) -> List[Dict[str, Union[str, int]]]:
        idxs = {iid: dict(v._asdict()) for iid, v in self._meta.indices.items()}
        for iid in idxs:
            idxs[iid].update(self._meta.progresses.get(iid, {}))
        return list(idxs.values())

    def _iterrows(self, prop: str, valu: Optional[Union[int, str]], exact=False) -> Iterable[Tuple[Any, ...]]:
        '''
        Query against an index.

        Args;
            prop:  The name of the indexed property
            valu:  The value.  If not present, all records with prop present, sorted by prop will be returned.
            If valu is a string, it may be a prefix.
            exact: The result must match exactly

        Returns:
            A iterable of tuples of the requested entries.

        N.B. ordering of the parts of string values after the first UTF-8-encoded 128 bytes are arbitrary.
        '''
        iid = self._meta.iidFromProp(prop)
        if iid is None:
            raise ValueError("%s isn't being indexed")
        iidenc = _iid_en(iid)

        islarge = valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE
        if islarge and not exact:
            valu = valu[:s_lmdb.LARGE_STRING_SIZE]  # type: ignore

        if islarge and exact:
            key = iidenc + s_lmdb.encodeValAsKey(valu)
        elif valu is None:
            key = iidenc
        else:
            key = iidenc + s_lmdb.encodeValAsKey(valu, isprefix=True)
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
                if (not exact and not curkey[:len(key)] == key) or (exact and curkey != key):
                    return
                offset = s_lmdb.int64be.unpack(offset_enc)[0]
                yield (offset, offset_enc, iidenc, txn)
                if not curs.next():
                    return

    def normValuByPropVal(self, prop: str, valu: Optional[Union[int, str]]=None, exact=False) -> \
            Iterable[Tuple[int, Union[str, int]]]:
        for (offset, offset_enc, iidenc, txn) in self._iterrows(prop, valu, exact):
            rv = txn.get(bytes(offset_enc) + iidenc, None, db=self._normtbl)
            if rv is None:
                raise s_exc.CorruptDatabase('Missing normalized record')
            yield offset, s_msgpack.un(rv)

    def normRecordsByPropVal(self, prop: str, valu: Optional[Union[int, str]]=None, exact=False) -> \
            Iterable[Tuple[int, Dict[str, Union[str, int]]]]:
        '''
        Retrieves all the normalized fields for an offset
        '''
        for offset, offset_enc, _, txn in self._iterrows(prop, valu, exact):
            norm: Dict[str, Union[int, str]] = {}
            olen = len(offset_enc)
            with txn.cursor(db=self._normtbl) as curs:
                if not curs.set_range(offset_enc):
                    raise s_exc.CorruptDatabase('Missing normalized record')
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
                    if not curs.next():
                        break
            yield offset, norm

    def rawRecordsByPropVal(self, prop: str, valu: Optional[Union[int, str]]=None, exact=False) -> \
            Iterable[Tuple[int, bytes]]:
        for offset, _, _, txn in self._iterrows(prop, valu, exact):
            yield next(self.cryotank.rows(offset, 1))
