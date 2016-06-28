import os
import mmap
import struct
import hashlib
import tempfile
import threading

from binascii import unhexlify as unhex

import synapse.compat as s_compat
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath
import synapse.lib.atomfile as s_atomfile

from synapse.common import *

magic_v1 = unhex(b'265343eb3092ce626cdb731ef68bde83')

FLAG_USED  = 0x01

headfmt = '<16sQQ'
headsize = struct.calcsize(headfmt)

# heap blob format
# |--------16------|----8---|----8---|
#        magic        size    flags

defpage = 0x100000

class Heap(s_eventbus.EventBus):
    '''
    A persistant heap object.
    '''
    def __init__(self, fd, **opts):
        s_eventbus.EventBus.__init__(self)

        self.alloclock = threading.Lock()

        self.on('heap:write', self._fireHeapSync)
        self.on('heap:resize', self._fireHeapSync)

        self.syncact = s_reactor.Reactor()
        self.syncact.act('heap:write', self._actSyncHeapWrite )
        self.syncact.act('heap:resize', self._actSyncHeapResize )

        self.pagesize = opts.get('pagesize',defpage)

        pagerem = self.pagesize % mmap.ALLOCATIONGRANULARITY
        if pagerem:
            self.pagesize += ( mmap.ALLOCATIONGRANULARITY - pagerem )

        fd.seek(0,os.SEEK_END)

        size = fd.tell()

        if size == 0:

            size = 32 # a few qword slots for expansion
            used = headsize + size
            heaphead = self._genHeapHead(size) + s_compat.to_bytes(used,8)

            rem = len(heaphead) % self.pagesize
            if rem:
                heaphead += b'\x00' * (self.pagesize - rem)

            fd.write(heaphead)

            fd.flush()

        self.fd = fd
        self.atom = opts.get('atom')

        if self.atom == None:
            self.atom = s_atomfile.getAtomFile(fd)

        self.used = s_compat.to_int( self.readoff(32,8) )

        self.onfini( self.atom.fini )

    def sync(self, mesg):
        '''
        Consume a heap:sync event.
        '''
        self.syncact.react( mesg[1].get('mesg') )

    def syncs(self, msgs):
        '''
        Consume a list of heap:sync events.
        '''
        [ self.syncact.react( mesg[1].get('mesg') ) for mesg in msgs ]

    def _fireHeapSync(self, mesg):
        self.fire('heap:sync',mesg=mesg)

    def _actSyncHeapWrite(self, mesg):
        # event is triggered *with* fdlock
        off = mesg[1].get('off')
        byts = mesg[1].get('byts')
        self._writeoff(off,byts)

    def _actSyncHeapResize(self, mesg):
        size = mesg[1].get('size')

    def _writeoff(self, off, byts):
        self.atom.writeoff(off,byts)
        self.fire('heap:write', off=off, byts=byts)

    def readoff(self, off, size):
        '''
        Read and return bytes from the heap at an offset.

        Example:

            head = heap.readoff(off,headsize)

        '''
        byts = self.atom.readoff(off,size)

        if len(byts) != size:
            raise Exception('readoff short: %d != %d' % (len(byts),size))

        return byts

    def readiter(self, off, size, itersize=10000000):
        '''
        Yield back byts chunks for the given off/size.

        Example:

            for byts in heap.readiter(off,size):
                dostuff()

        '''
        offmax = off + size

        while off < offmax:

            offend = min( off + itersize, offmax )

            yield self.atom.readoff(off,offend-off)

            off = offend

    def writeoff(self, off, byts):
        '''
        Write bytes at an offset within the heap.

        Example:

            off = heap.alloc(size)
            heap.writeoff(off,byts)

        '''
        return self._writeoff(off,byts)

    def _genHeapHead(self, size, flags=FLAG_USED):
        return struct.pack(headfmt, magic_v1, size, flags)

    def alloc(self, size):
        '''
        Allocate a block within the Heap and return the offset.

        Example:

            off = heap.alloc(len(foo))

        '''
        # 16 byte aligned allocation sizes
        rem = size % 16
        if rem:
            size += 16 - rem

        fullsize = headsize + size

        with self.alloclock:

            heapsize = self.used + fullsize

            if heapsize > self.atom.size:
                # align resizes to pagesize
                rem = heapsize % self.pagesize
                if rem:
                    heapsize += (self.pagesize - rem)

                self.atom.resize(heapsize)
                self.fire('heap:resize', size=heapsize)

            dataoff = self.used + headsize

            self.used += fullsize

            self._writeoff(32, s_compat.to_bytes(self.used,8))
            self._writeoff(self.used, self._genHeapHead(size))

        return dataoff

    def size(self):
        return self.atom.size
