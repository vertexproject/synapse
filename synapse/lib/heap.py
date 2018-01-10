import os
import mmap
import struct
import logging
import threading

from binascii import unhexlify as unhex

import synapse.common as s_common
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.lib.atomfile as s_atomfile

log = logging.getLogger(__name__)

magic_v1 = unhex(b'265343eb3092ce626cdb731ef68bde83')

FLAG_USED = 0x01

headfmt = '<16sQQ'
headsize = struct.calcsize(headfmt)

# heap blob format
# |--------16------|----8---|----8---|
#        magic        size    flags

defpage = 0x100000

def packHeapHead(size, flags=FLAG_USED):
    '''
    Generate a heap header bytestring from a given size and flags.

    Args:
        size (int): Number of bytes stored for the header.
        flags (int): Flags to store in the header.

    Returns:
        bytes: The bytes header object.
    '''
    return struct.pack(headfmt, magic_v1, size, flags)

def unpackHeapHead(byts):
    '''
    Unpacks a bytes object into the magic value, size and flags.

    Args:
        byts (bytes): Bytes to unpack.

    Returns:
        (bytes, int, int): A tuple containing the magic value, size and flags.
    '''
    magic, size, flags = struct.unpack(headfmt, byts)
    return magic, size, flags

class Heap(s_eventbus.EventBus):
    '''
    A persistent heap object.

    Args:
        fd (file): File descriptor for the backing store of the heap.
        **opts: Additional heap options.

    Notes:
        The heap object, while based on the Atomfile structure, only grows
         upward in size as data is allocated within it..
    '''
    def __init__(self, fd, **opts):
        s_eventbus.EventBus.__init__(self)

        self.alloclock = threading.Lock()

        self.on('heap:write', self._fireHeapSync)
        self.on('heap:resize', self._fireHeapSync)

        self.syncact = s_reactor.Reactor()
        self.syncact.act('heap:write', self._actSyncHeapWrite)
        self.syncact.act('heap:resize', self._actSyncHeapResize)

        self.pagesize = opts.get('pagesize', defpage)

        pagerem = self.pagesize % mmap.ALLOCATIONGRANULARITY
        if pagerem:
            self.pagesize += (mmap.ALLOCATIONGRANULARITY - pagerem)

        fd.seek(0, os.SEEK_END)

        size = fd.tell()

        if size == 0:
            # The heap has not yet been initalized. Write a heap header to it
            # at 0x0 which will be used to track the overall size of the
            # first record in the heap.
            size = 32 # a few qword slots for expansion
            used = headsize + size
            heaphead = packHeapHead(size) + s_common.to_bytes(used, 8)

            # Fill up the remainder of the current pagesize with null bytes
            rem = len(heaphead) % self.pagesize
            if rem:
                heaphead += b'\x00' * (self.pagesize - rem)

            # Write and flush to disk
            fd.write(heaphead)
            fd.flush()

        self.fd = fd
        self.atom = opts.get('atom')

        if self.atom is None:
            self.atom = s_atomfile.getAtomFile(fd)

        # Validate the header of the file
        _magic, _size, _flags = unpackHeapHead(self.readoff(0, headsize))
        if _magic != magic_v1:
            raise s_common.BadHeapFile(mesg='Bad magic value present in heapfile header',
                                       evalu=magic_v1, magic=_magic)
        if _size != 32:
            raise s_common.BadHeapFile(mesg='Unexpected size found for first heapfile header',
                                       evalu=headsize + 32, size=_size)

        # How much data is currently store in heap?
        self.used = s_common.to_int(self.readoff(headsize, 8))
        if self.used > self.atomSize():
            raise s_common.BadHeapFile(mesg='Heapfile has been truncated and is smaller than expected',
                                       esize=self.used, fsize=self.atomSize())

        self.onfini(self.atom.fini)

    def sync(self, mesg):
        '''
        Consume a heap:sync event.

        Args:
            mesg ((str, dict)): A heap:sync message.

        Returns:
            None
        '''
        self.syncact.react(mesg[1].get('mesg'))

    def syncs(self, msgs):
        '''
        Consume a list of heap:sync events.

        Args:
            msgs (list): A list of heap:sync messages.

        Returns:
            None
        '''
        [self.syncact.react(mesg[1].get('mesg')) for mesg in msgs]

    def _fireHeapSync(self, mesg):
        self.fire('heap:sync', mesg=mesg)

    def _actSyncHeapWrite(self, mesg):
        # event is triggered *with* fdlock
        off = mesg[1].get('off')
        byts = mesg[1].get('byts')
        self._writeoff(off, byts)

    def _actSyncHeapResize(self, mesg):
        size = mesg[1].get('size')
        if size < self.atom.size:
            log.warning('Attempted to resize the heap downwards, fsize=[%s], size=[%s]',
                        self.atom.size, size)
            return
        self.atom.resize(size)

    def _writeoff(self, off, byts):
        self.atom.writeoff(off, byts)
        self.fire('heap:write', off=off, byts=byts)

    def readoff(self, off, size):
        '''
        Read and return bytes from the heap at an offset.

        Args:
            off (int): Offset to read from.
            size (int): Number of bytes to read.

        Examples:
            Read the heapfile header at offset zero:

                head = heap.readoff(0,s_heap.headsize)

        Returns:
            bytes: The bytes from a given offset.

        Raises:
            s_common.BadHeapFile: If not enough bytes were read to fullfill the request.
        '''
        byts = self.atom.readoff(off, size)

        if len(byts) != size:
            raise s_common.BadHeapFile(mesg='readoff was short',
                                       expected_size=size,
                                       byts_len=len(byts))

        return byts

    def readiter(self, off, size, itersize=10000000):
        '''
        Yield back bytes chunks for the given offset and size.

        Args:
            off (int): Offset to read from.
            size (int): Number of bytes to read.
            itersize (int): Maximum number of bytes to yield in a chunk.


        Examples:
            Call dostuff() on byts as they are read from the heap:

                for byts in heap.readiter(off,size):
                    dostuff(byts)

        Yields:
            bytes: Chunks of bytes.
        '''
        offmax = off + size

        while off < offmax:

            offend = min(off + itersize, offmax)

            yield self.atom.readoff(off, offend - off)

            off = offend

    def writeoff(self, off, byts):
        '''
        Write bytes at an offset within the heap.

        Args:
            off (int): Offset to write bytes too.
            byts (bytes): Bytes to write at the offset.

        Examples:
            Allocate space for bytes and write it to the heap:

                byts = 'hehe'.encode()
                sz = len(byts)
                offset = heap.alloc(sz)
                heap.writeoff(offset, byts)

        Returns:
            None
        '''
        return self._writeoff(off, byts)

    def alloc(self, size):
        '''
        Allocate a block within the Heap and return the offset.

        Args:
            size (int): Number of bytes to allocate within the heapfile.

        Example:
            Store a string in a heap file:

                s = 'foobar'
                byts = s.encode()
                off = heap.alloc(len(byts))
                heap.writeoff(off, byts)

        Returns:
            int: Offset within the heap to use to store size bytes.
        '''
        # 16 byte aligned allocation sizes
        rem = size % 16
        if rem:
            size += 16 - rem

        # Account for the heap header
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

            self._writeoff(32, s_common.to_bytes(self.used, 8))
            self._writeoff(self.used, packHeapHead(size))

        return dataoff

    def heapSize(self):
        '''
        Get the amount of space currently used by the heap.

        Returns:
            int: Size of the bytes currently allocated by the heap.
        '''
        return self.used

    def atomSize(self):
        '''
        Get the amount of space currently used by the atomfile unerlying the heap.

        Returns:
            int: Size of the underlying atomfile which backs the heap.
        '''
        return self.atom.size
