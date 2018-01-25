import os
import stat
import time
import fcntl
import random
import logging
import threading

from binascii import unhexlify

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.heap as s_heap
import synapse.lib.tufo as s_tufo
import synapse.lib.config as s_config
import synapse.lib.persist as s_persist
import synapse.lib.service as s_service
import synapse.lib.thishost as s_thishost
import synapse.lib.thisplat as s_thisplat

# for backward compat (HashSet moved from this module to synapse.lib.hashset )
from synapse.lib.hashset import *

logger = logging.getLogger(__name__)

megabyte = 1024000
gigabyte = 1024000000
terabyte = 1024000000000
chunksize = megabyte * 10

'''
class AxonMixin:
    @s_telepath.clientside
    def eatfd(self, fd):
        hset = HashSet()
        #iden, props = hset.eatfd(fd)

        if self.has('guid', iden):
            return (iden, props)

        fd.seek(0)

        sess = self.alloc(props.get('size'))

        byts = fd.read(10000000)
        retn = self.chunk(sess, byts)

        byts = fd.read(10000000)
        while byts:
            retn = self.chunk(sess, byts)
            byts = fd.read(10000000)

        return (iden, props)

    def eatbytes(self, byts):
        hset = HashSet()

        hset.update(byts)
        iden, props = hset.guid()

        if self.has('guid', iden):
            return (iden, props)

        sess = self.alloc(props.get('size'))

        for chnk in s_common.chunks(byts, 10000000):
            self.chunk(sess, chnk)

        return (iden, props)
'''

class KvHashes:
    '''
    Use a synapse.lib.kv.KvStor to index (offs, size) tuples for
    various hashes.
    '''
    def __init__(self, stor, name='axon:hashes'):

        self.stor = stor
        self.iden = stor.getKvAlias(name)

        self.prefs = {} # hash key prefixes

    def _pref(self, name):
        pref = self.prefs.get(name)
        if pref is None:
            pref = name.encode('utf8') + b':'
            self.prefs[name] = pref
        return pref

    def add(self, offs, size, hashes):
        '''
        Add an (offs, size) tuple with the given (name,byts) hashes.

        Args:
            offs (int): The blob offset.
            size (int): The blob size.
            hashes ([(str,byts)]): A list of (name,hash) tuples.
        '''
        lval = s_msgpack.en((offs, size))

        dups = []
        for name, byts in hashes:
            lkey = self._pref(name) + byts
            dups.append(lkey, lval)

        self.addKvDups(dups)

    def get(self, name, byts):
        '''
        Retrieve a list of (offs, size) tuples for the given hash by name.

        Args:
            name (str): The name of the hash type.
            byts (bytes): The hash value in binary bytes.

        Returns:
            ([(int,int)]): A list of (offs,size) tuples.
        '''
        lkey = self._pref(name) + byts
        return [s_msgpack.un(b) for b in self.getKvDups(lkey)]

    def has(self, name, byts):
        '''
        Returns True if the KvHash contains the given hash.

        Args:
            name (str): The name of the hash type.
            byts (bytes): The hash value in binary bytes.

        Returns:
            (bool): True if the hash is present.
        '''
        lkey = self._pref(name) + byts
        return self.stor.hasKvDups(lkey)

#class Axon(s_config.Config, AxonMixin):
class Axon(s_config.Config):
    '''
    An Axon acts as a binary blob store with hash based indexing/retrieval.
    '''
    def __init__(self, conf):

        s_config.Config.__init__(self)
        #s_neuron.Node.__init__(self, conf)

        self.setConfOpts(conf)

        self.reqConfOpts()

        self.inprog = {}
        self.axondir = s_common.gendir(axondir)

        kvpath = os.path.join(self.axondir, 'axon.lmdb')

        self.kvstor = s_kv.KvStor(kvpath)

        self.hashes = KvHashes(self.kvstor)
        self.axinfo = self.kvstor.getKvDict('axon:info')

        fd = s_common.genfile(axondir, 'axon.blob')
        self.blobfile = s_blobfile.BlobFile(fd)

        # create a reactor to unwrap core/heap sync events
        self.syncact = s_reactor.Reactor()
        self.syncact.act('bytes', self._actSyncBytes)
        self.syncact.act('hashes', self._actSyncHashes)

        self.onfini(self.kvstor.fini)
        self.onfini(self.blobfile.fini)

    @staticmethod
    @s_config.confdef(name='axon')
    def _axon_confdefs():
        confdefs = (
            ('axon:bytemax', {'type': 'int', 'defval': terabyte,
                'doc': 'Max size of data this axon is allowed to store.'}),
        )
        return confdefs

    def find(self, htype, hvalu):
        '''
        Returns a list of (offs, size) tuples for byte blobs in the axon.

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.

        Examples:

            Find all (offs,size) tuples for a given md5sum::

                for offs, size in axon.find('md5', md5hash):
                    dostuff()

        Returns:
            list: List of (offs, size) tuples.
        '''
        byts = unhexlify(hvalu)
        return self.hashes.get(htype, byts)

    def bytes(self, htype, hvalu):
        '''
        Yield chunks of bytes for the given hash value.

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.

        Examples:
            Get the bytes for a given guid and do stuff with them::

                for byts in axon.bytes('guid', axonblobguid):
                    dostuff(byts)


            Iteratively write bytes to a file for a given md5sum::

                for byts in axon.bytes('md5', md5sum):
                    fd.write(byts)

            Form a contiguous bytes object for a given sha512sum. This is not recommended for large files.::

                byts = b''.join((_byts for _byts in axon.bytes('sha512', sha512sum)))

        Notes:
            This API will raise an exception to the caller if the requested
            hash is not present in the axon. This is contrasted against the
            Axon.iterblob() API, which first requires the caller to first
            obtain an axon:blob tufo in order to start retrieving bytes from
            the axon.

        Yields:
            bytes:  A chunk of bytes for a given hash.

        Raises:
            NoSuchFile: If the requested hash is not present in the axon. This
            is raised when the generator is first consumed.
        '''
        blobs = self.get(htype, hvalu)
        if not blobs:
            raise s_common.NoSuchFile(mesg='The requested blob was not found.', htype=htype, hvalu=hvalu)

        offs, size = blobs[0]
        for byts in self.iterbytes(offs, size):
            yield byts

    def iterblob(self, blob):
        '''
        Yield bytes blocks from the given (offset,size) tuple until complete.

        Args:
            blob ((int, int)): The (offset, size) tuple.

        Examples:

            Get the bytes from a blob and do stuff with them::

                for byts in axon.iterblob(blob):
                    dostuff(byts)

            Iteratively write bytes to a file for a given blob::

                fd = file('foo.bin','wb')
                for byts in axon.iterblob(blob):
                    fd.write(byts)

            Form a contiguous bytes object for a given blob. This is not recommended for large files.::

                byts = b''.join((_byts for _byts in axon.iterblob(blob)))

        Yields:
            bytes:  A chunk of bytes
        '''
        offs, size = blob
        for byts in self.blobfile.readiter(offs, size):
            yield byts

    def wants(self, htype, hvalu, size):
        '''
        Single round trip call to Axon.has() and possibly Axon.alloc().

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.
            size (int): Number of bytes to allocate.

        Examples:
            Check if a sha256 value is present in the Axon, and if not, create the node for a set of bytes::

                iden = axon.wants('sha256',valu,size)
                if iden != None:
                    for byts in chunks(filebytes,onemeg):
                        axon.chunk(iden,byts)

        Returns:
            None if the hvalu is present; otherwise the iden is returned for writing.
        '''
        if self.has(htype, hvalu):
            return None

        return self.alloc(size)

    #def _fireAxonSync(self, mesg):
        #self.fire('axon:sync', mesg=mesg)

    #def sync(self, mesg):
        #'''
        ##Consume an axon:sync event (only if we are a clone).
        #'''
        #if not self.getConfOpt('axon:clone'):
            #raise s_common.AxonNotClone()

        #self.syncact.react(mesg)

    #def syncs(self, msgs):
        #if not self.getConfOpt('axon:clone'):
            #raise s_common.AxonNotClone()

        #[ self.syncact.react(mesg) for mesg in msgs ]

    #def _onAxonFini(self):

        # join clone threads
        #[thr.join(timeout=2) for thr in list(self.axthrs)]
        #if self.axcthr is not None:
            #self.axcthr.join(timeout=2)

    def alloc(self, size):
        '''
        Initialize a new blob upload context within this axon.

        Args:
            size (int): Size of the blob to allocate space for.

        Examples:
            Allocate a blob for a set of bytes and write it too the axon::

                iden = axon.alloc(len(byts))
                for b in chunks(byts,10240):
                    axon.chunk(iden,b)

        Returns:
            str: Identifier for a given upload.

        Raises:

        '''
        self.axinfo.get('ro')
        if self.isro:
            raise AxonIsRo()

        size = self.blobfile.size()
        bytemax = self.getConfOpt('axon:bytemax')
        if (hsize + size) > bytemax:
            raise s_common.NotEnoughFree(mesg='Not enough free space on the heap to allocate bytes.',
                                         size=size, heapsize=hsize, bytemax=bytmax)

        iden = s_common.guid()
        off = self.blobfile.alloc(size)

        self.inprog[iden] = {'size': size, 'off': off, 'cur': off, 'maxoff': off + size, 'hashset': HashSet()}

        return iden

    def chunk(self, iden, byts):
        '''
        Save a chunk of a blob allocated with alloc().

        Args:
            iden (str): Iden to save bytes too
            byts (bytes): Bytes to write to the blob.

        Returns:
            (bool): True for the last chunk.

        Raises:
            NoSuchIden: If the iden is not in progress.
            AxonBadChunk: If a chunk would write past the allocation size.
        '''
        info = self.inprog.get(iden)

        if info is None:
            raise s_common.NoSuchIden(iden)

        blen = len(bytes)

        cur = info.get('cur')
        maxoff = info.get('maxoff')

        if cur + len(byts) > maxoff:
            self.inprog.pop(iden, None)
            raise AxonBadChunk(mesg='chunk larger than remaining size')

        self.blobfile.writeoff(cur, byts)
        self.syncbus.fire('bytes', offs=cur, byts=byts)

        info['cur'] += blen

        hset = info.get('hashset')
        hset.update(byts)

        if info['cur'] != maxoff:
            return False

        # if the upload is complete, fire the add event
        self.inprog.pop(iden, None)

        offs = info.get('off')
        size = info.get('size')

        guid, hashes = hset.hashes()
        hashes.append(('guid', guid))

        self.hashes.add(size, offs, hashes)

        self.syncbus.fire('hashes', offs=offs, size=size, hashes=hashes)

        return True

    def has(self, htype, hvalu):
        '''
        Check if the Axon has a given hash type/valu combination stored in it.

        Args:
            htype (str): Hash type.
            hvalu (bytes): Hash value.

        Examples:

            Check if a sha256 value is present::

                if not axon.has('sha256', shaval):
                    stuff()

            Check if a known superhash iden is present::

                if axon.has('guid', guidval):
                    stuff()

        Returns:
            ((str, dict)): axon:blob tufo if the axon has the hash or guid. None otherwise.
        '''
        return self.hashes.has(htype, unhexlify(hvalu))

s_dyndeps.addDynAlias('syn:axon', Axon)
