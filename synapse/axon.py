import time
import lmdb
import struct
import logging
import hashlib
import itertools

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.net as s_net
import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const
import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

zero64 = b'\x00\x00\x00\x00\x00\x00\x00\x00'
blocksize = s_const.mebibyte * 64

class BlobStor(s_eventbus.EventBus):
    '''
    The blob store maps buid,indx values to sequences of bytes stored in a LMDB database.
    '''

    def __init__(self, dirn, mapsize=s_const.tebibyte):

        s_eventbus.EventBus.__init__(self)

        path = s_common.gendir(dirn, 'blobs.lmdb')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self._blob_info = self.lenv.open_db(b'info')
        self._blob_bytes = self.lenv.open_db(b'bytes') # <fidn><foff>=<byts>

        self._blob_clone = s_lmdb.Seqn(self.lenv, b'clone')
        self._blob_metrics = s_lmdb.Metrics(self.lenv)

        def fini():
            self.lenv.sync()
            self.lenv.close()

        self.onfini(fini)

    def save(self, blocs):
        '''
        Save items from an iterator of (<buid><indx>, <byts>).

        Args:
            blocs: An iterator of (<buid><indx>, <bytes>).

        Notes:
            This API is only for use by a single Axon who owns this BlobStor.

        Returns:
            None
        '''
        with self.lenv.begin(write=True, db=self._blob_bytes) as xact:

            size = 0
            count = 0
            clones = []
            tick = s_common.now()

            for lkey, lval in blocs:
                clones.append(lkey)
                xact.put(lkey, lval, db=self._blob_bytes)

                size += len(lval)
                count += 1

            self._blob_clone.save(xact, clones)
            self._blob_metrics.inc(xact, 'bytes', size)
            self._blob_metrics.inc(xact, 'blocks', count)

            took = s_common.now() - tick
            self._blob_metrics.record(xact, {'time': tick, 'size': size, 'blocks': count, 'took': took})

    def load(self, buid):
        '''
        Load and yield the bytes blocks for a given buid.

        Args:
            buid (bytes): Buid to retrieve bytes for.

        Yields:
            bytes: Bytes for a given buid, in order.
        '''
        with self.lenv.begin(db=self._blob_bytes, buffers=True) as xact:

            curs = xact.cursor()
            if not curs.set_range(buid):
                return

            for lkey, byts in curs.iternext():

                if lkey[:32] != buid:
                    break

                yield byts

    def clone(self, offs):
        '''
        Yield (indx, (lkey, lval)) tuples to clone this BlobStor.

        Args:
            offs (int): Offset to start yielding rows from.

        Yields:
            ((bytes, (bytes, bytes))): tuples of (index, (<buid><index>,bytes)) data.
        '''
        with self.lenv.begin() as xact:
            curs = xact.cursor(db=self._blob_bytes)
            for indx, lkey in self._blob_clone.iter(xact, offs):
                byts = curs.get(lkey)
                yield indx, (lkey, byts)

    def addCloneRows(self, items):
        '''
        Add rows from obtained from a BlobStor.clone() method.

        Args:
            items (list): A list of tuples containing (index, (<buid><index>,bytes)) data.

        Returns:
            int: The last index value processed from the list of items.
        '''

        if not items:
            return

        with self.lenv.begin(write=True, db=self._blob_bytes) as xact:

            clones = []
            for indx, (lkey, lval) in items:
                xact.put(lkey, lval)
                clones.append(lkey)

            xact.put(b'clone:indx', struct.pack('>Q', indx), db=self._blob_info)
            self._blob_clone.save(xact, clones)
            return indx

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
        with self.lenv.begin() as xact:
            for item in self._blob_metrics.iter(xact, offs):
                yield item

    def getCloneOffs(self):
        '''
        Get the current offset for the clone:index of the BlobStor.

        Returns:
            int: The offset value.
        '''
        with self.lenv.begin() as xact:

            lval = xact.get(b'clone:indx', db=self._blob_info)
            if lval is None:
                return 0

            return struct.unpack('>Q', lval)[0] + 1

class BlobCell(s_cell.Cell):

    def postCell(self):

        if self.neuraddr is None:
            raise s_common.BadConfValu(mesg='BlobCell requires a neuron')

        path = self.getCellDir('blobs.lmdb')
        mapsize = self.getConfOpt('blob:mapsize')

        self.blobs = BlobStor(path, mapsize=mapsize)
        self.cloneof = self.getConfOpt('blob:cloneof')

        if self.cloneof is not None:
            self.cellpool.add(self.cloneof, self._fireCloneThread)
            self.cellinfo['blob:cloneof'] = self.cloneof

    def finiCell(self):
        self.blobs.fini()

    def _saveDispItems(self, items):

        def genr():

            for link, mesg in items:

                with link:

                    rows = mesg[1].get('rows', ())
                    for row in rows:
                        yield row

                    link.txok(len(rows))

        self.blobs.save(genr())

    @s_common.firethread
    def _fireCloneThread(self, sess):
        '''
        Fires a thread which requests clone rows from a given offset
        for the remote blob.
        '''
        while not sess.isfini:

            try:

                offs = self.blobs.getCloneOffs()

                mesg = ('blob:clone', {'offs': offs})
                ok, rows = sess.call(mesg, timeout=60)

                if not ok or not rows:
                    sess.waitfini(timeout=1)
                    continue

                self.blobs.addCloneRows(rows)
                self.fire('blob:clone:rows', size=len(rows))

            except Exception as e:
                if not sess.isfini:
                    logger.exception('BlobCell clone thread error')
                    time.sleep(1)

    def handlers(self):
        self.savedisp = s_net.LinkDisp(self._saveDispItems)
        return {
            'blob:save': self.savedisp.rx, # ('blob:save', {'rows':[ (lkey, lval)]})
            'blob:load': self._onBlobLoad, # ('blob:load', {'buid': <buid>} )
            'blob:stat': self._onBlobStat, # ('blob:stat', {}) -> (True, {info})
            'blob:clone': self._onBlobClone, # ('blob:clone', {'offs': <indx>}) -> [ (indx, (lkey, lval)), ]
            'blob:upload': self._onBlobUpload,
            'blob:metrics': self._onBlobMetrics, # ('metrics', {'offs':<indx>}) -> ( (indx, info), ... )
        }

    @s_glob.inpool
    def _onBlobClone(self, chan, mesg):
        with chan:
            offs = mesg[1].get('offs')
            genr = self.blobs.clone(offs)
            rows = list(itertools.islice(genr, 1000))
            chan.txok(rows)

    @s_glob.inpool
    def _onBlobUpload(self, chan, mesg):

        with chan:

            chan.setq()
            self.fire('blob:upload')

            chan.txok(True)
            for row in chan.rxwind(timeout=60):
                self.blobs.save([row])

    @s_glob.inpool
    def _onBlobStat(self, chan, mesg):
        with chan:
            chan.txok(self.blobs.stat())

    @s_glob.inpool
    def _onBlobMetrics(self, chan, mesg):

        offs = mesg[1].get('offs', 0)
        with chan:
            chan.setq()
            chan.txok(True)

            metr = self.blobs.metrics(offs=offs)
            genr = s_common.chunks(metr, 1000)

            chan.txwind(genr, 100, timeout=30)

    @s_glob.inpool
    def _onBlobLoad(self, chan, mesg):
        buid = mesg[1].get('buid')
        with chan:
            chan.setq()
            chan.txok(None)

            def genr():
                for byts in self.blobs.load(buid):
                    yield byts

            chan.txwind(genr(), 10, timeout=30)

    @staticmethod
    @s_config.confdef(name='blob')
    def _getBlobConfDefs():
        return (
            ('blob:mapsize', {'type': 'int', 'defval': s_const.tebibyte * 10,
                'doc': 'The maximum size of the LMDB memory map'}),

            ('blob:cloneof', {'defval': None,
                'doc': 'The name of a blob cell to clone from'}),
        )

class AxonCell(s_cell.Cell):
    '''
    An Axon acts as an indexer and manages access to BlobCell bytes.
    '''
    def postCell(self):

        if self.cellpool is None:
            raise s_common.BadConfValu(mesg='AxonCell requires a neuron and CellPool')

        mapsize = self.getConfOpt('axon:mapsize')

        path = self.getCellDir('axon.lmdb')

        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.blobhas = self.lenv.open_db(b'axon:blob:has') # <sha256>=<size>
        self.bloblocs = self.lenv.open_db(b'axon:blob:locs') # <sha256><loc>=<buid>

        self.metrics = s_lmdb.Metrics(self.lenv)

        self.blobs = s_cell.CellPool(self.cellauth, self.neuraddr)
        self.blobs.neurwait(timeout=10)

        for name in self.getConfOpt('axon:blobs'):
            self.blobs.add(name)

    def finiCell(self):
        self.lenv.sync()
        self.lenv.close()
        self.blobs.fini()

    def handlers(self):
        return {
            'axon:locs': self._onAxonLocs,
            'axon:save': self._onAxonSave,
            'axon:stat': self._onAxonStat,
            'axon:wants': self._onAxonWants,
            'axon:bytes': self._onAxonBytes,
            'axon:upload': self._onAxonUpload,
            'axon:metrics': self._onAxonMetrics,
        }

    @s_glob.inpool
    def _onAxonUpload(self, chan, mesg):

        with chan:

            chan.setq()

            ok, retn = self.blobs.any()
            if not ok:
                return chan.txerr(retn)

            name, sess = retn

            info = {'size': 0}
            buid = s_common.buid()

            sha256 = hashlib.sha256()

            def genr():

                indx = 0

                allb = b''
                for byts in chan.rxwind(timeout=30):

                    sha256.update(byts)
                    info['size'] += len(byts)

                    allb += byts
                    while len(allb) >= blocksize:

                        bloc = allb[:blocksize]
                        allb = allb[blocksize:]

                        lkey = buid + struct.pack('>Q', indx)
                        indx += 1

                        yield lkey, bloc

                if allb or (indx is 0):
                    lkey = buid + struct.pack('>Q', indx)
                    yield lkey, allb

            with sess.chan() as bchan:

                bchan.setq()

                bchan.tx(('blob:upload', {}))
                ok, retn = bchan.next(timeout=30)
                if not ok:
                    chan.txerr(retn)

                chan.txok(True)

                if bchan.txwind(genr(), 10, timeout=30):

                    size = info.get('size')
                    with self.lenv.begin(write=True) as xact:
                        self._addFileLoc(xact, buid, sha256.digest(), size, name)

            chan.txok(sha256.digest())

    def _addFileLoc(self, xact, buid, sha256, size, name):

        tick = s_common.now()

        nenc = name.encode('utf8')

        xact.put(sha256, struct.pack('>Q', size), db=self.blobhas)
        xact.put(sha256 + nenc, buid, db=self.bloblocs)

        self.metrics.inc(xact, 'files', 1)
        self.metrics.inc(xact, 'bytes', size)

        # metrics contains everything we need to clone
        self.metrics.record(xact, {'time': tick, 'cell': name, 'size': size, 'buid': buid, 'sha256': sha256})

    def _onAxonStat(self, chan, mesg):
        with chan:
            return chan.txok(self.metrics.stat())

    @s_glob.inpool
    def _onAxonMetrics(self, chan, mesg):
        offs = mesg[1].get('offs', 0)

        chan.setq()
        chan.txok(True)

        with self.lenv.begin() as xact:
            metr = self.metrics.iter(xact, offs)
            genr = s_common.chunks(metr, 1000)
            chan.txwind(genr, 100, timeout=30)
            chan.txfini()

    @s_glob.inpool
    def _onAxonWants(self, chan, mesg):

        # ('axon:wants', {'hashes': [sha256, ...]})
        with chan:

            wants = []
            hashes = mesg[1].get('hashes', ())

            with self.lenv.begin(db=self.blobhas) as xact:

                curs = xact.cursor()

                for sha256 in hashes:
                    if not curs.set_key(sha256):
                        wants.append(sha256)

            chan.txok(wants)

    @s_glob.inpool
    def _onAxonLocs(self, chan, mesg):
        with chan:
            sha256 = mesg[1].get('sha256')
            with self.lenv.begin() as xact:
                locs = self.getBlobLocs(xact, sha256)
            if not locs:
                return chan.txerr(('NoSuchFile', {}))
            return chan.txok(locs)

    @s_glob.inpool
    def _onAxonBytes(self, chan, mesg):

        with chan:

            chan.setq()

            sha256 = mesg[1].get('sha256')

            with self.lenv.begin() as xact:
                locs = self.getBlobLocs(xact, sha256)

            if not locs:
                return chan.txerr(('NoSuchFile', {}))
            sess = None
            buid = None

            for name, buid in locs:
                sess = self.blobs.get(name)
                if sess is not None:
                    break

            if sess is None:
                return chan.txerr(('NotReady', {}))

            with sess.chan() as bchan:

                bchan.setq()
                bchan.tx(('blob:load', {'buid': buid}))

                ok, retn = bchan.next(timeout=30)
                if not ok:
                    return chan.txerr(retn)

                chan.txok(name)

                def genr():
                    for byts in bchan.rxwind(timeout=30):
                        yield byts

                chan.txwind(genr(), 10, timeout=30)

    def getBlobLocs(self, xact, sha256):
        '''
        Get the blob and buids for a given sha256 value

        Args:
            xact (lmdb.Transaction): An LMDB transaction.
            sha256 (bytes): The sha256 digest to look up in bytes.

        Returns:
            list: A list of (blobname, buid) tuples.
        '''
        with xact.cursor(db=self.bloblocs) as curs:

            if not curs.set_range(sha256):
                return ()

            locs = []

            for lkey, buid in curs.iternext():
                if lkey[:32] != sha256:
                    break

                cellname = lkey[32:].decode('utf8')
                locs.append((cellname, buid))

            return locs

    def _filtSaveByts(self, files):

        todo = []
        with self.lenv.begin() as xact:

            curs = xact.cursor(db=self.blobhas)
            for byts in files:

                sha256 = hashlib.sha256(byts).digest()

                if curs.get(sha256):
                    continue

                todo.append((s_common.buid(), sha256, byts))

        return todo

    def _saveBlobByts(self, todo):

        rows = []
        for buid, sha256, byts in todo:
            for i, ibyts in enumerate(s_common.chunks(byts, blocksize)):
                indx = struct.pack('>Q', i)
                rows.append((buid + indx, ibyts))

        ok, retn = self.blobs.any()
        if not ok:
            return False, retn

        name, cell = retn

        mesg = ('blob:save', {'rows': rows})

        ok, retn = cell.call(mesg, timeout=30)
        if not ok:
            return False, retn

        return True, name

    @s_glob.inpool
    def _onAxonSave(self, chan, mesg):

        with chan:

            files = mesg[1].get('files', ())
            if not files:
                return chan.txok(0)

            todo = self._filtSaveByts(files)

            # if there is nothing to do after deconfliction, bail
            if not todo:
                return chan.txok(0)

            ok, retn = self._saveBlobByts(todo)
            if not ok:
                logger.warning('axon:save failed save blobs: %r' % (retn,))
                return chan.txerr(retn)

            name = retn
            with self.lenv.begin(write=True) as xact:
                for buid, sha256, byts in todo:
                    self._addFileLoc(xact, buid, sha256, len(byts), name)

            return chan.txok(len(todo))

    @staticmethod
    @s_config.confdef(name='axon')
    def _getAxonConfDefs():
        return (
            ('axon:mapsize', {'type': 'int', 'defval': s_const.tebibyte,
                'doc': 'The maximum size of the LMDB memory map'}),

            ('axon:blobs', {'req': True,
                'doc': 'A list of cell names in a neuron cluster'}),
        )

class AxonClient:

    def __init__(self, sess):
        self.sess = sess

    def locs(self, sha256, timeout=None):
        '''
        Get the Blob hostname and buid pairs for a given sha256.

        Args:
            sha256 (bytes): Sha256 to look up.
            timeout (int): The network timeout in seconds.

        Returns:
            tuple: A tuple of (blob, buid) tuples.

        Raises:
            RetnErr: If the file requested does not exist.
        '''
        mesg = ('axon:locs', {'sha256': sha256})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)

    def stat(self, timeout=None):
        '''
        Return the stat dictionary for the Axon.

        Args:
            timeout (int): The network timeout in seconds.

        Returns:
            dict: The stat dictionary.
        '''
        mesg = ('axon:stat', {})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)

    def save(self, files, timeout=None):
        '''
        Save a list of files to the axon.

        Args:
            files ([bytes]): A list of files as bytes blobs.
            timeout (int): The network timeout in seconds.

        Returns:
            int: The number of files saved.
        '''
        mesg = ('axon:save', {'files': files})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)

    def wants(self, hashes, timeout=None):
        '''
        Filter and return a list of hashes that the axon wants.

        Args:
            hashes (list): A list of SHA256 bytes.
            timeout (int): The network timeout in seconds.

        Returns:
            tuple: A tuple containg hashes the axon wants.
        '''
        mesg = ('axon:wants', {'hashes': hashes})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)

    def upload(self, genr, timeout=None):
        '''
        Upload a large file using a generator.

        Args:
            genr (generator): Yields file bytes chunks.
            timeout (int): The network timeout in seconds.

        Returns:
            bytes: The sha256 digest of the file received, in bytes.
        '''
        mesg = ('axon:upload', {})

        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            chan.txwind(genr, 10, timeout=timeout)

            ok, retn = chan.next(timeout=timeout)
            return s_common.reqok(ok, retn)

    def bytes(self, sha256, timeout=None):
        '''
        Yield bytes for the given SHA256.

        Args:
            sha256 (str): The SHA256 hash bytes.
            timeout (int): The network timeout in seconds.

        Yields:
            bytes: Bytes of the file requested.

        Raises:
            RetnErr: If the file requested does not exist.
        '''
        mesg = ('axon:bytes', {'sha256': sha256})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for byts in chan.rxwind(timeout=timeout):
                yield byts

    def metrics(self, offs=0, timeout=None):
        '''
        Yield metrics rows beginning at an offset.

        Args:
            offs (int): The offset to begin at.
            timeout (int): The network timeout in seconds.

        Yields:
            ((int, dict)): A tuple of offset and metrics information.
        '''
        mesg = ('axon:metrics', {'offs': offs})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for bloc in chan.rxwind(timeout=timeout):
                for item in bloc:
                    yield item

class BlobClient:

    def __init__(self, sess):
        self.sess = sess

    def metrics(self, offs=0, timeout=None):
        '''
        Get metrics for a given blob.

        Args:
            offs (int): Offset to start collecting metrics from.
            timeout (int): The network timeout in seconds.

        Yields:
            ((int, dict)): A tuple of offset and metrics information.
        '''
        mesg = ('blob:metrics', {'offs': offs})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for bloc in chan.rxwind(timeout=timeout):
                for item in bloc:
                    yield item

    def bytes(self, buid, timeout=None):
        '''
        Yield bytes for the given buid.

        Args:
            buid (bytes): The buid hash.
            timeout (int): The network timeout in seconds.

        Yields:
            bytes: Chunks of bytes for the given buid.
        '''
        mesg = ('blob:load', {'buid': buid})
        with self.sess.task(mesg, timeout=timeout) as chan:
            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)
            for byts in chan.rxwind(timeout=timeout):
                yield byts
