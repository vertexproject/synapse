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
        isclone (bool): This should be set to True if the BlobFile is recieving
        ``blob:sync`` events from another source. This will disable the
        ``alloc()`` and ``writeoff()`` APIs, in order to ensure that an arbitrary
        caller cannot modify the clone blobfile.  In addition, a BlobFile
        will not react to ``blob:sync`` events if ``isclone`` is False.
        **opts: Additional blob options.

    Notes:
        The BlobFile object, while based on the Atomfile structure,
        only grows upward in size as data is allocated within it.
    '''
    def __init__(self, fd, isclone=False, **opts):
        s_eventbus.EventBus.__init__(self)

        self.alloclock = threading.Lock()
        self.isclone = isclone

        self.on('blob:write', self._fireBlobSync)
        self.on('blob:alloc', self._fireBlobSync)

        self.syncact = s_reactor.Reactor()
        self.syncact.act('blob:write', self._actSyncBlobWrite)
        self.syncact.act('blob:alloc', self._actSyncBlobAlloc)

        fd.seek(0, os.SEEK_END)

        size = fd.tell()
        self._size = size

        self.fd = fd
        self.atom = opts.get('atom')  # type: s_atomfile.AtomFile

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
        if not self.isclone:
            return
        # event is triggered *with* fdlock
        off = mesg[1].get('off')
        byts = mesg[1].get('byts')
        self._writeoff(off, byts)

    def _actSyncBlobAlloc(self, mesg):
        if not self.isclone:
            return
        size = mesg[1].get('size')
        self._alloc(size)

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
        if self.isclone:
            raise s_common.BlobFileIsClone(mesg='BlobFile is a clone and cannot write data via writeoff()')
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
        if self.isclone:
            raise s_common.BlobFileIsClone(mesg='BlobFile is a clone and cannot alloc space via alloc()')
        return self._alloc(size)

    def _alloc(self, size):
        '''
        Internal method which implements alloc()
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
            self._writeoff(self._size, struct.pack(headfmt, size))

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

    def walk(self, callback=None):
        '''
        Walk the blobfile from the first record until the end.

        Args:
            callback (func): A callback function which is executed when a
            BlobFile record is encountered.  The callback should accept the
            following function signature: ``(fd, baseoff, off, size)``.  fd is
            the blob's file descriptor; baseoff is the offset where the blob
            header is located, offset is the location of the blob data, and
            size is the number of bytes allocated for the blob. If no callback
            is provided, nothing will happen when a BlobFile record is
            encountered.

        Notes:
            In addition to the callback, when walking the blobfile additional
            conditions may be encountered. These will fire an event and exit
            the walk() operation.

            These events will not serialize since they contain a
            reference to the underlying file descriptor and are designed in
            order to allow creation of tools which can inspect/consume bytes
            from a BlobFile.

                blob:walk:unpkerr - Fired if there is an error unpackting the Blobfile header.

                blob:walk:truncated - Fired if there is a truncated file encountered.

                blob:walk:done - Fired when the BlobWalker is done walking the file.

        Returns:
            None
        '''
        # Snag the max filesize
        self.fd.seek(0, os.SEEK_END)
        maxsize = self.fd.tell()

        # Start walking at zero
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

            if callback:
                callback(fd=self.fd, baseoff=baseoff, off=off, size=size)

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
