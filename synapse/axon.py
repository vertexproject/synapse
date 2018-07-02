import lmdb
import asyncio
import struct
import logging
import random
import hashlib
import contextlib
import tempfile

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.daemon as s_daemon

import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

zero64 = b'\x00' * 8
blocksize = s_const.mebibyte * 64

# FIXME:  allow axons to register for when new data arrives on blobstor

class PassThroughApi(s_cell.CellApi):
    ''' Class that passes through methods made on it to its cell. '''
    allowed_methods = []

    def __init__(self, cell, link):
        s_cell.CellApi.__init__(self, cell, link)

        for f in self.allowed_methods:
            # N.B. this curious double nesting is due to Python's closure mechanism (f is essentially captured by name)
            def funcapply(f):
                def func(*args, **kwargs):
                    return getattr(cell, f)(*args, **kwargs)
                return func
            setattr(self, f, funcapply(f))

class Uploader(s_telepath.Share):
    typename = 'uploader'
    BUF_SIZE = 16 * s_const.mebibyte

    def __init__(self, link, item):
        s_daemon.Share.__init__(self, link, item)
        self.doneevent = asyncio.Event()
        self.exitok = False
        self._init()
        # We delay getting the transaction (hence the write lock) until we have the first file
        self.xact = None
        self.tick = s_common.now()
        self.all_hashes = []
        self.totalsize = 0

        def _init(self):
            self.bytzfh = tempfile.SpooledTemporaryFile(buffering=self.BUF_SIZE)
            self.hashing = hashlib.sha256()

        async def fini():
            if self.exitok:
                self._save()
            else:
                self.bytzfh.close()
            del self.bytzfh
            if self.all_hashes:
                self._write_stats()
                self.xact.commit()
            elif self.xact:
                self.xact.abort()
            self.doneevent.set()
        self.onfini(fini)

    async def write(self, bytz):
        self.bytzfh.write(bytz)
        self.hashing.update(bytz)

    async def _runShareLoop(self):
        '''
        This keeps the object alive until we're fini'd.
        '''
        await self.doneevent.wait()

    async def finish(self):
        self.exitok = True
        self.fini()

    def _write_stats(self):
        self.item._save_update_stats(self.all_hashes, self.totalsize, self.tick, self.xact)

    async def _save(self):
        final_sha = self.hashing.digest()
        if self.xact is None:
            self.xact = self.item.lenv.begin(write=True, buffers=True)
        bytes_written = self.item._store_fh(self.bytzfh, final_sha, self.xact)
        if bytes_written:
            self.totalsize += bytes_written
            self.all_hashes.append(final_sha)

    async def finishFile(self):
        '''
        Finish and commit the existing file, keeping the uploader active for more files.
        '''
        self._save()
        self._init()

class BlobStorApi(PassThroughApi):

    allowed_methods = ['onsave', 'load', 'clone', 'stat', 'metrics', 'curPos', 'save', 'registerListener']

    def upload(self):
        return Uploader(self.link, self)

class BlobStor(s_cell.Cell):
    '''
    The blob store maps sha256 values to sequences of bytes stored in a LMDB database.
    '''
    CHUNK_SIZE = 16 * s_const.mebibyte
    CLONE_POLL_S = 60
    cellapi = BlobStorApi

    confdefs = (
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
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128, map_size=mapsize)

        self._blob_info = self.lenv.open_db(b'info')
        self._blob_bytes = self.lenv.open_db(b'bytes') # <sha256>=<byts>

        self._clone_seqn = s_lmdb.Seqn(self.lenv, b'clone')
        self._blob_metrics = s_lmdb.Metrics(self.lenv)

        self.cloneof = self.conf.get('cloneof')
        self.listeners = {}

        if self.cloneof is not None:
            self.clonetask = s_glob.plex.coroToTask(self._cloneeLoop(self.cloneof))

        def fini():
            self.lenv.close()

        self.onfini(fini)

    def registerListener(self, path):
        if path not in self.listeners:
            self.listeners[path] = None

    async def _cloneeLoop(self, cloneepath):
        ROWS_AT_A_TIME = 128
        clonee = s_telepath.openurl(cloneepath)
        while not self.isfini:
            try:
                if clonee.isfini:
                    clonee = s_telepath.openurl(cloneepath)

                offs = self.getCloneOffs()
                for row in clonee.clone(s_common.chunks(offs, ROWS_AT_A_TIME)):
                    self.blobs._consume_clone_rows([row])
                asyncio.sleep(self.CLONE_POLL_S)

            except Exception:
                if not self.isfini:
                    logger.exception('BlobStor.cloneeLoop error')
                    asyncio.sleep(self.CLONE_POLL_S)

    def _find_hash(self, curs, key):
        '''
        Returns false if key not present, else returns true and positions cursor at first chunk of value
        '''
        if not curs.set_range(key):
            return False
        return curs.key()[:len(key)] == key

    def bulkput(self, blocs):
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
        with self.lenv.begin(write=True, buffers=True) as xact:
            # FIXME: worry about transactions too large
            self._bulkput(blocs, xact)

    def put(self, item):
        self.bulkput((None, 0, item))

    def putmany(self, items):
        self.bulkput((None, 0, i) for i in items)

    def _store_fh(self, fh, sha256, xact):
        MAX_VAL_SIZE = 2**31  # Actually lmdb takes up to 2**32, but this is a nice round number
        count = 0

        with contextlib.closing(fh):
            # Check if already present
            with xact.cursor(db=self._blob_bytes) as curs:
                if self._find_hash(curs, sha256):
                    return None
            fh.seek(0)
            i = 0
            while True:
                chunk = fh.read(MAX_VAL_SIZE)
                sz = len(chunk)
                count += sz
                # We want to write *something* if data is empty
                if i and not sz:
                    break
                i_enc = i.to_bytes(4, 'big')
                xact.put(sha256 + i_enc, chunk, db=self._blob_bytes)
                i += 1
        return count

    def _save_update_stats(self, clones, size, tick, xact):
        self._clone_seqn.save(xact, clones)
        self._blob_metrics.inc(xact, 'bytes', size)
        self._blob_metrics.inc(xact, 'blobs', len(clones))

        took = s_common.now() - tick
        self._blob_metrics.record(xact, {'time': tick, 'size': size, 'took': took})

    def _bulkput(self, blocs, xact):
        '''
        Private version of bulkput that takes a passed-in transaction
        '''
        BUF_SIZE = 16 * s_const.mebibyte

        clones = []
        tick = s_common.now()
        last_chunknum = None
        bytzfh = None
        hashing = None
        total = 0
        skip_this_hash = False

        def storeit():
            nonlocal total, bytzfh
            final_hash = hashing.digest()
            print('Writing hash', final_hash)
            bytes_written = self._store_fh(bytzfh, final_hash, xact)
            bytzfh = None
            if bytes_written is not None:
                clones.append(final_hash)
                total += bytes_written

        for sha256, (chunknum, bytz) in blocs:
            if chunknum == 0:
                if bytzfh:
                    storeit()
                if not bytzfh:
                    last_chunknum = None
                    if sha256 is not None:
                        with xact.cursor(db=self._blob_bytes) as curs:
                            skip_this_hash = self._find_hash(curs, sha256)
                    else:
                        skip_this_hash = False
                    if not skip_this_hash:
                        bytzfh = tempfile.SpooledTemporaryFile(buffering=BUF_SIZE)
                        hashing = hashlib.sha256()

            elif sha256 is not None:
                raise s_exc.AxonBadChunk('sha256 present past the first chunk')
            elif chunknum - 1 != last_chunknum:
                raise s_exc.AxonBadChunk('Chunks out of sequence')
            last_chunknum = chunknum

            if not skip_this_hash:
                bytzfh.write(bytz)
                hashing.update(bytz)

        # Store the last chunk
        if bytzfh:
            storeit()
        if clones:
            self._save_update_stats(clones, total, tick, xact)

        # FIXME: partial commits, write-lock for writes

    def get(self, sha256):
        '''
        Load and yield the bytes blocks for a given hash.

        Args:
            sha256 (bytes): Buid to retrieve bytes for.

        Yields:
            bytes: Bytes for a given buid, in order.
        '''
        with self.lenv.begin(db=self._blob_bytes, buffers=True) as xact:
            yield from self._get(sha256, xact)

    def _get(self, sha256, xact):
        with xact.cursor(db=self._blob_bytes) as curs:
            if not self._find_hash(curs, sha256):
                return None
            for k, v in curs:
                if not k[:len(sha256)] == sha256:
                    return None
                yield from s_common.chunks(v, self.CHUNK_SIZE)

    def clone(self, offset):
        '''
        Yield (offset, (sha256, chunknum, bytes)) tuples to clone this BlobStor.

        Args:
            offset (int): Offset to start yielding rows from.

        Yields:
            ((bytes, (bytes, int, bytes))): tuples of (index, (sha256,chunknum,bytes)) data.
        '''
        with self.lenv.begin(buffers=True) as xact:
            for off, sha256 in self._clone_seqn.iter(xact, offset):
                for chunknum, chunk in enumerate(self._get(sha256, xact)):
                    yield off, (None if chunknum else sha256, chunknum, bytes(chunk))

    def _consume_clone_data(self, items):
        '''
        Add rows obtained from a BlobStor.clone() method.

        Args:
            items (Iterable): A list of tuples containing (offset, (sha256,chunknum,bytes)) data.

        Returns:
            int: The last index value processed from the list of items.
        '''

        if not items:
            return

        last_offset = None

        def yielder(i, xact):
            nonlocal last_offset
            for offset, (sha256, chunknum, bytz) in i:
                yield sha256, (chunknum, bytz)
                if offset != last_offset:
                    if last_offset is not None:
                        self._clone_seqn.save(xact, [last_offset])
                    last_offset = offset

        # FIXME: commit after X bytes processed
        with self.lenv.begin(write=True, buffers=True, db=self._blob_bytes) as xact:
            self._bulkput(yielder(items, xact), xact)
            xact.put(b'clone:offset', struct.pack('>Q', last_offset), db=self._blob_info)
            return last_offset

    def stat(self):
        '''
        Get storage stats for the BlobStor.

        Returns:
            dict: A dictionary containing the total bytes and blocks store in the BlobStor.
        '''
        return self._blob_metrics.stat()

    def metrics(self, offs=0):
        '''
        Get metrics for the BlobStor. These can be aggregated to compute the storage stats.

        Args:
            offs (int): Offset to start collecting stats from.

        Yields:
            ((int, dict)): Yields index, sample data from the metrics sequence.
        '''
        with self.lenv.begin(buffers=True) as xact:
            for item in self._blob_metrics.iter(xact, offs):
                yield item

    def offset(self):
        '''
        Get the current offset for the clone:index of the BlobStor.

        Returns:
            int: The offset value.
        '''
        with self.lenv.begin(buffers=True) as xact:

            lval = xact.get(b'clone:indx', db=self._blob_info)
            if lval is None:
                return 0

            return struct.unpack('>Q', lval)[0] + 1

class AxonApi(PassThroughApi):
    allowed_methods = ['startput', 'bulkput', 'get', 'locs', 'stat', 'wants', 'upload', 'metrics']

    def startUpload(self):
        raise NotImplemented

class Axon(s_cell.Cell):

    cellapi = AxonApi
    confdefs = (
        ('mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE, 'doc': 'The size of the LMDB memory map'}),
        ('blobs', {'req': True, 'doc': 'A list of cell names', 'defval': []}),
    )

    def _init_blobstors(self):
        for blobstorname in self.blobstornames:
            logger.info('Bringing BlobStor %s online', blobstorname)
            blobstor = self._blobstor_by_name(blobstorname)
            self._blobstorprox = blobstor
            if blobstor is not None:
                self._blobstorbuid[blobstor.getCellIden()] = blobstor

    def _blobstor_by_buid(self, buid):
        blobstorname = self._blobstorbuid[buid]
        if blobstorname is None:
            raise Exception(f'Encountered unknown BlobStor buid {buid}')
        return self._get_blobstor_by_name(blobstorname)

    def _blobstor_by_name(self, blobstorname):
        '''
        Retrieve a blobstor proxy by name.
        '''
        # TODO: give up on a blobstor after too many failures
        blobstor = self._blobstorprox.get(blobstorname, s_common.NoValu)
        if blobstorname is s_common.NoValu:
            raise s_exc.BadUrl(f'Unexpected blobstor path {blobstorname}')
        if blobstor is None or blobstor.isfini:
            try:
                s_telepath.openurl(blobstorname)
                if blobstor is not None:
                    self._blobstorbuid[blobstor.getCellIden()] = blobstor
                    # FIXME: register me(axon) with blobstor
                self._blobstorprox[blobstorname] = blobstor
                return blobstor
            except Exception:
                logger.exception('openurl(%s) failure', blobstorname)
                return None
        return blobstor

    def __init__(self, dirn: str, conf=None) -> None:
        s_cell.Cell.__init__(self, dirn)

        path = s_common.gendir(self.dirn, 'axon.lmdb')
        mapsize = self.conf.get('mapsize')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.blobhas = self.lenv.open_db(b'axon:blob:has') # <sha256>=<size>
        self.bloblocs = self.lenv.open_db(b'axon:blob:locs', dupsort=True, dupfixed=True) # <sha256>=blobstor_buid

        self._metrics = s_lmdb.Metrics(self.lenv)

        self.blobstornames = self.conf.get('blobs')
        self._blobstorprox = {}  # name -> blobstor proxy
        self._blobstorbuid = {}  # buid -> name

        self._init_blobstors()

        def fini():
            self.lenv.close()
            for blobstor in self._blobstorprox.values():
                if blobstor is not None:
                    blobstor.fini()

        self.onfini(fini)

    def stat(self):
        return self._metrics.stat()

    def wants(self, hashes):
        '''
        Given a list of hashes, returns a list of the hashes *not* available
        '''
        wants = []
        with self.lenv.begin(db=self.blobhas) as xact:
            curs = xact.cursor()
            for sha256 in hashes:
                if not curs.set_key(sha256):
                    wants.append(sha256)
        return wants

    def locs(self, sha256):
        '''
        Get the blobstor buids for a given sha256 value

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            sha256 (bytes): The sha256 digest to look up

        Returns:
            list: A list of blobnames
        '''
        with self.lenv.begin() as xact, xact.cursor(db=self.bloblocs) as curs:
            if not curs.set_key(sha256):
                return []
            blobstorbuids = []
            for buid in curs.iternext_dup():
                blobstorbuids.append(blobstorbuids)
            return blobstorbuids

    def _randoblobstor(self, items=None):
        # FIXME: fix list of buids vs. list of names
        # FIXME: return blobstor buid
        if items is None:
            items = self.blobstorenames
        rot = random.range(len(items))
        blobstornames = items[rot:] + items[:rot]
        # TODO: give up on a blobstor after too many failures to connect
        for blobstorname in self._randrotate(blobstornames):
            blobstor = self._blobstor_by_name(blobstorname)
            if blobstor is not None:
                return blobstor
        raise Exception('No blobstors available')

    def startput(self):
        '''
        Args:
            None

        Returns:
            an Uploader object suitable for streaming an upload
        '''
        blobstor, blobstorbuid = self._randoblobstor()
        return blobstor.startput()

    def bulkput(self, files):
        '''
        Save a list of files to the axon.

        Args:
            files ([bytes]): A list of files as bytes blobs.

        Returns:
            int: The number of files saved.
        '''
        blobstor, blobstorbuid = self._randoblobstor()
        count = 0
        with blobstor.startput() as uploader:
            for bytz in files:
                for chunk in s_common.chunks(self.CHUNK_SIZE):
                    uploader.write(chunk)
                sha256 = uploader.finishFile()
                count += 1
        with self.lenv.begin(write=True, buffer=True) as xact:
            self._addloc(sha256, len(bytz), blobstorbuid, xact)
        return count

    def get(self, sha256):
        '''
        Yield bytes for the given SHA256.

        Args:
            sha256 (str): The SHA256 hash bytes.

        Yields:
            bytes: Bytes of the file requested.

        Raises:
            RetnErr: If the file requested does not exist.
        '''
        locs = self.locs(sha256)
        if not locs:
            raise s_exc.NoSuchFile()
        blobstorbuids = self._randrotate(locs)
        for buid in blobstorbuids:
            blobstor = self._get_blobstor_by_buid(buid)
            if blobstor is not None:
                break
        else:
            raise Exception('No blobstors available')

        yield from blobstor.load(sha256)

    def metrics(self, offs=0):
        with self.lenv.begin(buffers=True) as xact:
            yield from s_common.chunks(self._metrics.iter(xact, offs), 1024)
