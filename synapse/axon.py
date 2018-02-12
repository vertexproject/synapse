import lmdb
import struct
import logging
import binascii
import itertools
import contextlib

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.neuron as s_neuron
#import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus

import synapse.lib.lmdb as s_lmdb
import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack

# for backward compat (HashSet moved from this module to synapse.lib.hashset )
from synapse.lib.hashset import *

logger = logging.getLogger(__name__)

zero64 = b'\x00\x00\x00\x00\x00\x00\x00\x00'
blocksize = 2**26 # 64 megabytes

class BlobStor(s_eventbus.EventBus):

    def __init__(self, dirn, mapsize=s_const.tebibyte):

        s_eventbus.EventBus.__init__(self)

        path = s_common.gendir(dirn, 'blobs.lmdb')
        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        #self.infodb = self.lenv.open_db(b'info')
        self.bytesdb = self.lenv.open_db(b'bytes') # <fidn><foff>=<byts>

        self._blob_clone = s_lmdb.Seqn(self.lenv, b'clone')
        self._blob_metrics = s_lmdb.Metrics(self.lenv)

    def save(self, blocs):
        '''
        Save items from an iterator of (<buid><indx>, <byts>).

        NOTE: This API is only for use by a single Axon who owns this BlobStor.
        '''
        for items in s_common.chunks(blocs, 100):

            with self.lenv.begin(write=True, db=self.bytesdb) as xact:

                size = 0
                count = 0

                clones = []
                for lkey, lval in items:

                    xact.put(lkey, lval, db=self.bytesdb)
                    clones.append(lkey)

                    count += 1
                    size += len(lval)

                self._blob_clone.save(xact, clones)

                self._blob_metrics.inc(xact, 'bytes', size)
                self._blob_metrics.inc(xact, 'blocks', count)

                tick = s_common.now()
                self._blob_metrics.record(xact, {'time': tick, 'size': size, 'blocks': count})

    def load(self, buid):
        '''
        Load and yield the bytes blocks for a given buid.
        '''
        with self.lenv.begin(db=self.bytesdb, buffers=True) as xact:

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
        '''
        with self.lenv.begin() as xact:
            curs = xact.cursor(db=self.bytesdb)
            for indx, lkey in self._blob_clone.iter(xact, offs):
                byts = curs.get(lkey)
                yield indx, (lkey, byts)

    def _saveCloneRows(self, genr):

        for items in s_common.chunks(genr, 100):

            with self.lenv.begin(write=True, db=self.bytesdb) as xact:

                clones = []
                for indx, (lkey, lval) in items:
                    xact.put(lkey, lval)
                    clones.append(lkey)

                self._blob_clone.save(xact, clones)

    def stat(self):
        return self._blob_metrics.stat()

    def metrics(self, offs=0):
        '''
        Yields (indx, sample) info from the metrics sequence.
        '''
        with self.lenv.begin() as xact:
            for item in self._blob_metrics.iter(xact, offs):
                yield item

class BlobCell(s_neuron.Cell):

    def postCell(self):

        path = self.getCellPath('blobs.lmdb')

        s_common.gendir(path)
        self.blobs = BlobStor(path)

    def finiCell(self):
        self.blobs.fini()

    def handlers(self):
        return {
            'blob:save': self._onBlobSave, # ('blob:save', {'items': ( (lkey, lval), ... ) } )
            'blob:load': self._onBlobLoad, # ('blob:load', {'buid': <buid>} )

            # some standard handlers..  # ('stat', {}) ->  {<stats>}
            'stat': self._onBlobStat,
            'metrics': self._onBlobMetrics, # ('metrics', {'offs':<indx>}) -> ( (indx, info), ... )
        }

    def _onBlobStat(self, chan, mesg):
        chan.txfini(self.blobs.stat())

    @s_glob.inpool
    def _onBlobMetrics(self, chan, mesg):

        offs = mesg[1].get('offs')

        chan.setq()
        chan.tx(True)

        with chan:
            genr = self.blobs.metrics(offs=offs)
            chan.txloop(genr)

    @s_glob.inpool
    def _onBlobSave(self, chan, mesg):

        with chan:

            chan.setq()
            chan.tx(True)

            genr = chan.rxwind(timeout=30)
            self.blobs.save(genr)

    @s_glob.inpool
    def _onBlobLoad(self, chan, mesg):

        buid = mesg[1].get('buid')
        with chan:

            chan.setq()
            genr = self.blobs.load(buid)
            chan.txloop(genr)

class BlobUser(s_neuron.CellUser):

    def __init__(self, addr, auth, timeout=30):
        s_neuron.CellUser.__init__(self, auth)

    def clone(self, offs, timeout=None):

        with self.open(self.addr, timeout=timeout) as sess:

            with sess.task(('blob:clone', {'offs': offs})) as chan:

                chan.next(timeout=timeout)
                for item in chan.rxwind(timeout=timeout):
                    yield item

class AxonCell(s_neuron.Cell):
    '''
    An Axon acts as an indexer and manages access to BlobCell bytes.
    '''
    def postCell(self):

        mapsize = self.config.getConfOpt('axon:mapsize')
        path = s_common.gendir(dirn, 'axon.lmdb')

        self.lenv = lmdb.open(path, writemap=True, max_dbs=128)
        self.lenv.set_mapsize(mapsize)

        self.propstor = s_lmdb.PropStor(self.lenv, b'axon')

        def fini():
            self.lenv.sync()
            self.lenv.close()

        self.onfini(fini)

        #for name, curl in self.config.getConfOpt('blobs')
        #blobs = self.config.getConfOpt('blobs')

        self.blobpool = s_net.LinkPool()

        netw, path = opts.cryocell[7:].split('/', 1)
        host, portstr = netw.split(':')

    @staticmethod
    @s_config.confdef(name='axon')
    def _getAxonConfDefs():
        return (

            ('mapsize', {'type': 'int', 'defval': s_const.tebibyte,
                'doc': 'The maximum size of the LMDB memory map'}),

            ('blobs', {'req': True,
                'doc': "A list of (name, conn) tuples.  Ex. ('blob00', 'cell://1.2.3.4:45998')"}),
        )

    #def files(self, offs, size):

        #lkey = struct.pack('>Q', offs)

        #with self.lenv.begin() as xact:

            #with xact.cursor(db=self.lenv_files) as curs:

                #if not curs.set_key(lkey):
                    #return ()

                #for lkey, lval in curs.iternext():

                    #indx = struct.unpack('>Q', lkey)[0]
                    #yield s_msgpack.un(lval)

    #def find(self, name, valu):
        #'''
        #Yields (id,info) tuples for files matching name=valu.

        #Args:
            #name (str): The hash name.
            #valu (str): The hex digest.
        #'''

        #pref = prefs.get(name)
        #if pref is None:
            #raise s_exc.NoSuchAlgo(name=name)

        #hkey = pref + unhex(valu)

        #with self.lenv.begin() as xact:

            #with xact.cursor(db=self.lenv_hashes) as curs:

                #if not curs.set_key(hkey):
                    #return

                #with xact.cursor(db=self.lenv_files) as furs:
                    #for fkey in curs.iternext_dup():
                        #yield s_msgpack.un(furs.get(fkey))

    def find(self, name, valu):
        '''
        Find file records with the given hash=valu.

        Yields:
            (buid, ((prop, valu), ...))
        '''
        pval = s_common.uhex(valu)
        penc = b'file:bytes:' + name.encode('utf8')

        with self.lenv.begin() as xact:
            rows = self.propstor.eq(xact, penc, pval)
            for reco in self.propstor.recs(xact, rows):
                yield reco

    def bytes(self, name, valu):
        '''
        Yields bytes chunks for the first file matching hash=valu.

        Args:
            name (str): The hash name.
            valu (str): The hex digest.

        Raises:
            NoSuchHash: When the hash does not exist.
        '''
        valu = s_common.uhex(valu)
        penc = b'file:bytes:' + name.encode('utf8')

        with self.lenv.begin() as xact:

            row = None
            for row in self.propstor.eq(xact, penc, valu):
                break

            if row is None:
                raise s_exc.NoSuchHash(name=name, valu=valu)

            buid = row[0]
            with xact.cursor(db=self.bytesdb) as curs:

                for indx in itertools.count(0):

                    bkey = buid + struct.pack('>Q', indx)

                    byts = curs.get(bkey)
                    if byts is None:
                        break

                    yield byts

    def upload(self, blobs):
        '''
        Interface for large uploads ( which must be pre-deconflicted! )
        Args:
            blobs (iter): An iterable which yields chunks of bytes.
        '''
        iden = s_common.guid()
        buid = s_common.buid(('file:bytes', iden))

        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()

        size = 0
        todo = b''

        indx = itertools.count()

        taste = None

        for byts in blobs:

            size += len(byts)

            md5.update(byts)
            sha1.update(byts)
            sha256.update(byts)
            sha512.update(byts)

            todo += byts

            # save file bytes in 64 meg chunks...
            while len(todo) >= self.blocksize:

                if taste is None:
                    taste = todo[:16]

                save = todo[:self.blocksize]
                todo = todo[self.blocksize:]

                lkey = buid + struct.pack('>Q', next(indx))

                with self.lenv.begin(write=True) as xact:
                    with xact.cursor(db=self.bytesdb) as curs:
                        curs.put(lkey, save)

        with self.lenv.begin(write=True) as xact:

            if todo:

                if taste is None:
                    taste = todo[:16]

                lkey = buid + struct.pack('>Q', next(indx))
                with xact.cursor(db=self.bytesdb) as curs:
                    curs.put(lkey, todo)

            # bespoke node...
            recs = (
                (buid, (
                    (b'file:bytes', s_common.uhex(iden), 0),
                    (b'file:bytes:size', struct.pack('>Q', size), 0),

                    (b'file:bytes:md5', md5.digest(), 0),
                    (b'file:bytes:sha1', sha1.digest(), 0),
                    (b'file:bytes:sha256', sha256.digest(), 0),
                    (b'file:bytes:sha512', sha512.digest(), 0),
                )),
            )

            setr = self.propstor.getPropSetr(xact)
            s_common.spin(setr.put(recs))

    def has(self, name, valu):
        '''
        Returns True if the axon contains a file with the given hash.
        '''
        with self.lenv.begin() as xact:
            penc = b'file:bytes:' + name.encode('utf8')
            pval = s_common.uhex(valu)
            return self.propstor.has(xact, penc, pval)

    def eat(self, blobs):
        '''
        Eat all the files in the iterator.
        ( small files bulk interface... )
        '''
        # make our commits in chunks of 100 files...
        for todo in s_common.chunks(blobs, 100):
            self._addFilesBytes(todo)

    def _addFilesBytes(self, todo):
        with self.lenv.begin(write=True) as xact:
            setr = self.propstor.getPropSetr(xact=xact)
            for byts in todo:
                self._addFileBytes(xact, setr, byts)

    def _addFileBytes(self, xact, setr, byts):

        sha256 = hashlib.sha256(byts).digest()

        if setr.has(b'file:bytes:sha256', sha256):
            return

        size = struct.pack('>Q', len(byts))

        md5 = hashlib.md5(byts).digest()
        sha1 = hashlib.sha1(byts).digest()
        sha512 = hashlib.sha512(byts).digest()

        iden = s_common.guid()
        buid = s_common.buid(('file:bytes', iden))

        recs = (
            (buid, (
                # bespoke node...
                (b'file:bytes', s_common.uhex(iden), 0),
                (b'file:bytes:mime', b'??', 0),
                (b'file:bytes:size', size, 0),
                (b'file:bytes:md5', md5, 0),
                (b'file:bytes:sha1', sha1, 0),
                (b'file:bytes:sha256', sha256, 0),
                (b'file:bytes:sha512', sha512, 0),
                (b'file:bytes:taste', byts[:16], 0),
            )),
        )

        with xact.cursor(db=self._) as curs:
            bkey = buid + zero64
            curs.put(bkey, byts)

        s_common.spin(setr.put(recs))

    #def _addFilesBytes(self, xact, bytss):
        #'''
        #Add file bytes from a yielder containing each file as a bytes.
        #'''
        #with self.propstor.getPropSetr(xact) as setr:

        #with xact.cursor(db=self.propstor.byprop) as burs:

            #for byts in bytss:

                #sha256 = hashlib.sha256(byts).digest()

                #if setr.has(b'file:bytes:sha256', sha256):
                    #continue

                #if burs.set_key(sha256prop + b'\x00' + sha256):
                    #continue

                #size = len(byts)

                #md5 = hashlib.md5(byts).digest()
                #sha1 = hashlib.sha1(byts).digest()
                #sha512 = hashlib.sha512(byts).digest()

                #iden = s_common.guid()
                #buid = s_common.buid(('file:bytes', iden))

                #props = (
                    #(buid, (
                        ## bespoke node...
                        #('file:bytes', STOR_TYPE_BYTES, 0, s_common.uhex(iden)),
                        #('file:bytes:mime', STOR_TYPE_UTF8, 0, '??'),
                        #('file:bytes:size', STOR_TYPE_UINT64, 0, size),
                        #('file:bytes:md5', STOR_TYPE_BYTES, 0, md5),
                        #('file:bytes:sha1', STOR_TYPE_BYTES, 0, sha1),
                        #('file:bytes:sha256', STOR_TYPE_BYTES, 0, sha256),
                        #('file:bytes:sha512', STOR_TYPE_BYTES, 0, sha512),
                    #)),
                #)

    #def _addFileBytes(self, xact, burs

    #def blobs(self, blobs):

    #def eats(self, bytz):
        #'''
        ##Single round trip file upload for many small files.
        #'''
    #def addFilesBytes(self, bytz):

    #def eat(self, byts):
        #'''
        #Single round trip file upload interface for small files.
        #'''
        #sha256 = hashlib.sha256(byts).hexdigest()
        #if self._hasHash('sha256', sha256):
            #return False

        #upld = Upload(self, len(byts))
        #upld.write(byts)
        #return True

    #def has(self, sha256s

    #def hashash(
    #def has(self, name, valu):
        #penc = b'file:bytes:' + name.encode('utf8')
        #with self.lenv.begin() as xact:
            #self.propstor.has(

        #return self._hasHash(name, valu)

class AxonUser(s_neuron.CellUser):

    def __init__(self, auth, addr, timeout=None):

        s_neuron.CellUser.__init__(self, auth)
        self.addr = addr
        self.timeout = timeout

        #self._axon_sess = self.open(addr, timeout=timeout)
        #if self._axon_sess is None:
            #raise s_exc.HitMaxTime(timeout=timeout)
