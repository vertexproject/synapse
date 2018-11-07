import enum
import struct
import random
import asyncio
import hashlib
import logging
import binascii
import tempfile
import functools
import concurrent
import contextlib

import lmdb  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.base as s_base
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const
import synapse.lib.queue as s_queue
import synapse.lib.share as s_share

logger = logging.getLogger(__name__)

# File convention: bsid -> persistent unique id for a blobstor (actually the cell iden)

# N.B. BlobStor does *not* use lmdb Slab.  It has its own incremental transaction.

# TODO: port to use Slab

CHUNK_SIZE = 16 * s_const.mebibyte

def _path_sanitize(blobstorpath):
    '''
    The path might contain username/password, so just return the last part
    '''
    return '.../' + blobstorpath.rsplit('/', 1)[-1]

async def to_aiter(it):
    '''
    Take either a sync or async iteratable and yields as an async generator
    '''
    if hasattr(it, '__aiter__'):
        async for i in it:
            yield i
    else:
        for i in it:
            yield i

def _find_hash(curs, key):
    '''
    Set a LMDB cursor to the first key that starts with \a key

    Returns:
        False if key not present, else True and positions cursor at first chunk of value
    '''
    if not curs.set_range(key):
        return False
    return curs.key()[:len(key)] == key

class PassThroughApi(s_cell.CellApi):
    '''
    Class that passes through methods made on it to its cell.
    '''
    allowed_methods = []  # type: ignore

    async def __anit__(self, cell, link):
        await s_cell.CellApi.__anit__(self, cell, link)

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
        Make an LMDB transaction if we don't already have kone, and return it
        '''
        if self.txn is None:
            self.txn = self.lenv.begin(write=True, buffers=True)
        return self.txn

    def cursor(self, db=None):
        self.guarantee()
        return self.txn.cursor(db)

    def put(self, key, value, db):
        '''
        Write data to the database, committing if too many bytes are uncommitted
        '''
        vallen = len(value)
        if vallen + self._bytecount > self.MAX_OUTSTANDING:
            self.commit()
        self.guarantee()
        self._bytecount += vallen
        rv = self.txn.put(key, value, db=db)
        return rv

class Uploader(s_share.Share):
    '''
    A remotely shareable object used for streaming uploads to a blobstor
    '''
    typename = 'uploader'

    async def __anit__(self, link, item):
        await s_share.Share.__anit__(self, link, item)
        self.doneevent = asyncio.Event(loop=self.loop)
        self.exitok = False
        self.chunknum = 0
        self.wcid = s_common.guid()
        self._needfinish = True

        async def fini():
            if self._needfinish:
                await self.finish()
            self.doneevent.set()

        self.onfini(fini)

    async def write(self, bytz):
        '''
        Upload some data

        Args:
            bytz (bytes):  a chunk of data.   It does not have to be an entire blob.
        '''
        await self.item._partialsubmit(self.wcid, ((self.chunknum, bytz), ))
        self.chunknum += 1

    async def _runShareLoop(self):
        '''
        This keeps the object alive until we're fini'd.
        '''
        await self.doneevent.wait()

    async def finish(self):
        '''
        Conclude an uploading session
        '''
        self._needfinish = False
        rv = await self.item._complete(self.wcid, wait_for_result=True)
        return rv

    async def cancelFile(self):
        '''
        Cancel the current blob.  Will still listen for new blobs.
        '''
        await self.item._cancel(self.wcid)
        self.chunknum = 0

    async def finishFile(self):
        '''
        Finish and commit the existing file, keeping the uploader active for more files.
        '''
        self.chunknum = 0

class _BlobStorWriter(s_base.Base):
    '''
    An active object that writes to disk on behalf of a blobstor (plus the client methods to interact with it)
    '''

    class Command(enum.Enum):
        '''
        The types of commands a blobstorwriter client can issue
        '''
        WRITE_BLOB = enum.auto()
        CANCEL_BLOB = enum.auto()
        FINISH = enum.auto()
        UPDATE_OFFSET = enum.auto()

    class ClientInfo:
        '''
        The session information for a single active client to a blobstor
        '''
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
            self.anything_written = False

    async def __anit__(self, blobstor):
        await s_base.Base.__anit__(self)
        self.xact = IncrementalTransaction(blobstor.lenv)
        self.lenv = blobstor.lenv
        self.blobstor = blobstor
        self._workq = await s_queue.AsyncQueue.anit(50)
        self._worker = self._workloop()
        self._worker.name = 'BlobStorWriter'
        self.clients = {}

        async def _onfini():
            await self._workq.fini()
            self._worker.join()
            self.xact.fini()
        self.onfini(_onfini)

    def _finish_file(self, client):
        '''
        Read from the temporary file and write to one or more database rows.
        '''
        if not client.anything_written:
            return
        hashval = client.hashing.digest()
        # Check if already present
        if hashval == self.blobstor._partial_hash:
            return  # We're currently writing this one
        with self.xact.cursor(db=self.blobstor._blob_bytes) as curs:
            if _find_hash(curs, hashval):
                return
        MAX_SEGMENT_SIZE = 2**31  # Actually an lmdb value can be up to 2**32-1 bytes, but this is a nice round number
        with contextlib.closing(client.tmpfh):
            client.tmpfh.seek(0)
            total_sz = 0
            segment = 0
            self.blobstor._partial_hash = hashval
            self.xact.put(b'blobstor:partial', hashval, db=self.blobstor._blob_info)
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

        self.xact.txn.delete(b'blobstor:partial', db=self.blobstor._blob_info)
        self.blobstor._partial_hash = None

        client.totalsize += total_sz
        client.newhashes.append(hashval)

    def _cancel_blob(self, wcid):
        '''
        Args:
            wcid (str): A value unique to a particular client session
        Returns:
            None
        '''
        client = self.clients.get(wcid)
        if client is None:
            return
        client.tmpfh.close()
        client.nextfile()

    def _write_blob(self, wcid, chunknum, bytz):
        '''
        Write data

        Args:
            wcid (str): A value unique to a particular client session
            chunknum (int):  the index of this particular chunk in blob.  A chunknum of 0 completes any previous
            blob and starts a new one.  chunknums must be consecutive for each blob.
            bytz (bytes):  the actual payload

        Returns:
            None
        '''
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
        client.anything_written = True

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
            return 0, None
        self._finish_file(client)
        self._save_update_stats(client)
        self.xact.commit()
        hashcount = len(client.newhashes)
        last_hashval = client.newhashes[-1] if hashcount else None
        del self.clients[wcid]
        return hashcount, last_hashval

    def _updateCloneProgress(self, offset):
        self.xact.guarantee()
        self.xact.txn.put(b'clone:progress', struct.pack('>Q', offset), db=self.blobstor._blob_info)
        self.xact.commit()

    @s_common.firethread
    def _workloop(self):
        '''
        Main loop for _BlobStorWriter
        '''
        try:
            while not self.isfini:
                msg = self._workq.get()
                if msg is None:
                    break
                cmd = msg[0]
                if cmd == self.Command.WRITE_BLOB:
                    _, wcid, chunknum, bytz = msg
                    self._write_blob(wcid, chunknum, bytz)
                elif cmd == self.Command.CANCEL_BLOB:
                    _, wcid = msg
                    self._cancel_blob(wcid)
                elif cmd == self.Command.FINISH:
                    _, wcid, fut = msg
                    result = self._complete_session(wcid)
                    if fut is not None:
                        self.schedCallSafe(fut.set_result, result)

                elif cmd == self.Command.UPDATE_OFFSET:
                    _, offset = msg
                    self._updateCloneProgress(offset)
        finally:
            # Workaround to avoid lmdb close/commit race (so that fini is on same thread as lmdb xact)
            self.xact.fini()

    # Client methods

    async def partialsubmit(self, wcid, blocs):
        ran_at_all = False
        async for b in to_aiter(blocs):
            chunknum, bytz = b
            ran_at_all = True
            await self._workq.put((self.Command.WRITE_BLOB, wcid, chunknum, bytz))
        return ran_at_all

    async def cancel(self, wcid):
        await self._workq.put((self.Command.CANCEL_BLOB, wcid))

    async def complete(self, wcid, wait_for_result=False):
        rv = None
        if wait_for_result:
            fut = asyncio.Future(loop=self.loop)
            await self._workq.put((self.Command.FINISH, wcid, fut))
            await fut
            rv = fut.result()
        else:
            await self._workq.put((self.Command.FINISH, wcid, None))
        self.blobstor._newdataevent.set()
        return rv

    async def updateCloneProgress(self, offset):
        logger.debug('updateCloneProgress {offset}')
        await self._workq.put((self.Command.UPDATE_OFFSET, offset))

    async def submit(self, blocs, wait_for_result=False):
        '''
        Returns:
             Count of hashes processed, last hash value processed
        '''
        wcid = s_common.guid()
        ran_at_all = await self.partialsubmit(wcid, blocs)
        if not ran_at_all:
            return 0, None if wait_for_result else None
        rv = await self.complete(wcid, wait_for_result)
        return rv

class BlobStorApi(PassThroughApi):

    allowed_methods = ['clone', 'stat', 'metrics', 'offset', 'bulkput', 'putone', 'putmany', 'get',
                       '_complete', '_cancel', '_partialsubmit', 'getCloneProgress']

    async def startput(self):
        upld = await Uploader.anit(self.link, self)
        self.onfini(upld)
        return upld

class BlobStor(s_cell.Cell):
    '''
    The blob store maps sha256 values to sequences of bytes stored in a LMDB database.
    '''
    cellapi = BlobStorApi

    confdefs = (  # type: ignore
        ('mapsize', {'type': 'int', 'doc': 'LMDB mapsize value', 'defval': s_lmdb.DEFAULT_MAP_SIZE}),
        ('cloneof', {'type': 'str', 'doc': 'The telepath of a blob cell to clone from', 'defval': None}),
    )

    async def __anit__(self, dirn: str, conf=None) -> None:  # type: ignore
        await s_cell.Cell.__anit__(self, dirn)

        self.clonetask = None

        if conf is not None:
            self.conf.update(conf)

        path = s_common.gendir(self.dirn, 'blobs.lmdb')

        mapsize = self.conf.get('mapsize')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128, map_size=mapsize)
        self._blob_info = self.lenv.open_db(b'info')
        self._blob_bytes = self.lenv.open_db(b'bytes') # <sha256>=<byts>

        self._clone_seqn = s_lmdb.Seqn(self.lenv, b'clone')
        self._metrics = s_lmdb.Metrics(self.lenv)
        self._newdataevent = asyncio.Event(loop=self.loop)

        def delevent():
            del self._newdataevent

        self.onfini(delevent)

        self._recover_partial()
        self._partial_hash = None  # hash currently being written

        self.writer = await _BlobStorWriter.anit(self)

        self.cloneof = self.conf.get('cloneof')

        if self.cloneof is not None:
            self.clonetask = self.schedCoro(self._cloneeLoop(self.cloneof))

        self.onfini(self.writer.fini)

    def _recover_partial(self):
        '''
        Check if we died in the middle of writing a big blob.  If so delete it.
        '''
        with self.lenv.begin(buffers=True, write=True) as xact:

            partial_hash = xact.get(b'blobstor:partial', db=self._blob_info)
            if partial_hash is None:
                return
            logger.info('Found partially written blob.  Deleting')
            with xact.cursor(db=self._blob_bytes) as curs:
                if not _find_hash(curs, partial_hash):
                    return None
                while True:
                    curkey = curs.key()
                    if curkey is None or curkey[:len(partial_hash)] != partial_hash:
                        break
                    curs.delete()

    async def _partialsubmit(self, wcid, blocs):
        ''' For Uploader's sake '''
        return await self.writer.partialsubmit(wcid, blocs)

    async def _complete(self, wcid, wait_for_result=False):
        ''' For Uploader's sake '''
        return await self.writer.complete(wcid, wait_for_result)

    async def _cancel(self, wcid):
        ''' For Uploader's sake '''
        return await self.writer.cancel(wcid)

    async def _cloneeLoop(self, cloneepath):
        '''
        Act to clone another blobstor, the clonee, by repeatedly asking long-poll-style for its new data
        '''
        CLONE_TIMEOUT = 30.0
        clonee = await s_telepath.openurl(cloneepath)
        cur_offset = self.getCloneProgress()
        while not self.isfini:
            try:
                if clonee.isfini:
                    clonee = await s_telepath.openurl(cloneepath)

                genr = await clonee.clone(cur_offset, timeout=CLONE_TIMEOUT)
                last_offset = await self._consume_clone_data(genr)
                if last_offset is not None:
                    cur_offset = last_offset + 1
                    await self.writer.updateCloneProgress(cur_offset)

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
        return await self.writer.submit(((0, item), ), wait_for_result=True)

    async def putmany(self, items):
        return await self.writer.submit(((0, i) for i in items), wait_for_result=True)

    async def get(self, hashval):
        '''
        Load and yield the bytes blocks for a given hash.

        Args:
            hashval (bytes): Hash to retrieve bytes for.

        '''
        if hashval == self._partial_hash:
            return
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
        MAX_ITERS = 1024  # just a rough number so we don't have genrs that last forever
        iter_count = 0
        cur_offset = self._clone_seqn.indx  # actually, the next offset at which we'll write
        if cur_offset <= offset:
            if timeout == 0:
                return
            self._newdataevent.clear()
            try:
                await asyncio.wait_for(self._newdataevent.wait(), timeout)
            except asyncio.TimeoutError:
                return
        with self.lenv.begin(buffers=True) as xact:
            for off, hashval in self._clone_seqn.iter(xact, offset):
                iter_count += 1
                if include_contents:
                    for chunknum, chunk in enumerate(self._get(hashval, xact)):
                        yield off, (None if chunknum else hashval, chunknum, bytes(chunk))
                        iter_count += 1
                else:
                    yield off, (hashval, None, None)
                if iter_count >= MAX_ITERS:
                    break

    async def _consume_clone_data(self, items):
        '''
        Add rows obtained from a BlobStor.clone() method.

        Args:
            items (Iterable): A list of tuples containing (offset, (sha256,chunknum,bytes)) data.

        Returns:
            int: The the last offset processed from the list of items, or None if nothing was processed
        '''
        last_offset = None

        async def yielder(i):
            '''
            Drop the offset and keep track of the last one encountered
            '''
            nonlocal last_offset
            async for offset, (hashval, chunknum, bytz) in to_aiter(i):
                yield hashval, chunknum, bytz
                last_offset = offset

        await self.bulkput(yielder(items))

        # Update how far we've cloned
        if last_offset is not None:
            logger.debug(f'_consume_clone_data returning {last_offset}')
            return last_offset
        logger.debug(f'_consume_clone_data returning None')
        return None

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

    def getCloneProgress(self):
        '''
        Get the next offset to retrieve for the clone:index of the BlobStor.

        Returns:
            int: The offset value
        '''
        with self.lenv.begin(buffers=True) as xact:

            lval = xact.get(b'clone:progress', db=self._blob_info)
            if lval is None:
                return 0

            return struct.unpack('>Q', lval)[0]

class _ProxyKeeper(s_base.Base):
    '''
    A container for active blobstor proxy objects.
    '''

    # All the proxy keepers share a common bsid -> path map
    bsidpathmap = {}  # type: ignore

    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self._proxymap = {}  # bsid -> proxy

        async def fini():
            for proxy in self._proxymap.values():
                if proxy is not None:
                    await proxy.fini()
            self._proxymap = {}

        self.onfini(fini)

    def get_all(self):
        '''
        Returns:
            (Dict[str, proxy]) A map of path -> proxy for all known blobstors.
        '''
        retn = {}
        for bsid, proxy in self._proxymap.items():
            path = self.bsidpathmap.get(bsid)
            if path is not None:
                retn[path] = proxy
        return retn

    async def _addproxy(self, proxy, path):
        bsid = binascii.unhexlify(await proxy.getCellIden())
        self.bsidpathmap[bsid] = path
        self._proxymap[bsid] = proxy
        return bsid

    async def connect(self, path):
        '''
        Connect to a proxy.

        Returns:
            (bytes, s_telepath.Proxy) the bsid and the proxy object
        '''
        try:
            proxy = await s_telepath.openurl(path)
        except Exception:
            logger.exception('Failed to connect to telepath %s', _path_sanitize(path))
            raise

        newbsid = await self._addproxy(proxy, path)
        return newbsid, proxy

    async def randoproxy(self, bsids=None):
        '''
        Returns a random (bsid, blobstor) pair from the bsids parameter, or from all know bsids if parameter is None
        '''
        if bsids is None:
            bsids = list(self.bsidpathmap.keys())
        if not bsids:
            raise s_exc.AxonNoBlobStors()
        rot = random.randrange(len(bsids))
        bsidsrot = bsids[rot:] + bsids[:rot]
        for bsid in bsidsrot:
            try:
                blobstor = await self.get(bsid)
            except Exception:
                logger.warning('Trouble connecting to BSID %r', bsid)
                continue

            return bsid, blobstor
        raise s_exc.AxonNoBlobStors()

    async def get(self, bsid: bytes) -> s_telepath.Proxy:
        '''
        Retrieve a proxy object by bsid, connecting if not already connected
        '''
        proxy = self._proxymap.get(bsid)
        if proxy:
            if proxy.isfini:
                del self._proxymap[bsid]
            else:
                return proxy
        path = self.bsidpathmap.get(bsid)
        if path is None:
            raise s_exc.AxonUnknownBsid()
        newbsid, proxy = await self.connect(path)
        if newbsid != bsid:
            raise s_exc.AxonBlobStorBsidChanged()
        return proxy

class AxonApi(PassThroughApi):
    allowed_methods = ['get', 'locs', 'stat', 'wants', 'metrics', 'putone',
                       'addBlobStor', 'unwatchBlobStor', 'getBlobStors']

    async def __anit__(self, cell, link):
        await PassThroughApi.__anit__(self, cell, link)

        # The Axon makes new connections to each blobstor for each client.
        self._proxykeeper = await _ProxyKeeper.anit()

        async def fini():
            await self._proxykeeper.fini()

        self.onfini(fini)

    async def get(self, hashval):
        return await self.cell.get(hashval, self._proxykeeper)

    async def startput(self):
        bsid, blobstor = await self._proxykeeper.randoproxy()
        rv = await UploaderProxy.anit(self.link, self.cell, blobstor, bsid)
        return rv

class UploaderProxy(s_share.Share):
    ''' A proxy to a blobstor uploader living with the axon '''
    typename = 'uploaderproxy'

    async def __anit__(self, link, axon, blobstorproxy, bsid):
        await s_share.Share.__anit__(self, link, axon)
        self.doneevent = asyncio.Event(loop=self.loop)
        self.blobstor = blobstorproxy
        self.bsid = bsid
        self.uploader = None
        self.hashing = None
        self.finished = False

        async def fini():
            if self.uploader is not None:
                try:
                    await self.finish()
                except lmdb.Error:
                    # We're shutting down.  Too late to commit.
                    pass
                await self.uploader.fini()
            self.doneevent.set()

        self.onfini(fini)

    async def write(self, bytz):
        if self.finished:
            raise s_exc.AxonUploaderFinished
        if self.uploader is None:
            self.uploader = await self.blobstor.startput()
        if self.hashing is None:
            self.hashing = hashlib.sha256()
        self.hashing.update(bytz)
        await self.uploader.write(bytz)

    async def _runShareLoop(self):
        '''
        This keeps the object alive until we're fini'd.
        '''
        await self.doneevent.wait()

    async def finish(self):
        return await self._finish(False)

    async def finishFile(self):
        return await self._finish(True)

    async def _finish(self, keep_going):
        if self.hashing is None:
            # Ignore inocuous calls to finish or finishFile if there weren't any writes.
            return
        if self.finished:
            raise s_exc.AxonUploaderFinished
        if self.uploader is None:
            return
        hashval = self.hashing.digest()
        self.hashing = None
        if await self.item.wants([hashval]) == []:
            await self.uploader.cancelFile()
            return

        if keep_going:
            retn = await self.uploader.finishFile()
            await self.item._executor_nowait(self.item._addloc, self.bsid, hashval)
        else:
            self.finished = True
            retn = await self.uploader.finish()
            if retn[1] is not None and retn[1] != hashval:
                # The BlobStor and the Axon don't agree on the hash?!
                raise s_exc.AxonBlobStorDisagree
            await self.item._executor(self.item._addloc, self.bsid, hashval, commit=True)
        return retn

class Axon(s_cell.Cell):

    cellapi = AxonApi
    confdefs = (  # type: ignore
        ('mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE, 'doc': 'The size of the LMDB memory map'}),
    )

    async def __anit__(self, dirn: str, conf=None) -> None:  # type: ignore
        await s_cell.Cell.__anit__(self, dirn)

        path = s_common.gendir(self.dirn, 'axon.lmdb')
        mapsize = self.conf.get('mapsize')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.bloblocs = self.lenv.open_db(b'axon:blob:locs', dupsort=True, dupfixed=True) # <sha256>=blobstor_bsid
        self.offsets = self.lenv.open_db(b'axon:blob:offsets') # <sha256>=blobstor_bsid

        # Persistent settings
        self.settings = self.lenv.open_db(b'axon:settings', dupsort=True)

        self._metrics = s_lmdb.Metrics(self.lenv)
        self._proxykeeper = await _ProxyKeeper.anit()

        # Clear the global proxykeeper bsid->telepath path map (really just for unit tests)
        _ProxyKeeper.bsidpathmap = {}

        paths = self._get_stored_blobstorpaths()
        self.blobstorwatchers = {}  # type: ignore

        async def _connect_to_blobstors():
            # Wait a few seconds for the daemon to register all of its shared objects
            DAEMON_DELAY = 3
            await asyncio.sleep(DAEMON_DELAY)
            for path in paths:
                try:
                    await self._start_watching_blobstor(path)
                except Exception:
                    logger.error('At axon startup, failed to connect to stored blobstor path %s', _path_sanitize(path))

        conn_future = self.schedCoro(_connect_to_blobstors())

        self._workq = await s_queue.AsyncQueue.anit(50)
        self.xact = IncrementalTransaction(self.lenv)
        self._worker = self._workloop()
        self._worker.name = 'Axon Writer'

        async def fini():
            conn_future.cancel()
            for stop_event in self.blobstorwatchers.values():
                stop_event.set()
            await self._workq.fini()
            await self._proxykeeper.fini()
            self._worker.join()

        self.onfini(fini)

    def _get_stored_blobstorpaths(self):
        paths = []
        with self.lenv.begin(buffers=True) as xact, xact.cursor(db=self.settings) as curs:
            if not curs.set_key(b'blobstorpaths'):
                return []
            for path in curs.iternext_dup():
                paths.append(bytes(path).decode())
        return paths

    async def _start_watching_blobstor(self, blobstorpath: str):
        '''
        Raises:
            telepath openurl exceptions
        '''
        bsid, blobstor = await self._proxykeeper.connect(blobstorpath)
        stop_watching_event = asyncio.Event(loop=self.loop)
        self.blobstorwatchers[blobstorpath] = stop_watching_event

        self.schedCoro(self._watch_blobstor(blobstor, bsid, blobstorpath, stop_watching_event))

    async def addBlobStor(self, blobstorpath):
        '''
        Causes an axon to start using a particular blobstor.  This is persistently stored; on Axon restart, it will
        automatically reconnect to the blobstor at the specified path.
        '''
        def _store_blobstorpath(path):
            txn = self.xact.guarantee()
            txn.put(b'blobstorpaths', path.encode(), dupdata=True, db=self.settings)
            self.xact.commit()

        if blobstorpath in self.blobstorwatchers:
            return

        await self._start_watching_blobstor(blobstorpath)
        await self._executor(_store_blobstorpath, blobstorpath)

    async def getBlobStors(self):
        '''
        Returns:
            A list of all the watched blobstors
        '''
        return list(self.blobstorwatchers.keys())

    async def unwatchBlobStor(self, blobstorpath):
        '''
        Cause an axon to stop using a particular blobstor by path.  This is persistently stored.
        '''
        def _del_blobstorpath(path):
            txn = self.xact.guarantee()
            txn.delete(b'blobstorpaths', path.encode(), db=self.settings)
            self.xact.commit()

        stop_event = self.blobstorwatchers.pop(blobstorpath, None)
        if stop_event is not None:
            stop_event.set()
        await self._executor(_del_blobstorpath, blobstorpath)

    async def _watch_blobstor(self, blobstor, bsid, blobstorpath, stop_event):
        '''
        As Axon, Monitor a blobstor, by repeatedly asking long-poll-style for its new data
        '''
        logger.info('Watching BlobStor %s', _path_sanitize(blobstorpath))

        CLONE_TIMEOUT = 60.0
        cur_offset = self._getSyncProgress(bsid)
        while not self.isfini and not stop_event.is_set():
            try:
                if blobstor.isfini:
                    blobstor = await s_telepath.openurl(blobstorpath)

                async def clone_and_next():
                    ''' Get the async generator and the first item of that generator '''
                    genr = await blobstor.clone(cur_offset, timeout=CLONE_TIMEOUT, include_contents=False)
                    try:
                        it = genr.__aiter__()
                        first_item = await it.__anext__()
                        return it, first_item
                    except (StopAsyncIteration, s_exc.SynErr):
                        return None, None

                # Wait on either the clone completing, or a signal to stop watching (or the blobstor throwing isfini)
                stop_coro = stop_event.wait()
                donelist, notdonelist = await asyncio.wait([clone_and_next(), stop_coro],
                                                           return_when=concurrent.futures.FIRST_COMPLETED)
                for task in notdonelist:
                    task.cancel()
                if stop_event.is_set():
                    # avoid asyncio debug warnings by retrieving any done task exceptions
                    for f in donelist:
                        try:
                            f.result()
                        except Exception:
                            pass
                    break
                genr, first_item = donelist.pop().result()
                if genr is None:
                    continue

                logger.debug('Got clone data for %s', _path_sanitize(blobstorpath))
                cur_offset = 1 + await self._consume_clone_data(first_item, genr, bsid)
                await self._executor_nowait(self._updateSyncProgress, bsid, cur_offset)

            except s_exc.IsFini:
                continue

            except asyncio.CancelledError:
                break

            except ConnectionRefusedError:
                logger.warning('Trouble connecting to blobstor %s.  Will retry in %ss.', _path_sanitize(blobstorpath),
                               CLONE_TIMEOUT)
                await asyncio.sleep(CLONE_TIMEOUT)
            except Exception:
                logger.exception('BlobStor._watch_blobstor error on %s', _path_sanitize(blobstorpath))
                if not self.isfini:
                    logger.error(f'_watch_blobstor - asyncio.sleep({CLONE_TIMEOUT})')
                    await asyncio.sleep(CLONE_TIMEOUT)

    def _updateSyncProgress(self, bsid, new_offset):
        '''
        Persistently record how far we've gotten in retrieving the set of hash values a particular blobstor has

        Records the next offset to retrieve
        '''
        self.xact.put(b'offset:' + bsid, struct.pack('>Q', new_offset), db=self.offsets)

        self.xact.commit()

    def _getSyncProgress(self, bsid):
        '''
        Get the current offset for one blobstor of the Axon

        Returns:
            int: The offset value.
        '''
        with self.lenv.begin(buffers=True) as xact:

            lval = xact.get(b'offset:' + bsid, db=self.offsets)
            if lval is None:
                rv = 0
            else:
                rv = struct.unpack('>Q', lval)[0]
        return rv

    @s_common.firethread
    def _workloop(self):
        '''
        Axon:  A worker for running stuff that requires a write lock
        '''
        try:
            while not self.isfini:
                msg = self._workq.get()
                if msg is None:
                    break
                func, done_event = msg
                func()
                if done_event is not None:
                    self.schedCallSafe(done_event.set)
        finally:
            self.xact.fini()

    async def _executor_nowait(self, func, *args, **kwargs):
        '''
        Run a function on the Axon's work thread without waiting for a result
        '''
        def syncfunc():
            func(*args, **kwargs)

        await self._workq.put((syncfunc, None))

    async def _executor(self, func, *args, **kwargs):
        '''
        Run a function on the Axon's work thread
        '''
        done_event = asyncio.Event(loop=self.loop)
        retn = None

        def syncfunc():
            nonlocal retn
            retn = func(*args, **kwargs)

        await self._workq.put((syncfunc, done_event))
        await done_event.wait()
        return retn

    def _addloc(self, bsid, hashval, commit=False):
        '''
        Record blobstor's bsid has a particular hashval.  Should be run in my executor.
        '''
        xact = self.xact.guarantee()

        tick = s_common.now()

        written = xact.put(hashval, bsid, db=self.bloblocs, dupdata=False)

        if written:
            self._metrics.inc(xact, 'files', 1)

            # metrics contains everything we need to clone
            self._metrics.record(xact, {'time': tick, 'bsid': bsid, 'sha256': hashval})

            if commit:
                self.xact.commit()

    async def _consume_clone_data(self, first_item, items, frombsid):
        '''
        Add rows obtained from a BlobStor.clone() method.

        Args:
            items (Iterable): A list of tuples containing (offset, (sha256,chunknum,bytes)) data.

        Returns:
            int: The last index value processed from the list of items, or None if nothing was processed
        '''
        last_offset, (hashval, _, _) = first_item
        await self._executor_nowait(self._addloc, frombsid, hashval)

        async for last_offset, (hashval, _, _) in to_aiter(items):
            await self._executor_nowait(self._addloc, frombsid, hashval)

        await self._executor_nowait(self.xact.commit)

        return last_offset

    async def stat(self):
        bsstats = {}
        proxymap = self._proxykeeper.get_all()
        for path, blobstor in proxymap.items():
            if not blobstor.isfini:
                bsstats[_path_sanitize(path)] = await blobstor.stat()
        my_stats = self._metrics.stat()
        my_stats['blobstors'] = bsstats
        return my_stats

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
        Get the blobstor bsids for a given sha256 value

        Args:
            hashval (bytes): The sha256 digest to look up

        Returns:
            list: A list of BlobStor IDs
        '''
        with self.lenv.begin() as xact, xact.cursor(db=self.bloblocs) as curs:
            if not curs.set_key(hashval):
                return []
            blobstorbsids = []
            for bsid in curs.iternext_dup():
                blobstorbsids.append(bsid)
            return blobstorbsids

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
        bsid, blobstor = await proxykeeper.randoproxy()
        count = 0
        async with await blobstor.startput() as uploader:
            for bytz in files:
                hashval = hashlib.sha256(bytz).digest()
                if await self.wants([hashval]) == []:
                    continue
                for chunk in s_common.chunks(bytz, CHUNK_SIZE):
                    await uploader.write(chunk)
                await uploader.finishFile()
            count, hashval = await uploader.finish()
            if count:
                await self._executor_nowait(self._addloc, bsid, hashval)

        await self._executor(self.xact.commit)

        return count

    async def putone(self, bytz, hashval=None, proxykeeper=None):
        '''
        If hashval is None and or not None and not already in the axon, stores bytz as a single blob

        Returns:
            bytes:  The hash of bytz
        '''

        if hashval is not None:
            if await self.wants([hashval]) == []:
                return hashval

        if proxykeeper is None:
            proxykeeper = self._proxykeeper

        bsid, blobstor = await proxykeeper.randoproxy()

        _, hashval = await blobstor.putone(bytz)
        await self._executor(self._addloc, bsid, hashval, commit=True)
        return hashval

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
            raise s_exc.NoSuchFile(f'{hashval} not present')
        _, blobstor = await proxykeeper.randoproxy(locs)

        # that await is due to the current async generator telepath asymmetry
        async for bloc in await blobstor.get(hashval):
            yield bloc

    async def metrics(self, offs=0):
        with self.lenv.begin(buffers=True) as xact:
            for item in self._metrics.iter(xact, offs):
                yield item
