import time
import lmdb
import struct
import logging
import hashlib
import itertools

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

zero64 = b'\x00' * 8
blocksize = s_const.mebibyte * 64

class BlobStorApi(s_cell.CellApi):
    def save(self, blocs):
        return self.cell.save(blocs)

    def load(self, buid):
        ''' Hmmm '''
        pass

    def clone(self, offs):
        yield from self.cell.clone(offs)

    def stats(self):
        return self.cell.stats()

    def metrics(self, offs=0):
        return self.cell.metrics(offs)

    def getCloneOffs(self):
        return self.cell.getCloneOffs()

class Axon:
    # FIXME
    pass

class BlobStor(s_cell.Cell):
    '''
    The blob store maps buid,indx values to sequences of bytes stored in a LMDB database.
    '''
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
        self._blob_bytes = self.lenv.open_db(b'bytes') # <fidn><foff>=<byts>

        self._blob_clone = s_lmdb.Seqn(self.lenv, b'clone')
        self._blob_metrics = s_lmdb.Metrics(self.lenv)

        self.cloneof = self.conf.get('cloneof')

        if self.cloneof is not None:
            self.clonetask = s_glob.plex.coroToTask(self._cloneeLoop(self.cloneof))

        def fini():
            self.lenv.close()

        self.onfini(fini)

    def _cloneeLoop(self, sess):
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

