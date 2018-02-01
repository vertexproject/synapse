import os
import lmdb
import random
import struct
import logging
import binascii
import contextlib

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.neuron as s_neuron
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.blobfile as s_blobfile

# for backward compat (HashSet moved from this module to synapse.lib.hashset )
from synapse.lib.hashset import *

logger = logging.getLogger(__name__)

blocksize = 2**26 # 64 meg blocks

def unhex(text):
    return binascii.unhexlify(text)

def enhex(byts):
    return binascii.hexlify(byts).decode('utf8')

prefs = {
    'md5': b'md5:',
    'sha1': b'sha1:',
    'sha256': b'sha256:',
    'sha512': b'sha512:',
}

class Upload:

    def __init__(self, axon, size):

        self.gotn = 0
        self.byts = b''

        self.axon = axon
        self.size = size

        self.md5 = hashlib.md5()
        self.sha1 = hashlib.sha1()
        self.sha256 = hashlib.sha256()
        self.sha512 = hashlib.sha512()

        self.blocks = []

    def write(self, byts):

        blen = len(byts)

        self.gotn += blen

        if self.gotn > self.size:
            raise Exception('upload larger than expected')

        self.md5.update(byts)
        self.sha1.update(byts)
        self.sha256.update(byts)
        self.sha512.update(byts)

        self.byts += byts

        if self.gotn < self.size and len(self.byts) < blocksize:
            return False

        with self.axon._withLmdbXact(write=True) as xact:

            while len(self.byts) >= blocksize:

                chnk = self.byts[:blocksize]
                bkey = self.axon._saveFileByts(chnk, xact)
                self.blocks.append(bkey)
                self.byts = self.byts[blocksize:]

            if self.gotn < self.size:
                return False

            # we got the last chunk... mop up!
            if self.byts:
                bkey = self.axon._saveFileByts(self.byts, xact)
                self.blocks.append(bkey)

            info = {
                'size': self.size,
                'tick': s_common.now(),

                'md5': self.md5.hexdigest(),
                'sha1': self.sha1.hexdigest(),
                'sha256': self.sha256.hexdigest(),
                'sha512': self.sha512.hexdigest(),
            }

            hashes = (
                b'md5:' + self.md5.digest(),
                b'sha1:' + self.sha1.digest(),
                b'sha256:' + self.sha256.digest(),
                b'sha512:' + self.sha512.digest(),
            )
            self.axon._saveFileDefn(info, self.blocks, hashes, xact)

        return True

class Axon(s_eventbus.EventBus):
    '''
    An Axon acts as a binary blob store with hash based indexing/retrieval.
    '''
    def __init__(self, dirn, mapsize=1099511627776): # from LMDB docs....

        s_eventbus.EventBus.__init__(self)

        path = s_common.gendir(dirn, 'axon.lmdb')

        self.lmdb = lmdb.open(path, writemap=True, max_dbs=128)
        self.lmdb.set_mapsize(mapsize)

        self.lmdb_bytes = self.lmdb.open_db(b'bytes')

        self.lmdb_files = self.lmdb.open_db(b'files')
        self.lmdb_fileblocks = self.lmdb.open_db(b'fileblocks')

        self.lmdb_hashes = self.lmdb.open_db(b'hashes', dupsort=True)

        with self.lmdb.begin() as xact:
            self.bytes_indx = xact.stat(db=self.lmdb_bytes)['entries']
            self.files_indx = xact.stat(db=self.lmdb_files)['entries']

        def fini():
            self.lmdb.sync()
            self.lmdb.close()

        self.onfini(fini)
        self.inprog = {}

    @contextlib.contextmanager
    def _withLmdbXact(self, write=False):
        with self.lmdb.begin(write=write) as xact:
            yield xact

    def _saveFileByts(self, byts, xact):
        with xact.cursor(db=self.lmdb_bytes) as curs:

            indx = self.bytes_indx
            self.bytes_indx += 1

            lkey = struct.pack('>Q', indx)
            curs.put(lkey, byts, append=True)

        return lkey

    def _saveFileDefn(self, info, blocks, hashes, xact):

        # add a file definition blob ( [indx, ...] of bytes )
        indx = self.files_indx
        self.files_indx += 1

        fkey = struct.pack('>Q', indx)

        rows = []
        for i, bkey in enumerate(blocks):
            ikey = struct.pack('>Q', i)
            rows.append((fkey + ikey, bkey))

        with xact.cursor(db=self.lmdb_fileblocks) as curs:
            curs.putmulti(rows, append=True)

        with xact.cursor(db=self.lmdb_files) as curs:
            byts = s_msgpack.en((indx, info))
            curs.put(fkey, byts, append=True)

        with xact.cursor(db=self.lmdb_hashes) as curs:
            rows = tuple([ (hkey, fkey) for hkey in hashes ])
            curs.putmulti(rows, dupdata=True)

    def files(self, offs, size):

        lkey = struct.pack('>Q', offs)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_files) as curs:

                if not curs.set_key(lkey):
                    return ()

                for lkey, lval in curs.iternext():

                    indx = struct.unpack('>Q', lkey)[0]
                    yield s_msgpack.un(lval)

    def find(self, name, valu):
        '''
        Yields (id,info) tuples for files matching name=valu.

        Args:
            name (str): The hash name.
            valu (str): The hex digest.
        '''

        pref = prefs.get(name)
        if pref is None:
            raise s_exc.NoSuchAlgo(name=name)

        hkey = pref + unhex(valu)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_hashes) as curs:

                if not curs.set_key(hkey):
                    return

                with xact.cursor(db=self.lmdb_files) as furs:
                    for fkey in curs.iternext_dup():
                        yield s_msgpack.un(furs.get(fkey))

    def bytes(self, name, valu):
        '''
        Yields bytes chunks for the first file matching name=valu.

        Args:
            name (str): The hash name.
            valu (str): The hex digest.
        '''

        pref = prefs.get(name)
        if pref is None:
            raise s_exc.NoSuchAlgo(name=name)

        hkey = pref + unhex(valu)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_hashes) as curs:

                if not curs.set_key(hkey):
                    raise s_exc.NoSuchHash(name=name, valu=valu)

                fkey = curs.value()

            with xact.cursor(db=self.lmdb_fileblocks) as curs:

                with xact.cursor(db=self.lmdb_bytes) as burs:

                    curs.set_range(fkey)

                    for bkey, bval in curs.iternext():

                        if not bkey.startswith(fkey):
                            break

                        yield burs.get(bval)

    def alloc(self, size, sha256=None):
        '''
        Allocate a new upload context for size bytes.

        Args:
            size (int): Size of the file in bytes.
            sha256 (bytes): The SHA256 digest to deconflict on.

        Returns:
            bytes: The binary guid for upload calls to chunk().
        '''
        if sha256 is not None and self._hasHash('sha256', sha256):
            return None

        iden = s_common.guid()
        self.inprog[iden] = Upload(self, size)
        return iden

    def _hasHash(self, name, valu):

        pref = prefs.get(name)
        if pref is None:
            raise s_exc.NoSuchAlgo(name=name)

        lkey = pref + unhex(valu)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_hashes) as curs:

                return curs.set_key(lkey)

    def chunk(self, iden, byts):
        '''
        Save a chunk of a blob allocated with alloc().

        Args:
            iden (str): The file upload guid started with alloc().
            byts (bytes): Bytes to write to the blob.

        Returns:
            (bool): True for the last chunk.

        Raises:
            NoSuchIden: If the iden is not in progress.
            AxonBadChunk: If a chunk would write past the allocation size.
        '''
        upld = self.inprog.get(iden)
        if upld is None:
            raise s_common.NoSuchIden(iden)

        return upld.write(byts)

    def eat(self, byts):
        '''
        Single round trip file upload interface for small files.
        '''
        sha256 = hashlib.sha256(byts).hexdigest()
        if self._hasHash('sha256', sha256):
            return False

        upld = Upload(self, len(byts))
        upld.write(byts)
        return True

    def has(self, name, valu):
        '''
        Check if the Axon has a given hash type/valu combination stored in it.

        Args:
            name (str): Hash type.
            valu (str): Hash value.

        Examples:

            Check if a sha256 value is present::

                if not axon.has('sha256', shaval):
                    stuff()

        Returns:
            ((str, dict)): axon:blob tufo if the axon has the hash or guid. None otherwise.
        '''
        return self._hasHash(name, valu)

class AxonCell(s_neuron.Cell):

    def postCell(self):
        path = self.getCellDir('axon')
        self.axon = Axon(path)

    def handlers(self):
        return {
            'axon:eat': self._onAxonEat,
            'axon:has': self._onAxonHas,

            'axon:find': self._onAxonFind,
            'axon:bytes': self._onAxonBytes,

            'axon:alloc': self._onAxonAlloc,
            'axon:chunk': self._onAxonChunk,
        }

    @s_glob.inpool
    def _onAxonHas(self, chan, mesg):
        name = mesg[1].get('name')
        valu = mesg[1].get('valu')
        chan.txfini(self.axon.has(name, valu))

    @s_glob.inpool
    def _onAxonEat(self, chan, mesg):
        byts = mesg[1].get('byts')
        chan.txfini(self.axon.eat(byts))

    @s_glob.inpool
    def _onAxonFind(self, chan, mesg):
        name = mesg[1].get('name')
        valu = mesg[1].get('valu')
        chan.txfini(tuple(self.axon.find(name, valu)))

    @s_glob.inpool
    def _onAxonAlloc(self, chan, mesg):
        size = mesg[1].get('size')
        sha256 = mesg[1].get('sha256')
        # TODO Maybe eventually make a more efficient
        # "inverse generator" convention for this API
        chan.txfini(self.axon.alloc(size, sha256=sha256))

    @s_glob.inpool
    def _onAxonChunk(self, chan, mesg):
        iden = mesg[1].get('iden')
        byts = mesg[1].get('byts')
        # TODO Maybe eventually make a more efficient
        # "inverse generator" convention for this API
        chan.txfini(self.axon.chunk(iden, byts))

    @s_glob.inpool
    def _onAxonBytes(self, chan, mesg):

        name = mesg[1].get('name')
        valu = mesg[1].get('valu')

        chan.setq()

        with chan:
            for byts in self.axon.bytes(name, valu):
                chan.tx(byts)
                if not chan.next(timeout=30):
                    return

class AxonUser(s_neuron.CellUser):

    def __init__(self, auth, addr, timeout=None):

        s_neuron.CellUser.__init__(self, auth)
        self.addr = addr
        self.timeout = timeout

        self._axon_sess = self.open(addr, timeout=timeout)
        if self._axon_sess is None:
            raise s_exc.HitMaxTime(timeout=timeout)

    def eat(self, byts, timeout=None):
        mesg = ('axon:eat', {'byts': byts})
        return self._axon_sess.call(mesg, timeout=timeout)

    def has(self, name, valu, timeout=None):
        mesg = ('axon:has', {'name': name, 'valu': valu})
        return self._axon_sess.call(mesg, timeout=timeout)

    def bytes(self, name, valu):
        mesg = ('axon:bytes', {'name': name, 'valu': valu})
        with self._axon_sess.task(mesg) as chan:
            for byts in chan.iter():
                chan.tx(True)
                yield byts

    #def eatfd(self, fd):
    #def has(self, name, valu):
    #def bytes(self, name, valu):
    #def alloc(self, size, sha256=None):
    #def chunk(self, iden, byts):
