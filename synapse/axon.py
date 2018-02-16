import time
import lmdb
import struct
import logging
import hashlib
import itertools

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.neuron as s_neuron
import synapse.eventbus as s_eventbus

import synapse.lib.net as s_net
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const
import synapse.lib.config as s_config

logger = logging.getLogger(__name__)

zero64 = b'\x00\x00\x00\x00\x00\x00\x00\x00'
blocksize = s_const.mebibyte * 64

class BlobStor(s_eventbus.EventBus):

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

            for lkey, lval in blocs:
                clones.append(lkey)
                xact.put(lkey, lval, db=self._blob_bytes)

                size += len(lval)
                count += 1

            self._blob_clone.save(xact, clones)
            self._blob_metrics.inc(xact, 'bytes', size)
            self._blob_metrics.inc(xact, 'blocks', count)

            tick = s_common.now()
            self._blob_metrics.record(xact, {'time': tick, 'size': size, 'blocks': count})

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

class BlobCell(s_neuron.Cell):

    def postCell(self):

        if self.neuraddr is None:
            raise Exception('BlobCell requires a neuron')

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
                rows = mesg[1].get('rows', ())
                for row in rows:
                    yield row

                link.txfini((True, len(rows)))

        self.blobs.save(genr())

    @s_common.firethread
    def _fireCloneThread(self, sess):

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
                    logger.warning('BlobCell clone thread error: %s' % (e,))
                    time.sleep(1)

    def handlers(self):
        self.savedisp = s_net.LinkDisp(self._saveDispItems)
        return {
            'blob:save': self.savedisp.rx, # ('blob:save', {'rows':[ (lkey, lval)]})
            'blob:load': self._onBlobLoad, # ('blob:load', {'buid': <buid>} )
            'blob:stat': self._onBlobStat, # ('blob:stat', {}) -> (True, {info})
            'blob:clone': self._onBlobClone, # ('blob:clone', {'offs': <indx>}) -> [ (indx, (lkey, lval)), ]
            'blob:metrics': self._onBlobMetrics, # ('metrics', {'offs':<indx>}) -> ( (indx, info), ... )
        }

    @s_glob.inpool
    def _onBlobClone(self, chan, mesg):
        offs = mesg[1].get('offs')
        genr = self.blobs.clone(offs)
        rows = list(itertools.islice(genr, 1000))
        chan.txfini((True, rows))

    @s_glob.inpool
    def _onBlobUpload(self, chan, mesg):

        with chan:

            chan.setq()
            chan.tx((True, True))

            def genr():

                for ok, row in self.rxwind(timeout=60):
                    if not ok:
                        break

                    yield row

            # in chunks for transaction optimization
            for rows in s_common.chunks(genr(), 10):
                self.blobs.save(rows)

            chan.txfini((True, True))

    @s_glob.inpool
    def _onBlobStat(self, chan, mesg):
        chan.txfini((True, self.blobs.stat()))

    @s_glob.inpool
    def _onBlobMetrics(self, chan, mesg):
        offs = mesg[1].get('offs', 0)
        chan.setq()

        genr = self.blobs.metrics(offs=offs)
        chan.txwind(genr, 1000, timeout=30)
        chan.txfini()

    @s_glob.inpool
    def _onBlobLoad(self, chan, mesg):
        buid = mesg[1].get('buid')
        with chan:
            chan.setq()
            chan.tx((True, None))
            genr = self.blobs.load(buid)
            chan.txwind(genr, 10, timeout=30)

    @staticmethod
    @s_config.confdef(name='blob')
    def _getBlobConfDefs():
        return (
            ('blob:mapsize', {'type': 'int', 'defval': s_const.tebibyte * 10,
                'doc': 'The maximum size of the LMDB memory map'}),

            ('blob:cloneof', {'defval': None,
                'doc': 'The name of a blob cell to clone from'}),
        )

class AxonCell(s_neuron.Cell):
    '''
    An Axon acts as an indexer and manages access to BlobCell bytes.
    '''
    def postCell(self):

        if self.cellpool is None:
            raise Exception('AxonCell requires a neuron and CellPool')

        mapsize = self.getConfOpt('axon:mapsize')

        path = self.getCellDir('axon.lmdb')

        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.blobhas = self.lenv.open_db(b'axon:blob:has') # <sha256>=1
        self.bloblocs = self.lenv.open_db(b'axon:blob:locs') # <sha256><loc>=1
        self.metrics = s_lmdb.Metrics(self.lenv)

        def fini():
            self.lenv.sync()
            self.lenv.close()

        self.onfini(fini)

        self.blobs = s_neuron.CellPool(self.cellauth, self.neuraddr)
        self.onfini(self.blobs.fini)

        for name in self.getConfOpt('axon:blobs'):
            self.blobs.add(name)

    def handlers(self):
        return {
            'axon:save': self._onAxonSave,       # ('axon:save', {'files':[<bytes>, ...]})
            'axon:stat': self._onAxonStat,
            'axon:wants': self._onAxonWants,
            'axon:bytes': self._onAxonBytes,
            'axon:upload': self._onAxonUpload,
            'axon:metrics': self._onAxonMetrics,
        }

    @s_glob.inpool
    def _onAxonUpload(self, chan, mesg):

        sha256 = mesg[1].get('sha256')

        with chan:

            with self.lenv.begin() as xact:
                if xact.get(sha256, db=self.blobhas):
                    return chan.txfini((True, False))

            ok, retn = self.blobs.any()
            if not ok:
                return chan.txfini((False, retn))

            name, sess = retn

            info = {'size': 0}

            def genr():

                indx = 0
                size = 0

                ok = False
                for ok, byts in chan.rxwind(timeout=30):
                    if not ok:
                        break

                    info['size'] += len(byts)

                    lkey = sha256 + struct.pack('>Q', indx)
                    indx += 1

                    yield lkey, byts

            with sess.chan() as chanb:

                chanb.tx(('blob:upload', {}))
                ok, retn = chanb.next(timeout=30)
                if not ok:
                    chan.tx((False, retn))

                chan.tx((True, True))
                # XXX Broken code
                if bchan.txwind(genr(), 10):

                    nenc = name.encode('utf8')
                    with self.lenv.begin(write=True) as xact:
                        self._addFileLoc(xact, sha256, size, name)

            chan.txfini((True, name))

    def _addFileLoc(self, xact, sha256, size, name):

        tick = s_common.now()

        nenc = name.encode('utf8')

        xact.put(sha256, struct.pack('>Q', size), db=self.blobhas)
        xact.put(sha256 + nenc, struct.pack('>Q', tick), db=self.bloblocs)

        self.metrics.inc(xact, 'files', 1)
        self.metrics.inc(xact, 'bytes', size)

        # metrics contains everything we need to clone
        self.metrics.record(xact, {'time': tick, 'cell': name, 'size': size, 'sha256': sha256})

    def _onAxonStat(self, chan, mesg):
        with chan:
            return chan.txfini((True, self.metrics.stat()))

    @s_glob.inpool
    def _onAxonMetrics(self, chan, mesg):
        offs = mesg[1].get('offs')
        size = mesg[1].get('size', 10000)

        with chan:
            with self.lenv.begin() as xact:
                genr = self.metrics.iter(xact, offs)
                retn = list(itertools.islice(genr, size))
                return chan.txfini((True, retn))

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

            chan.txfini((True, wants))

    @s_glob.inpool
    def _onAxonBytes(self, chan, mesg):

        sha256 = mesg[1].get('sha256')
        with chan:

            with self.lenv.begin() as xact:
                locs = self.getBlobLocs(xact, sha256)

            if not locs:
                return chan.txfini((False, ('FileNotFound', {})))

            sess = None
            for name in locs:
                sess = self.blobs.get(name)
                if sess is not None:
                    break

            if sess is None:
                return chan.txfini((False, ('NotReady', {})))

            chan.setq()

            with sess.chan() as bchan:

                bchan.setq()
                bchan.tx(('blob:load', {'buid': sha256}))

                ok, retn = bchan.next(timeout=30)
                if not ok:
                    return chan.txfini((ok, retn))

                chan.tx((True, name))

                def genr():

                    for ok, item in bchan.rxwind():
                        if not ok:
                            return

                        yield item

                chan.txwind(genr(), 10, timeout=30)

    def getBlobLocs(self, xact, sha256):

        with xact.cursor(db=self.bloblocs) as curs:

            if not curs.set_range(sha256):
                return ()

            locs = []

            for lkey in curs.iternext(values=False):
                if lkey[:32] != sha256:
                    break

                locs.append(lkey[32:].decode('utf8'))

            return locs

    def _filtSaveByts(self, files):

        todo = []
        with self.lenv.begin() as xact:

            curs = xact.cursor(db=self.blobhas)
            for byts in files:

                sha256 = hashlib.sha256(byts).digest()

                if curs.get(sha256):
                    continue

                todo.append((sha256, byts))

        return todo

    def _saveBlobByts(self, todo):

        rows = []
        for sha256, byts in todo:
            rows.append((sha256 + zero64, byts))

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
                return chan.txfini((True, 0))

            todo = self._filtSaveByts(files)

            # if there is nothing to do after deconfliction, bail
            if not todo:
                return chan.txfini((True, 0))

            ok, retn = self._saveBlobByts(todo)
            if not ok:
                logger.warning('axon:save failed save blobs: %r' % (retn,))
                return chan.txfini((False, retn))

            name = retn
            with self.lenv.begin(write=True) as xact:
                for sha256, byts in todo:
                    self._addFileLoc(xact, sha256, len(byts), name)

            return chan.txfini((True, len(todo)))

    @staticmethod
    @s_config.confdef(name='axon')
    def _getAxonConfDefs():
        return (
            ('axon:mapsize', {'type': 'int', 'defval': s_const.tebibyte,
                'doc': 'The maximum size of the LMDB memory map'}),

            ('axon:blobs', {'req': True,
                'doc': 'A list of cell names in a neuron cluster'}),
        )
