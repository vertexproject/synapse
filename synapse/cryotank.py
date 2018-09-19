import os
import shutil
import struct
import logging
import threading
import contextlib
from functools import wraps
from collections import defaultdict
from typing import Iterable, Optional, Union, Tuple, Dict

import lmdb  # type: ignore

import synapse.glob as s_glob

import synapse.lib.kv as s_kv
import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.queue as s_queue
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads
import synapse.lib.datapath as s_datapath

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.datamodel as s_datamodel

logger = logging.getLogger(__name__)

class TankApi(s_cell.CellApi):

    def slice(self, size, offs, iden=None):
        yield from self.cell.slice(size, offs, iden=iden)

    def puts(self, items, seqn=None):
        return self.cell.puts(items, seqn=seqn)

    def metrics(self, offs, size=None):
        yield from self.cell.metrics(offs, size=size)

    def offset(self, iden):
        return self.cell.getOffset(iden)

    def addIndex(self, prop, syntype, datapaths):
        '''
        Add an index to the cryotank

        Args:
            prop (str):  the name of the property this will be stored as in the normalized record
            syntype (str):  the synapse type this will be interpreted as
            datapaths(Iterable[str]):  datapath specs against which the raw record is run to extract a single field
                that is passed to the type normalizer.  These will be tried in order until one succeeds.  At least one
                must be present.
        Returns:
            None
        Note:
            Additional datapaths will only be tried if prior datapaths are not present, and *not* if
            the normalization fails.
        '''
        return self.cell.indexer.addIndex(prop, syntype, datapaths)

    def delIndex(self, prop):
        '''
        Delete an index

        Args:
            prop (str): the (normalized) property name
        Returns:
            None
        '''
        return self.cell.indexer.delIndex(prop)

    def pauseIndex(self, prop=None):
        '''
        Temporarily stop indexing one or all indices

        Args:
            prop: (Optional[str]):  the index to stop indexing, or if None, indicate to stop all indices
        Returns:
            None
        Note:
            Pausing is not persistent.  Restarting the process will resume indexing.
        '''
        return self.cell.indexer.pauseIndex(prop)

    def resumeIndex(self, prop=None):
        '''
        Undo a pauseIndex

        Args:
            prop (Optional[str]):  the index to start indexing, or if None, indicate to resume all indices
        Returns:
            None
        '''
        return self.cell.indexer.resumeIndex(prop=prop)

    def getIndices(self):
        '''
        Get information about all the indices

        Args:
            None
        Returns:
            List[Dict[str: Any]]: all the indices with progress and statistics
        '''
        if self.cell.indexer is None:
            return []
        return self.cell.indexer.getIndices()

    def queryNormValu(self, prop, valu=None, exact=False):
        '''
        Query for normalized individual property values

        Args:
            name (str):  name of the Cryotank
            prop (str):  The name of the indexed property
            valu (Optional[Union[int, str]]):  The normalized value.  If not present, all records with prop present,
            sorted by prop will be returned.  It will be considered a prefix if exact is False.
            exact (bool): Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            Iterable[Tuple[int, Union[str, int]]]:  A generator of offset, normalized value tuples.
        '''
        yield from self.cell.indexer.queryNormValu(prop, valu, exact)

    def queryNormRecords(self, prop, valu=None, exact=False):
        '''
        Query for normalized property values grouped together in dicts

        Args:
            name (str):  name of the Cryotank
            prop (str):  The name of the indexed property
            valu (Optional[Union[int, str]]):  The normalized value.  If not present, all records with prop present,
            sorted by prop will be returned.  It will be considered a prefix if exact is False.
            exact (bool): Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            Iterable[Tuple[int, Dict[str, Union[str, int]]]]: A generator of offset, dictionary tuples
        '''
        yield from self.cell.indexer.queryNormRecords(prop, valu, exact)

    def queryRows(self, prop, valu=None, exact=False):
        '''
        Query for raw (i.e. from the cryotank itself) records

        Args:
            name (str):  name of the Cryotank
            prop (str):  The name of the indexed property
            valu (Optional[Union[int, str]]):  The normalized value.  If not present, all records with prop present,
            sorted by prop will be returned.  It will be considered a prefix if exact is False.
            exact (bool): Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            Iterable[Tuple[int, bytes]]: A generator of tuple (offset, messagepack encoded) raw records
        '''
        yield from self.cell.indexer.queryRows(prop, valu, exact)

class CryoTank(s_cell.Cell):
    '''
    A CryoTank implements a stream of structured data.
    '''
    cellapi = TankApi

    confdefs = (
        ('mapsize', {'type': 'int', 'doc': 'LMDB mapsize value', 'defval': s_lmdb.DEFAULT_MAP_SIZE}),
        ('noindex', {'type': 'bool', 'doc': 'Disable indexing', 'defval': 0}),
    )

    def __init__(self, dirn: str, conf=None) -> None:

        s_cell.Cell.__init__(self, dirn)

        if conf is not None:
            self.conf.update(conf)

        path = s_common.gendir(self.dirn, 'tank.lmdb')

        mapsize = self.conf.get('mapsize')

        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.lenv_items = self.lenv.open_db(b'items')
        self.lenv_metrics = self.lenv.open_db(b'metrics')

        offsdb = self.lenv.open_db(b'offsets')
        self.offs = s_lmdb.Offs(self.lenv, offsdb)

        noindex = self.conf.get('noindex')
        self.indexer = None if noindex else CryoTankIndexer(self)

        with self.lenv.begin() as xact:
            self.items_indx = xact.stat(self.lenv_items)['entries']
            self.metrics_indx = xact.stat(self.lenv_metrics)['entries']

        def fini():
            self.lenv.close()

        self.onfini(fini)

    def getOffset(self, iden):
        return self.offs.get(iden)

    def setOffset(self, iden, offs):
        return self.offs.set(iden, offs)

    def last(self):
        '''
        Return the last item stored in this CryoTank.
        '''
        with self.lenv.begin() as xact:

            with xact.cursor(db=self.lenv_items) as curs:

                if not curs.last():
                    return None

                indx = struct.unpack('>Q', curs.key())[0]
                return indx, s_msgpack.un(curs.value())

    def puts(self, items, seqn=None):
        '''
        Add the structured data from items to the CryoTank.

        Args:
            items (list):  A list of objects to store in the CryoTank.
            seqn (iden, offs): An iden / offset pair to record.

        Returns:
            int: The ending offset of the items or seqn.
        '''
        itembyts = [s_msgpack.en(i) for i in items]

        tick = s_common.now()
        bytesize = sum([len(b) for b in itembyts])

        with self.lenv.begin(db=self.lenv_items, write=True) as xact:

            todo = []
            for byts in itembyts:
                todo.append((struct.pack('>Q', self.items_indx), byts))
                self.items_indx += 1

            retn = self.items_indx

            with xact.cursor() as curs:
                curs.putmulti(todo, append=True)

            took = s_common.now() - tick

            with xact.cursor(db=self.lenv_metrics) as curs:

                lkey = struct.pack('>Q', self.metrics_indx)
                self.metrics_indx += 1

                info = {'time': tick, 'count': len(items), 'size': bytesize, 'took': took}
                curs.put(lkey, s_msgpack.en(info), append=True)

            if seqn is not None:
                iden, offset = seqn
                nextoff = offset + len(items)
                self.offs.xset(xact, iden, nextoff)
                retn = nextoff

        self.fire('cryotank:puts', numrecords=len(itembyts))

        return retn

    def metrics(self, offs, size=None):
        '''
        Yield metrics rows starting at offset.

        Args:
            offs (int): The index offset.
            size (int): The maximum number of records to yield.

        Yields:
            ((int, dict)): An index offset, info tuple for metrics.
        '''
        mink = struct.pack('>Q', offs)

        with self.lenv.begin() as xact:

            with xact.cursor(db=self.lenv_metrics) as curs:

                if not curs.set_range(mink):
                    return

                for i, (lkey, lval) in enumerate(curs):

                    if size is not None and i >= size:
                        return

                    indx = struct.unpack('>Q', lkey)[0]
                    item = s_msgpack.un(lval)

                    yield indx, item

    def slice(self, offs, size, iden=None):
        '''
        Yield a number of items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Notes:
            This API performs msgpack unpacking on the bytes, and could be
            slow to call remotely.

        Yields:
            ((index, object)): Index and item values.
        '''
        lmin = struct.pack('>Q', offs)

        if iden is not None:
            self.setOffset(iden, offs)

        with self.lenv.begin() as xact:

            with xact.cursor(db=self.lenv_items) as curs:

                if not curs.set_range(lmin):
                    return

                for i, (lkey, lval) in enumerate(curs):

                    if i >= size:
                        return

                    indx = struct.unpack('>Q', lkey)[0]
                    yield indx, s_msgpack.un(lval)

    def rows(self, offs, size, iden=None):
        '''
        Yield a number of raw items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            ((indx, bytes)): Index and msgpacked bytes.
        '''
        lmin = struct.pack('>Q', offs)
        imax = offs + size

        if iden is not None:
            self.setOffset(iden, offs)

        # time slice the items from the cryo tank
        with self.lenv.begin() as xact:

            with xact.cursor(db=self.lenv_items) as curs:

                if not curs.set_range(lmin):
                    return

                for lkey, lval in curs:

                    indx = struct.unpack('>Q', lkey)[0]
                    if indx >= imax:
                        break

                    yield indx, lval

    def info(self):
        '''
        Returns information about the CryoTank instance.

        Returns:
            dict: A dict containing items and metrics indexes.
        '''
        with self.lenv.begin(db=self.lenv_items) as xact:
            dbstat = xact.stat()
        return {'indx': self.items_indx, 'metrics': self.metrics_indx, 'stat': dbstat}

class CryoApi(s_cell.CellApi):
    '''
    The CryoCell API as seen by a telepath proxy.

    This is the API to reference for remote CryoCell use.
    '''
    async def init(self, name, conf=None):
        await self.cell.init(name, conf=conf)
        return True

    async def slice(self, name, offs, size, iden=None):
        tank = await self.cell.init(name)
        async for item in tank.slice(offs, size, iden=iden):
            yield item

    def list(self):
        return self.cell.list()

    async def last(self, name):
        tank = await self.cell.init(name)
        return tank.last()

    async def puts(self, name, items, seqn=None):
        tank = await self.cell.init(name)
        return tank.puts(items, seqn=seqn)

    async def offset(self, name, iden):
        tank = await self.cell.init(name)
        return tank.getOffset(iden)

    async def rows(self, name, offs, size, iden=None):
        tank = await self.cell.init(name)
        async for item in tank.rows(offs, size, iden=iden):
            yield item

    async def metrics(self, name, offs, size=None):
        tank = await self.cell.init(name)
        async for item in tank.metrics(offs, size=size):
            yield item

    @s_cell.adminapi
    def delete(self, name):
        return self.cell.delete(name)

class CryoCell(s_cell.Cell):

    cellapi = CryoApi

    confdefs = (
        ('tankdefaults', {'defval': {},
                          'doc': 'Default config over-rides for a new tank.'}),
    )

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        path = s_common.gendir(self.dirn, 'cryo.lmdb')

        self.dmon = None
        self.sharename = None

        self.kvstor = s_kv.KvStor(path)
        self.onfini(self.kvstor.fini)

        self.names = self.kvstor.getKvDict('cryo:names')
        self.confs = self.kvstor.getKvDict('cryo:confs')

        self.tanks = s_eventbus.BusRef()

        self.onfini(self.tanks.fini)

        for name, iden in self.names.items():

            logger.info('Bringing tank [%s][%s] online', name, iden)

            path = s_common.genpath(self.dirn, 'tanks', iden)

            conf = self.confs.get(name)
            tank = CryoTank(path, conf)
            self.tanks.put(name, tank)

    async def onTeleOpen(self, link, path):
        return await self.init(path[1])

    async def init(self, name, conf=None):
        '''
        Generate a new CryoTank with a given name or get an reference to an existing CryoTank.

        Args:
            name (str): Name of the CryoTank.

        Returns:
            CryoTank: A CryoTank instance.
        '''
        tank = self.tanks.get(name)
        if tank is not None:
            return tank

        iden = s_common.guid()

        logger.info('Creating new tank: %s', name)

        path = s_common.genpath(self.dirn, 'tanks', iden)

        mergeconf = self.conf.get('tankdefaults').copy()
        if conf is not None:
            mergeconf.update(conf)

        tank = await CryoTank.anit(path, mergeconf)

        self.names.set(name, iden)
        self.confs.set(name, conf)
        self.tanks.put(name, tank)

        return tank

    def list(self):
        '''
        Get a list of (name, info) tuples for the CryoTanks.

        Returns:
            list: A list of tufos.
        '''
        return [(name, tank.info()) for (name, tank) in self.tanks.items()]

    def delete(self, name):

        tank = self.tanks.pop(name)
        if tank is None:
            return False

        self.names.pop(name)

        tank.fini()
        shutil.rmtree(tank.dirn, ignore_errors=True)

        return True

# TODO: what to do with subprops returned from getTypeNorm

class _MetaEntry:
    ''' Describes a single CryoTank index in the system. '''
    def __init__(self, model: s_datamodel.Model, propname: str, syntype: str, datapaths: Iterable[str]) -> None:
        '''
        Makes a MetaEntry

        Args:
            propname: The name of the key in the normalized dictionary
            syntype: The synapse type name against which the data will be normalized
            datapath (Iterable[str]) One or more datapath strings that will be used to find the field in a raw record
        '''
        self.propname = propname
        self.syntype = model.type(syntype)
        self.datapaths = tuple(s_datapath.DataPath(d) for d in datapaths)

    def en(self):
        '''
        Encodes a MetaEntry for storage
        '''
        return s_msgpack.en(self.asdict())

    def asdict(self):
        '''
        Returns a MetaEntry as a dictionary
        '''
        return {'propname': self.propname,
                'syntype': self.syntype.name,
                'datapaths': tuple(d.path for d in self.datapaths)}

# Big-endian 64-bit integer encoder
_Int64be = struct.Struct('>Q')

class _IndexMeta:
    '''
    Manages persistence of CryoTank index metadata with an in-memory copy

    "Schema":
    b'indices' key has msgpack encoded dict of
    { 'present': [8238483: {'propname': 'foo:bar', 'syntype': type, 'datapaths': (datapath, datapath2)}, ...],
      'deleting': [8238483, ...]
    }
    b'progress' key has mesgpack encoded dict of
    { 8328483: {nextoffset, ngood, nnormfail}, ...

    _present_ contains the encoding information about the current indices
    _deleting_ contains the indices currently being deleted (but aren't done)
    _progress_ contains how far each index has gotten, how many successful props were indexed (which might be different
    because of missing properties), and how many normalizations failed.  It is separate because it gets updated a lot
    more.
    '''
    def __init__(self, model: s_datamodel.Model, dbenv: lmdb.Environment) -> None:
        '''
        Creates metadata for all the indices.

        Args:
            dbenv (lmdb.Environment): the lmdb instance in which to store the metadata.

        Returns:
            None
        '''
        self._dbenv = dbenv
        self.model = model

        # The table in the database file (N.B. in LMDB speak, this is called a database)
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
                raise s_exc.CorruptDatabase('missing meta information in index meta')  # pragma: no cover

        indices = s_msgpack.un(indices_enc)

        # The details about what the indices are actually indexing: the datapath and type.

        self.indices = {k: _MetaEntry(model, **s_msgpack.un(v)) for k, v in indices.get('present', {}).items()}
        self.deleting = list(indices.get('deleting', ()))
        # Keeps track (non-persistently) of which indices have been paused
        self.asleep = defaultdict(bool)  # type: ignore

        # How far each index has progressed as well as statistics
        self.progresses = s_msgpack.un(progress_enc)
        if not all(p in self.indices for p in self.deleting):
            raise s_exc.CorruptDatabase(
                'index meta table: deleting entry with unrecognized property name')  # pragma: no cover
        if not all(p in self.indices for p in self.progresses):
            raise s_exc.CorruptDatabase(
                'index meta table: progress entry with unrecognized property name')  # pragma: no cover
        if is_new_db:
            self.persist()

    def persist(self, progressonly=False, txn=None):
        '''
        Persists the index info to the database

        Args:
            progressonly (bool): if True, only persists the progress (i.e. more dynamic) information
            txn (Optional[lmdb.Transaction]): if not None, will use that transaction to record data.  txn is
            not committed.
        Returns:
            None
        '''
        d = {'delete': self.deleting,
             'present': {k: metaentry.en() for k, metaentry in self.indices.items()}}

        with contextlib.ExitStack() as stack:
            if txn is None:
                txn = stack.enter_context(self._dbenv.begin(db=self._metatbl, buffers=True, write=True))
            if not progressonly:
                txn.put(b'indices', s_msgpack.en(d), db=self._metatbl)
            txn.put(b'progress', s_msgpack.en(self.progresses), db=self._metatbl)

    def lowestProgress(self):
        '''
        Returns:
            int: The next offset that should be indexed, based on active indices.
        '''
        nextoffsets = [p['nextoffset'] for iid, p in self.progresses.items() if not self.asleep[iid]]
        return min(nextoffsets) if nextoffsets else s_lmdb.MAX_INT_VAL

    def iidFromProp(self, prop):
        '''
        Retrieve the random index ID from the property name

        Args:
            prop (str) The name of the indexed property
        Returns:
            int: the index id for the propname, None if not found
        '''
        return next((k for k, idx in self.indices.items() if idx.propname == prop), None)

    def addIndex(self, prop, syntype, datapaths):
        '''
        Add an index to the cryotank

        Args:
            prop (str):  the name of the property this will be stored as in the normalized record
            syntype (str):  the synapse type this will be interpreted as
            datapaths (Iterable[str]):  datapaths that will be tried in order.
        Returns:
            None
        Note:
            Additional datapaths will only be tried if prior datapaths are not present, and *not* if
            the normalization fails.
        '''
        if self.iidFromProp(prop) is not None:
            raise s_exc.DupIndx(mesg='Index already exists', index=prop)
        if not len(datapaths):
            raise s_exc.BadOperArg(mesg='datapaths must have at least one entry')

        if self.model.type(syntype) is None:
            raise s_exc.BadOperArg(mesg=f'unknown synapse type {syntype}')
        iid = int.from_bytes(os.urandom(8), 'little')
        self.indices[iid] = _MetaEntry(self.model, propname=prop, syntype=syntype, datapaths=datapaths)
        self.progresses[iid] = {'nextoffset': 0, 'ngood': 0, 'nnormfail': 0}
        self.persist()

    def delIndex(self, prop):
        '''
        Delete an index

        Args:
            prop (str): the (normalized) property name
        Returns:
            None
        '''
        iid = self.iidFromProp(prop)
        if iid is None:
            raise s_exc.NoSuchIndx(mesg='No such index', index=prop)
        del self.indices[iid]
        self.deleting.append(iid)

        # remove the progress entry in case a new index with the same propname gets added later
        del self.progresses[iid]
        self.persist()

    def pauseIndex(self, prop):
        '''
        Temporarily stop indexing one or all indices

        Args:
            prop: (Optional[str]):  the index to stop indexing, or if None, indicate to stop all indices
        Returns:
            None
        Note:
            Pausing is not persistent.  Restarting the process will resume indexing.
        '''
        for iid, idx in self.indices.items():
            if prop is None or prop == idx.propname:
                self.asleep[iid] = True

    def resumeIndex(self, prop):
        '''
        Undo a pauseIndex

        Args:
            prop (Optional[str]):  the index to start indexing, or if None, indicate to resume all indices
        Returns:
            None
        '''
        for iid, idx in self.indices.items():
            if prop is None or prop == idx.propname:
                self.asleep[iid] = False

    def markDeleteComplete(self, iid):
        '''
        Indicates that deletion of a single index is complete

        Args:
            iid (int):  The index ID to mark as deleted
        '''

        self.deleting.remove(iid)
        self.persist()

_Int64le = struct.Struct('<Q')

def _iid_en(iid):
    '''
    Encode a little endian 64-bit integer
    '''
    return _Int64le.pack(iid)

def _iid_un(iid):
    '''
    Decode a little endian 64-bit integer
    '''
    return _Int64le.unpack(iid)[0]

def _inWorker(callback):
    '''
    Queue the the decorated function to the indexing worker to run in his thread

    Args:
        callback: the function to wrap
    Returns:
        the wrapped function

    (Just like inpool for the worker)
    '''
    @wraps(callback)
    def wrap(self, *args, **kwargs):
        with s_threads.RetnWait() as retn:
            self._workq.put((retn, callback, (self, ) + args, kwargs))
            succ, rv = retn.wait(timeout=self.MAX_WAIT_S)
            if succ:
                if isinstance(rv, Exception):
                    raise rv
                return rv
            raise s_exc.TimeOut()

    return wrap

class CryoTankIndexer:
    '''
    Manages indexing of a single cryotank's records

    This implements a lazy indexer that indexes a cryotank in a separate thread.

    Cryotank entries are msgpack-encoded values.  An index consists of a property name, one or more datapaths (i.e.
    what field out of the entry), and a synapse type.   The type specifies the function that normalizes the output of
    the datapath query into a string or integer.

    Indices can be added and deleted asynchronously from the indexing thread via CryotankIndexer.addIndex and
    CryotankIndexer.delIndex.

    Indexes can be queried with queryNormValu, queryNormRecords, queryRows.

    To harmonize with LMDB requirements, writing only occurs on a singular indexing thread.  Reading indices takes
    place in the caller's thread.  Both reading and writing index metadata (that is, information about which indices
    are running) take place on the indexer's thread.

    Note:
        The indexer cannot detect when a type has changed from underneath itself.   Operators must explicitly delete
        and re-add the index to avoid mixed normalized data.
    '''
    MAX_WAIT_S = 10

    def __init__(self, cryotank: CryoTank) -> None:
        '''
        Create an indexer

        Args:
            cryotank: the cryotank to index
        Returns:
            None
        '''
        self.cryotank = cryotank
        ebus = cryotank
        self._worker = threading.Thread(target=self._workerloop, name='CryoTankIndexer')
        path = s_common.gendir(cryotank.dirn, 'cryo_index.lmdb')
        cryotank_map_size = cryotank.lenv.info()['map_size']
        self._dbenv = lmdb.open(path, writemap=True, metasync=False, max_readers=8, max_dbs=4,
                                map_size=cryotank_map_size)
        # iid, v -> offset table
        self._idxtbl = self._dbenv.open_db(b'indices', dupsort=True)
        # offset, iid -> normalized prop
        self._normtbl = self._dbenv.open_db(b'norms')
        self._to_delete = {}  # type: Dict[str, int]
        self._workq = s_queue.Queue()
        # A dict of propname -> MetaEntry
        self.model = s_datamodel.Model()
        self._meta = _IndexMeta(self.model, self._dbenv)
        self._next_offset = self._meta.lowestProgress()
        self._chunk_sz = 1000  # < How many records to read at a time
        self._remove_chunk_sz = 1000  # < How many index entries to remove at a time
        ebus.on('cryotank:puts', self._onData)

        self._worker.start()

        def _onfini():
            self._workq.done()
            self._worker.join(self.MAX_WAIT_S)
            self._dbenv.close()

        ebus.onfini(_onfini)

    def _onData(self, unused):
        '''
        Wake up the index worker if he already doesn't have a reason to be awake
        '''
        if 0 == len(self._workq):
            self._workq.put((None, lambda: None, None, None))

    def _removeSome(self):
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
                            raise s_exc.CorruptDatabase('delete failure')  # pragma: no cover

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
        Yield stream of normalized fields

        Args:
            raw_records:  generator of tuples of offset/decoded raw cryotank records
        Returns:
            generator of tuples of offset, index ID, normalized property value
        '''
        for offset, record in raw_records:
            self._next_offset = offset + 1
            dp = s_datapath.initelem(s_msgpack.un(record))

            for iid, idx in ((k, v) for k, v in self._meta.indices.items() if not self._meta.asleep[k]):
                if self._meta.progresses[iid]['nextoffset'] > offset:
                    continue
                try:
                    self._meta.progresses[iid]['nextoffset'] = offset + 1
                    for datapath in idx.datapaths:
                        field = dp.valu(datapath)
                        if field is None:
                            continue
                        # TODO : what to do with subprops?
                        break
                    else:
                        # logger.debug('Datapaths %s yield nothing for offset %d',
                        #              [d.path for d in idx.datapaths], offset)
                        continue
                    normval, _ = idx.syntype.norm(field)
                except (s_exc.NoSuchType, s_exc.BadTypeValu, ValueError):
                    # logger.debug('Norm fail', exc_info=True)
                    self._meta.progresses[iid]['nnormfail'] += 1
                    continue
                self._meta.progresses[iid]['ngood'] += 1
                yield offset, iid, normval

    def _writeIndices(self, rows):
        '''
        Persist actual indexing to disk

        Args:
            rows(Iterable[Tuple[int, int, Union[str, int]]]):  generators of tuples of offset, index ID, normalized
            property value

        Returns:
            int:  the next cryotank offset that should be indexed
        '''
        count = -1
        with self._dbenv.begin(db=self._idxtbl, buffers=True, write=True) as txn:
            for count, (offset, iid, normval) in enumerate(rows):

                offset_enc = _Int64be.pack(offset)
                iid_enc = _iid_en(iid)
                valkey_enc = s_lmdb.encodeValAsKey(normval)

                txn.put(iid_enc + valkey_enc, offset_enc)
                txn.put(offset_enc + iid_enc, s_msgpack.en(normval), db=self._normtbl)

            self._meta.persist(progressonly=True, txn=txn)
        return count + 1

    def _workerloop(self):
        '''
        Actually do the indexing

        Runs as separate thread.
        '''
        stillworktodo = True
        last_callback = 'None'

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
                            last_callback = callback.__name__
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
                # Recalculate the next offset to index, since we may have a new index
                self._next_offset = self._meta.lowestProgress()

            record_tuples = self.cryotank.rows(self._next_offset, self._chunk_sz)
            norm_gen = self._normalize_records(record_tuples)
            rowcount = self._writeIndices(norm_gen)

            self._removeSome()
            if not rowcount and not self._meta.deleting:
                if stillworktodo is True:
                    s_glob.plex.coroToTask(self.cryotank.fire('cryotank:indexer:noworkleft:' + last_callback))
                    last_callback = 'None'
                    stillworktodo = False
            else:
                stillworktodo = True

    @_inWorker
    def addIndex(self, prop, syntype, datapaths):
        '''
        Add an index to the cryotank

        Args:
            prop (str):  the name of the property this will be stored as in the normalized record
            syntype (str):  the synapse type this will be interpreted as
            datapaths(Iterable[str]):  datapath specs against which the raw record is run to extract a single field
                that is passed to the type normalizer.  These will be tried in order until one succeeds.  At least one
                must be present.
        Returns:
            None
        Note:
            Additional datapaths will only be tried if prior datapaths are not present, and *not* if
            the normalization fails.
        '''
        return self._meta.addIndex(prop, syntype, datapaths)

    @_inWorker
    def delIndex(self, prop):
        '''
        Delete an index

        Args:
            prop (str): the (normalized) property name
        Returns:
            None
        '''
        return self._meta.delIndex(prop)

    @_inWorker
    def pauseIndex(self, prop=None):
        '''
        Temporarily stop indexing one or all indices.

        Args:
            prop: (Optional[str]):  the index to stop indexing, or if None, indicate to stop all indices
        Returns:
            None
        Note:
            Pausing is not persistent.  Restarting the process will resume indexing.
        '''
        return self._meta.pauseIndex(prop)

    @_inWorker
    def resumeIndex(self, prop=None):
        '''
        Undo a pauseIndex

        Args:
            prop: (Optional[str]):  the index to start indexing, or if None, indicate to resume all indices
        Returns:
            None
        '''
        return self._meta.resumeIndex(prop)

    @_inWorker
    def getIndices(self):
        '''
        Get information about all the indices

        Args:
            None
        Returns:
            List[Dict[str: Any]]: all the indices with progress and statistics
        '''
        idxs = {iid: dict(metaentry.asdict()) for iid, metaentry in self._meta.indices.items()}
        for iid in idxs:
            idxs[iid].update(self._meta.progresses.get(iid, {}))
        return list(idxs.values())

    def _iterrows(self, prop, valu, exact=False):
        '''
        Query against an index.

        Args:
            prop (str):  The name of the indexed property
            valu (Optional[Union[int, str]]):  The normalized value.  If not present, all records with prop present,
            sorted by prop will be returned.  It will be considered prefix if exact is False.
            exact (bool): Indicates that the result must match exactly.  Conversly, if False, indicates a prefix match.

        Returns:
            Iterable[Tuple[int, bytes, bytes, lmdb.Transaction]: a generator of a Tuple of the offset, the encoded
            offset, the encoded index ID, and the LMDB read transaction.

        Note:
            Ordering of Tuples disregard everything after the first 128 bytes of a property.
        '''
        iid = self._meta.iidFromProp(prop)
        if iid is None:
            raise s_exc.NoSuchIndx(mesg='No such index', index=prop)
        iidenc = _iid_en(iid)

        islarge = valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE
        if islarge and not exact:
            raise s_exc.BadOperArg(mesg='prefix search valu cannot exceed 128 characters')

        if islarge and exact:
            key = iidenc + s_lmdb.encodeValAsKey(valu)
        elif valu is None:
            key = iidenc
        else:
            key = iidenc + s_lmdb.encodeValAsKey(valu, isprefix=not exact)
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
                offset = _Int64be.unpack(offset_enc)[0]
                yield (offset, offset_enc, iidenc, txn)
                if not curs.next():
                    return

    def queryNormValu(self, prop: str, valu: Optional[Union[int, str]] = None, exact=False):
        '''
        Query for normalized individual property values

        Args:
            prop:  The name of the indexed property
            valu:  The normalized value.  If not present, all records with prop present, sorted by prop will be
                returned.  It will be considered a prefix if exact is False.
            exact (bool): Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            A generator of offset, normalized value tuples
        '''
        if not exact and valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE:
            raise s_exc.BadOperArg(mesg='prefix search valu cannot exceed 128 characters')
        for (offset, offset_enc, iidenc, txn) in self._iterrows(prop, valu, exact):
            rv = txn.get(bytes(offset_enc) + iidenc, None, db=self._normtbl)
            if rv is None:
                raise s_exc.CorruptDatabase('Missing normalized record')  # pragma: no cover
            yield offset, s_msgpack.un(rv)

    def queryNormRecords(self, prop: str, valu: Optional[Union[int, str]] = None, exact=False) -> \
            Iterable[Tuple[int, Dict[str, Union[str, int]]]]:
        '''
        Query for normalized property values grouped together in dicts

        Args:
            prop:  The name of the indexed property
            valu:  The normalized value.  If not present, all records with prop present, sorted by prop will be
                returned.  It will be considered a prefix if exact is False.
            exact: Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            A generator of offset, dictionary tuples
        '''
        if not exact and valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE:
            raise s_exc.BadOperArg(mesg='prefix search valu cannot exceed 128 characters')
        for offset, offset_enc, _, txn in self._iterrows(prop, valu, exact):
            norm = {}
            olen = len(offset_enc)
            with txn.cursor(db=self._normtbl) as curs:
                if not curs.set_range(offset_enc):
                    raise s_exc.CorruptDatabase('Missing normalized record')  # pragma: no cover
                while True:
                    curkey, norm_enc = curs.item()
                    if curkey[:olen] != offset_enc:
                        break
                    iid = _iid_un(curkey[olen:])

                    # this is racy with the worker, but it is still safe
                    idx = self._meta.indices.get(iid)

                    if idx is not None:
                        norm[idx.propname] = s_msgpack.un(norm_enc)
                    if not curs.next():
                        break
            yield offset, norm

    def queryRows(self, prop: str, valu: Optional[Union[int, str]] = None, exact=False) -> Iterable[Tuple[int, bytes]]:
        '''
        Query for raw (i.e. from the cryotank itself) records

        Args:
            prop:  The name of the indexed property
            valu:  The normalized value.  If not present, all records with prop present,
            sorted by prop will be returned.  It will be considered a prefix if exact is False.
            exact: Indicates that the result must match exactly.  Conversely, if False, indicates a prefix match.

        Returns:
            Iterable[Tuple[int, bytes]]: A generator of tuple (offset, messagepack encoded) raw records
        '''
        if not exact and valu is not None and isinstance(valu, str) and len(valu) >= s_lmdb.LARGE_STRING_SIZE:
            raise s_exc.BadOperArg(mesg='prefix search valu cannot exceed 128 characters')
        for offset, _, _, txn in self._iterrows(prop, valu, exact):
            yield next(self.cryotank.rows(offset, 1))
