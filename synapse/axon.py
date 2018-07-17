import enum
import lmdb  # type: ignore
import asyncio
import binascii
import struct
import logging
import random
import hashlib
import tempfile
import itertools
import threading
import concurrent
import contextlib
import collections
from typing import List, Dict, Tuple, Optional

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

# File convention: buid -> unique id for a blobstor
CHUNK_SIZE = 16 * s_const.mebibyte


async def to_aiter(it):
    if hasattr(it, '__aiter__'):
        async for i in it:
            yield i
    else:
        for i in it:
            yield i

def _find_hash(curs, key):
    '''
    Returns false if key not present, else returns true and positions cursor at first chunk of value
    '''
    if not curs.set_range(key):
        return False
    return curs.key()[:len(key)] == key

class PassThroughApi(s_cell.CellApi):
    ''' Class that passes through methods made on it to its cell. '''
    allowed_methods: List[str] = []

    def __init__(self, cell, link):
        s_cell.CellApi.__init__(self, cell, link)

        for f in self.allowed_methods:
            # N.B. this curious double nesting is due to Python's closure mechanism (f is essentially captured by name)
            def funcapply(f):
                def func(*args, **kwargs):
                    return getattr(cell, f)(*args, **kwargs)
                return func
            setattr(self, f, funcapply(f))

class IncrementalTransaction(s_eventbus.EventBus):
    '''
    An lmdb write transaction that commits if the number of outstanding bytes to be commits grows too large.

    Naturally, this breaks transaction atomicity.
    '''
    MAX_OUTSTANDING = s_const.gibibyte

    def __init__(self, lenv):
        s_eventbus.EventBus.__init__(self)
        self.lenv = lenv
        self.txn = None
        self._bytecount = 0

        def fini():
            self.commit()
            # lmdb workaround:  close environment from here to avoid lmdb crash
            print('closing lenv', flush=True)
            self.lenv.close()

        self.onfini(fini)

    def commit(self):
        if self.txn is None:
            return
        self.txn.commit()
        self.txn = None
        self._bytecount = 0

    def guarantee(self):
        '''
        Make a real transaction if we don't have one
        '''
        if self.txn is None:
            self.txn = self.lenv.begin(write=True, buffers=True)
        return self.txn

    def cursor(self, db=None):
        self.guarantee()
        return self.txn.cursor(db)

    def __enter__(self):
        return self

    def __exit__(self, exc, cls, tb):
        self.commit()

    def put(self, key, value, db):
        vallen = len(value)
        if vallen + self._bytecount > self.MAX_OUTSTANDING:
            self.commit()
        self.guarantee()
        self._bytecount += vallen
        rv = self.txn.put(key, value, db=db)
        return rv

class Uploader(s_daemon.Share):
    typename = 'uploader'
    BUF_SIZE = 16 * s_const.mebibyte

    def __init__(self, link, item):
        s_daemon.Share.__init__(self, link, item)
        self.doneevent = asyncio.Event()
        self.exitok = False
        self.chunknum = 0
        self.wcid = self.item._makeclientid()
        self.result = None

        async def fini():
            self.result = await self.item._complete(self.wcid, wait_for_result=True)
            self.doneevent.set()

        self.onfini(fini)

    async def write(self, bytz):
        await self.item._partialsubmit(self.wcid, ((self.chunknum, bytz), ))
        self.chunknum += 1

    async def _runShareLoop(self):
        '''
        This keeps the object alive until we're fini'd.
        '''
        await self.doneevent.wait()

    async def finish(self):
        await self.fini()
        return self.result

    async def finishFile(self):
        '''
        Finish and commit the existing file, keeping the uploader active for more files.
        '''
        self.chunknum = 0

class _AsyncQueue(s_coro.Fini):
    ''' Multi-async producer, single sync consumer queue.  Assumes producers run on s_glob.loop '''
    def __init__(self, max_entries, drain_level=None):
        s_coro.Fini.__init__(self)
        self.deq = collections.deque()
        self.notdrainingevent = asyncio.Event(loop=s_glob.plex.loop)
        self.notdrainingevent.set()  # technically not thread-safe, but not used yet
        self.notemptyevent = threading.Event()
        self.max_entries = max_entries
        self.drain_level = max_entries // 2 if drain_level is None else drain_level

        async def _onfini():
            self.notemptyevent.set()
            self.notdrainingevent.set()
        self.onfini(_onfini)

    def get(self):
        while not self.isfini:
            try:
                val = self.deq.popleft()
                break
            except IndexError:
                self.notemptyevent.clear()
                if len(self.deq):
                    continue
                self.notemptyevent.wait()
        else:
            return None

        if not self.notdrainingevent.is_set():
            if len(self.deq) < self.drain_level:
                s_glob.plex.callSoonSafe(self.notdrainingevent.set)
        return val

    async def put(self, item):
        while not self.isfini:
            if len(self.deq) >= self.max_entries:
                self.notdrainingevent.clear()
            if not self.notdrainingevent.is_set():
                await self.notdrainingevent.wait()
                continue
            break

        self.deq.append(item)
        self.notemptyevent.set()

class _BlobStorWriter(s_coro.Fini):

    # FIXME: what about clients never finishing their transaction?
    # FIXME: partial commitsk, write-lock for writes

    class Command(enum.Enum):
        WRITE_BLOB = enum.auto()
        FINISH = enum.auto()
        UPDATE_OFFSET = enum.auto()

    class ClientInfo:
        BUF_SIZE = 16 * s_const.mebibyte

        def __init__(self):
            self.starttime = s_common.now()
            self.newhashes = []
            self.totalsize = 0
            self.nextfile()

        def nextfile(self):
            self.nextchunknum = 0
            self.tmpfh = tempfile.SpooledTemporaryFile(buffering=self.BUF_SIZE)
            self.hashing = hashlib.sha256()

    def __init__(self, blobstor):
        s_coro.Fini.__init__(self)
        self.xact = IncrementalTransaction(blobstor.lenv)
        self.lenv = blobstor.lenv
        self.blobstor = blobstor
        self._wcidcounter = itertools.count()  # a thread-safe incrementer
        self._workq = _AsyncQueue(50)
        self._worker = threading.Thread(target=self._workloop, name='BlobStorWriter')
        self.clients = {}

        async def _onfini():
            await self._workq.fini()
            self._worker.join()
        self.onfini(_onfini)

        self._worker.start()

    def _finish_file(self, client) -> None:
        hashval = client.hashing.digest()
        # Check if already present
        with self.xact.cursor(db=self.blobstor._blob_bytes) as curs:
            if _find_hash(curs, hashval):
                return
        MAX_SEGMENT_SIZE = 2**31  # Actually an lmdb value can be up to 2**32-1 bytes, but this is a nice round number
        with contextlib.closing(client.tmpfh):
            client.tmpfh.seek(0)
            total_sz = 0
            segment = 0
            while True:
                chunk = client.tmpfh.read(MAX_SEGMENT_SIZE)
                sz = len(chunk)
                total_sz += sz
                # We want to write *something* if data is empty
                if segment and not sz:
                    break
                segment_enc = segment.to_bytes(4, 'big')
                self.xact.put(hashval + segment_enc, chunk, db=self.blobstor._blob_bytes)
                segment += 1

        client.totalsize += total_sz
        client.newhashes.append(hashval)

    def _write_blob(self, wcid: int, chunknum: int, bytz: bytes) -> None:
        client = self.clients.get(wcid)
        if not chunknum:
            if client is None:
                self.clients[wcid] = client = self.ClientInfo()
            else:
                self._finish_file(client)
                client.nextfile()
        elif client is None:
            raise s_exc.AxonBadChunk('BlobStorWriter missing first chunk')

        client.tmpfh.write(bytz)
        client.hashing.update(bytz)

    def _save_update_stats(self, client):
        took = s_common.now() - client.starttime
        self.xact.guarantee()
        self.blobstor._clone_seqn.save(self.xact.txn, client.newhashes)
        self.blobstor._metrics.inc(self.xact.txn, 'bytes', client.totalsize)
        self.blobstor._metrics.inc(self.xact.txn, 'blobs', len(client.newhashes))
        self.blobstor._metrics.record(self.xact.txn, {'time': client.starttime, 'size': client.totalsize, 'took': took})

    def _complete_session(self, wcid):
        client = self.clients.get(wcid)
        if client is None:
            logger.debug('BlobStorWriter got session completion on unknown client')
            return None
        self._finish_file(client)
        self._save_update_stats(client)
        self.xact.commit()
        hashcount = len(client.newhashes)
        last_hashval = client.newhashes[-1] if hashcount else None
        del self.clients[wcid]
        return hashcount, last_hashval

    def update_offset(self, offset):
        self.xact.guarantee()
        self.xact.txn.put(b'clone:offset', struct.pack('>Q', offset), db=self.blobstor._blob_info)

    def _workloop(self):
        try:
            while not self.isfini:
                msg = self._workq.get()
                if msg is None:
                    break
                cmd = msg[0]
                if cmd == self.Command.WRITE_BLOB:
                    _, wcid, chunknum, bytz = msg
                    self._write_blob(wcid, chunknum, bytz)
                elif cmd == self.Command.FINISH:
                    _, wcid, fut = msg
                    result = self._complete_session(wcid)
                    if fut is not None:
                        s_glob.plex.callSoonSafe(lambda: fut.set_result(result))
                elif cmd == self.Command.UPDATE_OFFSET:
                    _, offset = msg
                    self.update_offset(offset)
        finally:
            # Workaround to avoid lmdb close/commit race
            self.xact.fini()

    # Client methods

    def makeclientid(self):
        return next(self._wcidcounter)

    async def partialsubmit(self, wcid, blocs):
        ran_at_all = False
        async for b in to_aiter(blocs):
            chunknum, bytz = b
            ran_at_all = True
            await self._workq.put((self.Command.WRITE_BLOB, wcid, chunknum, bytz))
        return ran_at_all

    async def complete(self, wcid, wait_for_result=False):
        rv = None
        if wait_for_result:
            fut = asyncio.Future(loop=s_glob.plex.loop)
            await self._workq.put((self.Command.FINISH, wcid, fut))
            await fut
            print('complete 1', flush=True)
            rv = fut.result()
        else:
            await self._workq.put((self.Command.FINISH, wcid, None))
        self.blobstor._newdataevent.set()
        return rv

    async def update_clonee_offset(self, offset):
        await self._workq.put((self.Command.UPDATE_OFFSET, offset))

    async def submit(self, blocs, wait_for_result=False):
        '''
        Returns:
             Count of hashes processed, last hash value processed
        '''
        wcid = self.makeclientid()
        ran_at_all = await self.partialsubmit(wcid, blocs)
        if not ran_at_all:
            return 0, None if wait_for_result else None
        rv = await self.complete(wcid, wait_for_result)
        return rv

class BlobStorApi(PassThroughApi):

    allowed_methods = ['clone', 'stat', 'metrics', 'offset', 'bulkput', 'putone', 'putmany', 'get', '_makeclientid',
                       '_complete', '_partialsubmit']

    async def startput(self):
        return Uploader(self.link, self)

class BlobStor(s_cell.Cell):
    '''
    The blob store maps sha256 values to sequences of bytes stored in a LMDB database.
    '''
    cellapi = BlobStorApi

    confdefs = (  # type: ignore
        ('mapsize', {'type': 'int', 'doc': 'LMDB mapsize value', 'defval': s_lmdb.DEFAULT_MAP_SIZE}),
        ('cloneof', {'type': 'str', 'doc': 'The name of a blob cell to clone from', 'defval': None}),
    )

    def __init__(self, dirn: str, conf=None) -> None:

        s_cell.Cell.__init__(self, dirn)
        self.clonetask = None

        if conf is not None:
            self.conf.update(conf)

        path = s_common.gendir(self.dirn, 'blobs.lmdb')

        mapsize = self.conf.get('mapsize')
        print(f'blobstor lmdb.open {path}', flush=True)
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128, map_size=mapsize)
        print('blobstor lmdb.open done', flush=True)

        self._blob_info = self.lenv.open_db(b'info')
        self._blob_bytes = self.lenv.open_db(b'bytes') # <sha256>=<byts>

        self._clone_seqn = s_lmdb.Seqn(self.lenv, b'clone')
        self._metrics = s_lmdb.Metrics(self.lenv)
        self._newdataevent = asyncio.Event(loop=s_glob.plex.loop)

        self.writer = _BlobStorWriter(self)

        self.cloneof = self.conf.get('cloneof')

        if self.cloneof is not None:
            self.clonetask = s_glob.plex.coroToTask(self._cloneeLoop(self.cloneof))

        def fini():
            s_glob.plex.addLoopCoro(self.writer.fini())
            # To avoid lmdb seg fault, let writer close the environment

        self.onfini(fini)

    def _makeclientid(self):
        ''' For Uploader's sake '''
        return self.writer.makeclientid()

    async def _partialsubmit(self, wcid, blocs):
        ''' For Uploader's sake '''
        return await self.writer.partialsubmit(wcid, blocs)

    async def _complete(self, wcid, wait_for_result=False):
        ''' For Uploader's sake '''
        return await self.writer.complete(wcid, wait_for_result)

    async def _cloneeLoop(self, cloneepath):
        '''
        Act to clone another blobstor, the clonee, by repeatedly asking long-poll-style for its new data
        '''
        CLONE_TIMEOUT = 60.0
        clonee = s_telepath.openurl(cloneepath)
        import ipdb; ipdb.set_trace()
        cur_offset = self._getCloneOffset()
        while not self.isfini:
            try:
                if clonee.isfini:
                    clonee = await s_telepath.openurl(cloneepath)

                genr = clonee.clone(cur_offset + 1, timeout=CLONE_TIMEOUT)
                if genr is not None:
                    new_offset = await self.blobs._consume_clone_data(genr)
                    if new_offset is not None:
                        cur_offset = new_offset
                        self.set_clone_offset(cur_offset)

            except Exception:
                if not self.isfini:
                    logger.exception('BlobStor.cloneeLoop error')

    async def bulkput(self, blocs):
        '''
        Save items from an iterator of (sha256, chunk #, <bytes>).

        Args:
            blocs: An iterator of (sha256, chunk #, <bytes>).  Every 0 chunk # represents a new file.
            The sha256 must be None, except if the chunk # is 0, in which it may optionally be a sha256 hash.  If
            present and the blobstor contains a value with a matching hash, all bytes will be skipped until the next
            bloc with a chunk # of 0 is encountered.

        Returns:
            None
        '''
        async def filter_out_known_hashes(self, blocs):
            skipping = False
            with self.lenv.begin(db=self._blob_bytes, buffers=True) as xact, xact.cursor(db=self._blob_bytes) as curs:
                async for hashval, chunknum, bytz in to_aiter(blocs):
                    if not chunknum:
                        skipping = hashval is not None and _find_hash(curs, hashval)
                    if skipping:
                        continue
                    yield chunknum, bytz

        hashcount, _ = await self.writer.submit(filter_out_known_hashes(self, blocs), wait_for_result=True)
        if hashcount:
            self._newdataevent.set()
        return hashcount

    async def putone(self, item):
        clientid = self.writer.makeclientid()
        await self.writer.submit(clientid, (None, 0, item))

    async def putmany(self, items):
        await self.writer.submit((None, 0, i) for i in items)

    async def get(self, hashval):
        '''
        Load and yield the bytes blocks for a given hash.

        Args:
            hashval (bytes): Hash to retrieve bytes for.

        '''
        with self.lenv.begin(db=self._blob_bytes, buffers=True) as xact:
            for chunk in self._get(hashval, xact):
                yield chunk

    def _get(self, hashval, xact):
        with xact.cursor(db=self._blob_bytes) as curs:
            if not _find_hash(curs, hashval):
                return None
            for k, v in curs:
                if not k[:len(hashval)] == hashval:
                    return None
                yield from s_common.chunks(v, CHUNK_SIZE)

    async def clone(self, offset: int, include_contents=True, timeout=0):
        '''
        Yield (offset, (sha256, chunknum, bytes)) tuples to clone this BlobStor.

        Args:
            offset (int): Offset to start yielding rows from.
            include_contents (bool):  Whether to include the blob value in the results stream

        Yields:
            ((bytes, (bytes, int, bytes))): tuples of (index, (sha256,chunknum,bytes)) data.
        '''
        cur_offset = self._clone_seqn.indx
        print(f'clone: offset={offset}, cur_offset={cur_offset}, timeout={timeout}', flush=True)
        if cur_offset <= offset:
            if timeout == 0:
                return
            self._newdataevent.clear()
            try:
                await asyncio.wait_for(self._newdataevent.wait(), timeout, loop=s_glob.plex.loop)
            except asyncio.TimeoutError:
                return
        print('clone woke!', flush=True)

        with self.lenv.begin(buffers=True) as xact:
            for off, sha256 in self._clone_seqn.iter(xact, offset):
                if include_contents:
                    for chunknum, chunk in enumerate(self._get(sha256, xact)):
                        yield off, (None if chunknum else sha256, chunknum, bytes(chunk))
                else:
                    yield off, (sha256, None, None)

    async def _consume_clone_data(self, items):
        '''
        Add rows obtained from a BlobStor.clone() method.

        Args:
            items (Iterable): A list of tuples containing (offset, (sha256,chunknum,bytes)) data.

        Returns:
            int: The last index value processed from the list of items, or None if nothing was processed
        '''
        last_offset = None

        async def yielder(i):
            '''
            Drop the offset and keep track of the last one encountered
            '''
            nonlocal last_offset
            async for offset, (sha256, chunknum, bytz) in to_aiter(i):
                yield sha256, chunknum, bytz
                last_offset = offset

        await self.bulkput(yielder(items))

        # Update how far we've cloned
        if last_offset is not None:
            self.writer.update_offset(last_offset)
        return last_offset

    async def stat(self):
        '''
        Get storage stats for the BlobStor.

        Returns:
            dict: A dictionary containing the total bytes and blocks store in the BlobStor.
        '''
        return self._metrics.stat()

    async def metrics(self, offs=0):
        '''
        Get metrics for the BlobStor. These can be aggregated to compute the storage stats.

        Args:
            offs (int): Offset to start collecting stats from.

        Yields:
            ((int, dict)): Yields index, sample data from the metrics sequence.
        '''
        with self.lenv.begin(buffers=True) as xact:
            for item in self._metrics.iter(xact, offs):
                yield item

    def _get_clone_offset(self):
        '''
        Get the current offset for the clone:index of the BlobStor.

        Returns:
            int: The offset value.
        '''
        # FIXME who writes to clone:index?
        with self.lenv.begin(buffers=True) as xact:

            lval = xact.get(b'clone:indx', db=self.blobstor._blob_info)
            if lval is None:
                return -1

            return struct.unpack('>Q', lval)[0] + 1

class _ProxyKeeper(s_coro.Fini):

    # All the proxy keepers share a common buid -> path map
    buidpathmap: Dict[bytes, str] = {}  # buid -> path

    def __init__(self):
        s_coro.Fini.__init__(self)
        self._proxymap = {}  # buid -> proxy

        # All the proxy

        async def fini():
            for proxy in self._proxymap.values():
                if proxy is not None:
                    await proxy.fini()

        self.onfini(fini)

    async def _addproxy(self, proxy, path):
        buid = binascii.unhexlify(await proxy.getCellIden())
        self.buidpathmap[buid] = path
        self._proxymap[buid] = proxy
        return buid

    async def connect(self, path: str) -> Tuple[bytes, s_telepath.Proxy]:
        proxy = await s_telepath.openurl(path)
        if proxy is None:
            return None
        newbuid = await self._addproxy(proxy, path)
        return newbuid, proxy

    async def randoproxy(self, buids=None):
        '''
        Returns a random buid, blobstor from the buids parameter, or from all know buids if parameter is None
        '''
        if buids is None:
            buids = list(self.buidpathmap.keys())
        if not buids:
            raise s_exc.AxonNoBlobStors()
        rot = random.randrange(len(buids))
        buidsrot = buids[rot:] + buids[:rot]
        for buid in buidsrot:
            blobstor = await self.get(buid)
            if blobstor is not None:
                return buid, blobstor
        raise s_exc.AxonNoBlobStors()

    async def get(self, buid: bytes) -> s_telepath.Proxy:
        proxy = self._proxymap.get(buid)
        if proxy:
            if proxy.isfini:
                del self._proxymap[buid]
            else:
                return proxy
        path = self.buidpathmap.get(buid)
        if path is None:
            raise s_exc.AxonUnknownBuid()
        newbuid, proxy = await self.connect(path)
        if newbuid != buid:
            raise s_exc.AxonBlobStorBuidChanged()
        return proxy

class AxonApi(PassThroughApi):
    allowed_methods = ['startput', 'get', 'locs', 'stat', 'wants', 'metrics', 'addBlobStor']

    def __init__(self, cell, link):
        PassThroughApi.__init__(self, cell, link)

        # The Axon makes new connections to each blobstor for each client.
        self._proxykeeper = _ProxyKeeper()

    async def fini(self):
        await self._proxykeeper.fini()

    async def get(self, hashval):
        return await self.item.get(hashval, self._proxykeeper)

    def startput(self, files):
        return self.item.startput(files, self._proxykeeper)

class Axon(s_cell.Cell):

    cellapi = AxonApi
    confdefs = (  # type: ignore
        ('mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE, 'doc': 'The size of the LMDB memory map'}),
    )

    def __init__(self, dirn: str, conf=None) -> None:
        s_cell.Cell.__init__(self, dirn)

        path = s_common.gendir(self.dirn, 'axon.lmdb')
        mapsize = self.conf.get('mapsize')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.bloblocs = self.lenv.open_db(b'axon:blob:locs', dupsort=True, dupfixed=True) # <sha256>=blobstor_buid
        self.offsets = self.lenv.open_db(b'axon:blob:offsets', dupsort=True, dupfixed=True) # <sha256>=blobstor_buid

        # Persistent settings
        self.settings = self.lenv.open_db(b'axon:settings', dupsort=True)

        self._metrics = s_lmdb.Metrics(self.lenv)
        self._proxykeeper = _ProxyKeeper()

        paths = self._get_stored_blobstorpaths()
        self.blobstorwatchers: Dict[str, asyncio.Event] = {}
        for path in paths:
            self._start_watching_blobstor(path)

        self._worker = threading.Thread(target=self._workloop, name='BlobStorWriter')
        self._workq = _AsyncQueue(50)
        self.xact = IncrementalTransaction(self.lenv)
        self._worker.start()

        def fini():

            async def run_on_loop():
                for stop_event in self.blobstorwatchers.values():
                    stop_event.set()
                await self._workq.fini()
            s_glob.plex.coroToTask(run_on_loop())
            self._worker.join(5)

        self.onfini(fini)

    def _get_stored_blobstorpaths(self):
        paths = []
        with self.lenv.begin(buffers=True) as xact, xact.cursor(db=self.settings) as curs:
            if not curs.set_key(b'blobstorpaths'):
                return []
            for path in curs.iternext_dup():
                paths.append(path.decode())
        return paths

    async def _start_watching_blobstor(self, blobstorpath: str):
        stop_watching_event = asyncio.Event(loop=s_glob.plex.loop)
        self.blobstorwatchers[blobstorpath] = stop_watching_event
        buid, blobstor = await self._proxykeeper.connect(blobstorpath)
        s_glob.plex.addLoopCoro(self._watch_blobstor(blobstor, buid, blobstorpath, stop_watching_event))

    async def addBlobStor(self, blobstorpath):
        '''
        Causes an axon to start using a particular blobstor.  This is persistently stored; on Axon restart, it will
        automatically reconnect to the blobstor at the specified path.
        '''
        def _store_blobstorpath(path):
            txn = self.xact.guarantee()
            txn.put(b'blobstorpaths', path.encode(), dupdata=True, db=self.settings)
            self.xact.commit()

        await self._executor(_store_blobstorpath, blobstorpath)
        await self._start_watching_blobstor(blobstorpath)
        print('addBlobSTor done', flush=True)

    async def _watch_blobstor(self, blobstor, buid, blobstorpath, stop_event):
        '''
        Monitor a blobstor, by repeatedly asking long-poll-style for its new data
        '''
        print('_watch_blobstor', flush=True)
        logger.info('Bringing BlobStor %s online', blobstorpath)

        CLONE_TIMEOUT = 60.0
        cur_offset = self._getSyncProgress(buid)
        while not self.isfini and not stop_event.is_set():
            try:
                if blobstor.isfini:
                    blobstor = await s_telepath.openurl(blobstorpath)
                    if blobstor is None:
                        logger.warning('No longer monitoring %s for new data', blobstorpath)
                        break

                # Wait on either the clone completing, or a signal to stop watching
                clone_coro = blobstor.clone(cur_offset+1, timeout=CLONE_TIMEOUT, include_contents=False)
                stop_coro = stop_event.wait()
                print('before wait', flush=True)
                donelist, notdonelist = await asyncio.wait([clone_coro, stop_coro], loop=s_glob.plex.loop,
                                                           return_when=concurrent.futures.FIRST_COMPLETED)
                print('after wait', flush=True)
                for task in notdonelist:
                    task.cancel()
                if stop_event.is_set():
                    break
                genr = donelist.pop().result()

                if genr is not None:
                    rv = await self._consume_clone_data(genr, buid)
                    if rv is not None:
                        cur_offset = rv
                        await self._executor_nowait(self._updateSyncProgress, buid, cur_offset)


            except Exception:
                if not self.isfini:
                    logger.exception('BlobStor.blobstorLoop error')

    def _updateSyncProgress(self, buid, new_offset):
        xact = self.xact.guarantee()
        xact.put(b'offset:' + buid, struct.pack('>Q', new_offset), db=self.offsets)

        self.xact.commit()


    def _getSyncProgress(self, buid):
        '''
        Get the current offset for one blobstor of the Axon

        Returns:
            int: The offset value.
        '''
        with self.lenv.begin(buffers=True) as xact:

            lval = xact.get(b'offset:' + buid, db=self.offsets)
            if lval is None:
                return -1

            return struct.unpack('>Q', lval)[0] + 1

    def _workloop(self):
        '''
        A worker for running stuff that requires a write lock
        '''
        try:
            while not self.isfini:
                msg = self._workq.get()
                if msg is None:
                    break
                func, done_event = msg
                func()
                if done_event is not None:
                    s_glob.plex.callSoonSafe(done_event.set)
        finally:
            self.xact.fini()
        print('_workloop done')

    async def _executor_nowait(self, func, *args, **kwargs):
        def syncfunc():
            func(*args, **kwargs)

        await self._workq.put((syncfunc, None))

    async def _executor(self, func, *args, **kwargs):
        done_event = asyncio.Event(loop=s_glob.plex.loop)
        retn = None

        def syncfunc():
            nonlocal retn
            retn = func(*args, **kwargs)

        await self._workq.put((syncfunc, done_event))
        await done_event.wait()
        return retn

    def _addloc(self, buid, hashval):
        '''
        Record blobstor's buid has a particular hashval.  Should be run in my executor.
        '''
        print(f'_addloc: {buid} has {hashval}', flush=True)
        # import ipdb; ipdb.set_trace()
        xact = self.xact.guarantee()

        tick = s_common.now()

        written = xact.put(hashval, buid, db=self.bloblocs, overwrite=False)

        if written:
            print('***Inc', flush=True)
            self._metrics.inc(xact, 'files', 1)

            # metrics contains everything we need to clone
            self._metrics.record(xact, {'time': tick, 'buid': buid, 'sha256': hashval})

            self.xact.commit()

    async def _consume_clone_data(self, items, frombuid):
        '''
        Add rows obtained from a BlobStor.clone() method.

        Args:
            items (Iterable): A list of tuples containing (offset, (sha256,chunknum,bytes)) data.

        Returns:
            int: The last index value processed from the list of items, or None if nothing was processed
        '''
        last_offset = None

        async for offset, (hashval, _, _) in to_aiter(items):
            await self._executor_nowait(self._addloc, frombuid, hashval)

            last_offset = offset

        return last_offset

    async def stat(self):
        return self._metrics.stat()

    async def wants(self, hashvals):
        '''
        Given a list of hashvals, returns a list of the hashes *not* available
        '''
        wants = []
        with self.lenv.begin(db=self.bloblocs) as xact:
            curs = xact.cursor()
            for hashval in hashvals:
                if not curs.set_key(hashval):
                    wants.append(hashval)
        return wants

    async def locs(self, hashval):
        '''
        Get the blobstor buids for a given sha256 value

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            sha256 (bytes): The sha256 digest to look up

        Returns:
            list: A list of blobnames
        '''
        with self.lenv.begin() as xact, xact.cursor(db=self.bloblocs) as curs:
            if not curs.set_key(hashval):
                return []
            blobstorbuids = []
            for buid in curs.iternext_dup():
                blobstorbuids.append(buid)
            return blobstorbuids

    async def startput(self, proxykeeper=None):
        '''
        Args:
            None

        Returns:
            an Uploader object suitable for streaming an upload
        '''
        if proxykeeper is None:
            proxykeeper = self._proxykeeper
        _, blobstor = await proxykeeper.randoproxy()
        return await blobstor.startput()

    async def bulkput(self, files, proxykeeper=None):
        '''
        Save a list of files to the axon.

        Args:
            files ([bytes]): A list of files as bytes blobs.

        Returns:
            int: The number of files saved.
        '''
        if proxykeeper is None:
            proxykeeper = self._proxykeeper
        buid, blobstor = await proxykeeper.randoproxy()
        async with await blobstor.startput() as uploader:
            for bytz in files:
                for chunk in s_common.chunks(bytz, CHUNK_SIZE):
                    await uploader.write(chunk)
                await uploader.finishFile()
            count, hashval = await uploader.finish()
        if count:
            await self._executor(self._addloc, buid, hashval)

        return count

    async def get(self, hashval, proxykeeper=None):
        '''
        Yield bytes for the given SHA256.

        Args:
            hashval (str): The SHA256 hash bytes.

        Yields:
            bytes: Bytes of the file requested.

        Raises:
            RetnErr: If the file requested does not exist.
        '''
        if proxykeeper is None:
            proxykeeper = self._proxykeeper
        locs = await self.locs(hashval)
        if not locs:
            raise s_exc.NoSuchFile()
        _, blobstor = await proxykeeper.randoproxy(locs)

        # that await is due to the current async generator telepath assymetry
        async for bloc in await blobstor.get(hashval):
            yield bloc

    async def metrics(self, offs=0):
        with self.lenv.begin(buffers=True) as xact:
            for item in self._metrics.iter(xact, offs):
                yield item
