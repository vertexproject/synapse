import os
import struct
import logging
import threading

import synapse.common as s_common
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.lib.atomfile as s_atomfile

log = logging.getLogger(__name__)


headfmt = '<Q'
headsize = struct.calcsize(headfmt)

# blobfile format
# |----8---|
#    size

class BlobFile(s_eventbus.EventBus):
    '''
    A persistent file blob object.

    Args:
        fd (file): File descriptor for the backing store of the blob.
        **opts: Additional blob options.

    Notes:
        The BlobFile object, while based on the Atomfile structure,
        only grows upward in size as data is allocated within it.
    '''
    def __init__(self, fd, **opts):
        s_eventbus.EventBus.__init__(self)

        self.alloclock = threading.Lock()

        self.on('blob:write', self._fireBlobSync)
        self.on('blob:alloc', self._fireBlobSync)

        self.syncact = s_reactor.Reactor()
        self.syncact.act('blob:write', self._actSyncBlobWrite)
        self.syncact.act('blob:alloc', self._actSyncBlobAlloc)

        fd.seek(0, os.SEEK_END)

        size = fd.tell()
        self._size = size

        self.fd = fd
        self.atom = opts.get('atom')

        if self.atom is None:
            self.atom = s_atomfile.getAtomFile(fd, memok=False)
            # If the atomfile comes in from the caller, we assume
            # that they will handle the fini()
            self.onfini(self.atom.fini)

    def sync(self, mesg):
        '''
        Consume a blob:sync event.

        Args:
            mesg ((str, dict)): A blob:sync message.

        Returns:
            None
        '''
        self.syncact.react(mesg[1].get('mesg'))

    def syncs(self, msgs):
        '''
        Consume a list of blob:sync events.

        Args:
            msgs (list): A list of blob:sync messages.

        Returns:
            None
        '''
        [self.syncact.react(mesg[1].get('mesg')) for mesg in msgs]

    def _fireBlobSync(self, mesg):
        self.fire('blob:sync', mesg=mesg)

    def _actSyncBlobWrite(self, mesg):
        # event is triggered *with* fdlock
        off = mesg[1].get('off')
        byts = mesg[1].get('byts')
        self._writeoff(off, byts)

    def _actSyncBlobAlloc(self, mesg):
        size = mesg[1].get('size')
        self.alloc(size)

    def _writeoff(self, off, byts):
        self.atom.writeoff(off, byts)
        self.fire('blob:write', off=off, byts=byts)

    def readoff(self, off, size):
        '''
        Read and return bytes from the blob at an offset.

        Args:
            off (int): Offset to read from.
            size (int): Number of bytes to read.

        Examples:
            Read the blobsize of the first blob stored at in the blobfile:

                head = blob.readoff(0,s_blobfile.headsize)

        Returns:
            bytes: The bytes from a given offset.

        Raises:
            s_common.BadBlobFile: If not enough bytes were read to fullfill the request.
        '''
        byts = self.atom.readoff(off, size)

        if len(byts) != size:
            raise s_common.BadBlobFile(mesg='readoff was short',
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
            Call dostuff() on byts as they are read from the blob:

                for byts in blob.readiter(off,size):
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
        Write bytes at an offset within the blob.

        Args:
            off (int): Offset to write bytes too.
            byts (bytes): Bytes to write at the offset.

        Examples:
            Allocate space for bytes and write it to the blob:

                byts = 'hehe'.encode()
                sz = len(byts)
                offset = blob.alloc(sz)
                blob.writeoff(offset, byts)

        Returns:
            None
        '''
        self._writeoff(off, byts)

    def alloc(self, size):
        '''
        Allocate a block within the Blob and return the offset.

        Args:
            size (int): Number of bytes to allocate within the blob.

        Example:
            Store a string by allocating space for it in a blob file:

                s = 'foobar'
                byts = s.encode()
                off = blob.alloc(len(byts))
                blob.writeoff(off, byts)

        Returns:
            int: Offset within the blob to use to store size bytes.
        '''
        # Account for the blob header
        fullsize = headsize + size

        with self.alloclock:

            # Fire our alloc event
            self.fire('blob:alloc', size=size)

            nsize = self._size + fullsize

            # Grow the file
            self.atom.resize(nsize)

            # Write the size dword
            self.writeoff(self._size, struct.pack(headfmt, size))

            # Compute the return value
            dataoff = self._size + headsize

            # Update our runtime size
            self._size = nsize

        return dataoff

    def size(self):
        '''
        Get the amount of space currently used by the blob.

        Returns:
            int: Size of the bytes currently allocated by the blob.
        '''
        return self._size

class BlobWalker(s_eventbus.EventBus):
    '''
    The BlobWalker is a class designed to assist in walking a
    BlobFile object for inspection purposes.

    Args:
        fd (file):
    '''
    def __init__(self, fd):
        s_eventbus.EventBus.__init__(self)

        self.fd = fd

        # Setup fini
        self.onfini(fd.close)

    def walk(self):
        '''
        Walk a BlobFile and fire events at each Blob encountered.

        Notes:
            This fires the following events that a consumer can use to inspect
            the file. These events will not serialize since they contain a
            reference to the underlying file descriptor and are designed in
            order to allow creation of tools which can inspect/consume bytes
            from a BlobFile.

                blob:walk:record - Fired each time a BlobFile record is touched.

                blob:walk:done - Fired when the BlobWalker is done walking the file.

                blob:walk:unpkerr - Fired if there is an error unpackting the Blobfile header.

                blob:walk:truncated - Fired if there is a truncated file encoutered.


        Returns:
            None
        '''
        # Snag the max filesize
        self.fd.seek(0, os.SEEK_END)
        maxsize = self.fd.tell()

        # Setup the expected size for the heap structures
        self.fd.seek(0)
        while True:

            # Store the current blobs offset value
            baseoff = self.fd.tell()

            # Read the header
            try:
                header = self.fd.read(headsize)
                size, = struct.unpack(headfmt, header)
            except Exception as e:
                log.exception('Failed to read/unpack header')
                self.fire('blob:walk:unpkerr',
                          fd=self.fd,
                          baseoff=baseoff,
                          size=headsize,
                          excinfo=s_common.excinfo(e))
                break

            # Save the current fd position
            off = self.fd.tell()

            # Fire the callback that someone can hook
            self.fire('blob:walk:record', fd=self.fd, baseoff=baseoff, off=off, size=size)

            # Calcuate the next expected header
            next_header = off + size
            self.fd.seek(next_header)

            if next_header > maxsize:
                self.fire('blob:walk:truncated',
                          fd=self.fd,
                          maxsize=maxsize,
                          next_header=next_header)
                break

            if next_header == maxsize:
                break

        self.fire('blob:walk:done',
                  fd=self.fd,
                  last_header=next_header,
                  maxsize=maxsize
                  )
