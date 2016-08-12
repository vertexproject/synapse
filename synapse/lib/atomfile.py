import os
import mmap
import threading

import ctypes
import ctypes.util

import synapse.lib.thisplat as s_thisplat
import synapse.lib.thishost as s_thishost

from synapse.eventbus import EventBus

libc = s_thisplat.getLibC()

ptrsize = s_thishost.get('ptrsize')
# TODO figure out how to use windows mmap for this
haspriv = getattr(mmap,'MAP_PRIVATE',None) != None
haspread = getattr(os,'pread',None) != None
hasremap = getattr(libc,'mremap',None) != None

def getAtomFile(fd, memok=True):
    '''
    Factory to construct the most optimal AtomFile for this platform.

    Example:

        atom = getAtomFile(fd)

        # provides thread safe routines for most optimal
        # offset based file I/O for this platform.

        # read 20 bytes at offset 300
        byts = atom.readoff(300,20)

        # write byts at offset 400
        atom.writeoff(400,byts)

    '''
    if ptrsize >= 8 and hasremap and haspriv and memok:
        return MemAtom(fd)

    if haspread:
        return FastAtom(fd)

    return AtomFile(fd)

class AtomFile(EventBus):
    '''
    Implement generic atomic "seek and read" behavior which some platforms override.
    '''
    def __init__(self, fd, **opts):
        EventBus.__init__(self)

        fd.seek(0, os.SEEK_END)

        self.fd = fd
        self.size = fd.tell()
        self.fdoff = self.size
        self.fileno = fd.fileno()

        self.lock = threading.Lock()

        self.onfini( self._onAtomFini )

    def readoff(self, off, size):
        '''
        Atomically read size bytes at the given offset.

        Example:

            byts = atom.readoff(off,size)

        '''
        return self._readoff(off,size)

    def writeoff(self, off, byts):
        '''
        Atomically write bytes at the given offset.
        '''
        return self._writeoff(off,byts)

    def resize(self, size):
        '''
        Resize the underlying file (currently only supports growth).

        Example:

            atom.resize(newsize)

        '''

        if size < self.size:
            raise Exception('resize() to smaller not supported')

        if size == self.size:
            return

        self._resize(size)

    def flush(self):
        '''
        Request that all changes are flushed to disk.

        Example:

            atom.flush()

        '''
        return self._flush()

    def _flush(self):
        self.fd.flush()

    def _resize(self, size):

        with self.lock:

            self.size = size
            self.fdoff = size

            self.fd.seek(size - 1)
            self.fd.write(b'\x00')

    def _readoff(self, off, size):

        with self.lock:

            if self.fdoff != off:
                self.fd.seek(off)

            byts = self.fd.read(size)

            self.fdoff = off + len(byts)

            return byts

    def _writeoff(self, off, byts):

        with self.lock:

            if self.fdoff != off:
                self.fd.seek(off)

            self.fd.write(byts)
            self.fdoff = off + len(byts)
            self.size = max( self.size, self.fdoff )

    def _onAtomFini(self):
        self.fd.flush()
        self.fd.close()

class MemAtom(AtomFile):
    '''
    An AtomFile which uses a contiguous memory map for high-speed file IO.
    '''
    def __init__(self, fd, **opts):
        AtomFile.__init__(self, fd)
        # TODO create a windows variant

        self.fd.flush()
        self.mm = mmap.mmap(self.fileno, self.size, mmap.MAP_SHARED, mmap.ACCESS_WRITE)

    def _onAtomFini(self):
        self.mm.flush()
        self.mm.close()

        return AtomFile._onAtomFini(self)

    def _flush(self):
        self.fd.flush()
        self.mm.flush()

    def _readoff(self, off, size):
        return self.mm[off:off+size]

    def _writeoff(self, off, byts):
        if off + len(byts) > self.size:
            raise Exception('writeoff past size!')

        self.mm[off:off+len(byts)] = byts

    def _resize(self, size):
        with self.lock:
            self.mm.resize(size)
            self.size = size

class FastAtom(AtomFile):
    '''
    An AtomFile which uses pread/pwrite to avoid locking.
    '''
    def _readoff(self, off, size):
        return os.pread(self.fileno, size, off)

    def _writeoff(self, off, byts):
        os.pwrite(self.fileno, byts, off)
        self.size = max(self.size, off + len(byts))

