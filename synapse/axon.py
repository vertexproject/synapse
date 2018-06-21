import os
import lmdb
import asyncio
import struct
import logging
import random
import hashlib
import itertools
import tempfile

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

zero64 = b'\x00' * 8
blocksize = s_const.mebibyte * 64

# FIXME:  allow axons to register for when new data arrives on blobstor

class BlobStorApi(s_cell.CellApi):
    def save(self, blocs):
        # FIXME:  genr uploader thing '''
        return self.cell.save(blocs)

    def load(self, sha256):
        return self.cell.load(sha256)

    def clone(self, offs):
        yield from self.cell.clone(offs)

    def stat(self):
        return self.cell.stat()

    def metrics(self, offs=0):
        return self.cell.metrics(offs)

    def getCloneOffs(self):
        return self.cell.getCloneOffs()

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

        if self.cloneof is not None:
            self.clonetask = s_glob.plex.coroToTask(self._cloneeLoop(self.cloneof))

        def fini():
            self.lenv.close()

        self.onfini(fini)

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

    def save(self, blocs):
        '''
        Save items from an iterator of (chunk #, <bytes>).

        Args:
            blocs: An iterator of (chunk #, <bytes>).  Every 0 chunk # represents a new file

        Notes:
            This API is only for use by a single Axon who owns this BlobStor.

        Returns:
            None
        '''
        with self.lenv.begin(write=True, buffers=True) as xact:
            self._save(blocs, xact)

    def _save(self, blocs, xact):
        '''
        Private version of save that takes a passed-in transaction
        '''
        BUF_SIZE = 16 * s_const.mebibyte

        size = 0
        hashes = 0
        clones = []
        tick = s_common.now()
        last_chunknum = None
        bytzfh = None
        hashing = None

        def saveit():
            nonlocal hashes, bytzfh
            bytzfh.seek(0)
            sha256 = hashing.digest()
            # FIXME: limit val to 2**32
            # FIXME: check if already stored
            xact.put(sha256, bytzfh.read(), db=self._blob_bytes)
            bytzfh.close()
            oldbytesfh, bytzfh = bytzfh, None
            del oldbytesfh
            clones.append(sha256)
            hashes += 1

        for chunknum, bytz in blocs:
            if chunknum == 0:
                if bytzfh is not None:
                    saveit()
                bytzfh = tempfile.SpooledTemporaryFile(buffering=BUF_SIZE)
                hashing = hashlib.sha256()
                last_chunknum = None
            elif chunknum - 1 != last_chunknum:
                raise s_exc.AxonBadChunk('Chunks out of sequence')

            size += len(bytz)

            bytzfh.write(bytz)
            hashing.update(bytz)
            last_chunknum = chunknum

        # Store the last chunk
        saveit()

        self._clone_seqn.save(xact, clones)
        self._blob_metrics.inc(xact, 'bytes', size)
        self._blob_metrics.inc(xact, 'hashes', hashes)

        took = s_common.now() - tick
        self._blob_metrics.record(xact, {'time': tick, 'size': size, 'blocks': hashes, 'took': took})

    def load(self, sha256):
        '''
        Load and yield the bytes blocks for a given hash.

        Args:
            sha256 (bytes): Buid to retrieve bytes for.

        Yields:
            bytes: Bytes for a given buid, in order.
        '''
        with self.lenv.begin(db=self._blob_bytes, buffers=True) as xact:
            bytz = xact.get(sha256)
            if bytz is None:
                return
            yield from s_common.chunks(bytz, self.CHUNK_SIZE_B)

    def clone(self, offset):
        '''
        Yield (offset, (sha256, chunknum, bytes)) tuples to clone this BlobStor.

        Args:
            offset (int): Offset to start yielding rows from.

        Yields:
            ((bytes, (bytes, int, bytes))): tuples of (index, (sha256,bytes)) data.
        '''
        with self.lenv.begin(buffers=True) as xact:
            curs = xact.cursor(db=self._blob_bytes)
            for off, sha256 in self._clone_seqn.iter(xact, offset):
                byts = curs.get(sha256)
                if byts is None:
                    raise s_exc.CorruptDatabase('missing blob value with hash %s', sha256)
                for chunknum, chunk in enumerate(s_common.chunks(byts, self.CHUNK_SIZE_B)):
                    yield off, (sha256, chunknum, byts)

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

        with self.lenv.begin(write=True, buffers=True, db=self._blob_bytes) as xact:
            self._save(yielder(items, xact), xact)
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

    def getCloneOffs(self):
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

class AxonApi(PassThroughApi):
    allowed_methods = ['locs', 'stat', 'save', 'wants', 'upload', 'bytes', 'metrics']

    def startUpload(self):
        raise NotImplemented

# FIXME:  clones tell axon about clone info

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
        Retrieve a blobstor proxy by name.  If not connected
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
            for blobstor in self._blobstor.values():
                if blobstor is not None:
                    blobstor.fini()

        self.onfini(fini)

    def stat(self):
        return self._metrics.stat()

    def wants(self, hashes):
        wants = []
        with self.lenv.begin(db=self.blobhas) as xact:
            curs = xact.cursor()
            for sha256 in hashes:
                if not curs.set_key(sha256):
                    wants.append(sha256)
        return wants

    def locs(self, sha256):
        '''
        Get the blobnames for a given sha256 value

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            sha256 (bytes): The sha256 digest to look up

        Returns:
            list: A list of blobnames
        '''
        with self.lenv.begin() as xact, xact.cursor(db=self.bloblocs) as curs:
            if not curs.set_key(sha256):
                return []
            blobstornames = []
            for buid in curs.iternext_dup():
                blobstorname = self._blobstorbuid.get(buid)
                if blobstorname is None:
                    logger.warning('Encountered unknown blobstor buid')
                    continue
                blobstornames.append(blobstorname)
            return blobstornames

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

    def upload(self, genr):
        '''
        Args:

        Returns:
            bytes: The sha256 digest of the file received, in bytes.
        '''
        blobstor = self._randoblobstor()
        uploader = blobstor.startUpload()
        for chunk in genr:
            uploader.write(chunk)
        return uploader.finish()

    def save(self, files):
        '''
        Save a list of files to the axon.

        Args:
            files ([bytes]): A list of files as bytes blobs.

        Returns:
            int: The number of files saved.
        '''
        blobstor, blobstorbuid = self._randoblobstor()
        count = 0
        with blobstor.startUpload() as uploader:
            for bytz in files:
                for chunk in s_common.chunks(self.CHUNK_SIZE):
                    uploader.write(chunk)
                sha256 = uploader.finishFile()
                count += 1
        with self.lenv.begin(write=True, buffer=True) as xact:
            self._addloc(sha256, len(bytz), blobstorbuid, xact)
        return count

    def bytes(self, sha256):
        '''
        Yield bytes for the given SHA256.

        Args:
            sha256 (str): The SHA256 hash bytes.

        Yields:
            bytes: Bytes of the file requested.

        Raises:
            RetnErr: If the file requested does not exist.
        '''
        locs = self._getBlobLocs(sha256)
        if not locs:
            raise s_exc.NoSuchFile()
        blobstornames = self._randrotate(locs)
        for blobstorname in blobstornames:
            blobstor = self._get_blobstor_by_name(blobstorname)
            if blobstor is None:
                continue
        else:
            raise Exception('No blobstors available')

        yield from blobstor.load(sha256)

    def metrics(self, offs=0):
        with self.lenv.begin(buffers=True) as xact:
            yield from s_common.chunks(self._metrics.iter(xact, offs), 1024)
