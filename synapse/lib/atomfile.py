import os
import mmap
import logging
import threading

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.const as s_const


logger = logging.getLogger(__name__)

class AtomBase(s_eventbus.EventBus):

    def __init__(self):
        s_eventbus.EventBus.__init__(self)
        self._fini_atexit = True

        self.lock = threading.Lock()

    def readoff(self, off, size):
        '''
        Atomically read size bytes at the given offset.

        Example:

            byts = atom.readoff(off,size)

        '''
        return self._readoff(off, size)

    def writeoff(self, off, byts):
        '''
        Atomically write bytes at the given offset.
        '''
        return self._writeoff(off, byts)

    def resize(self, size):
        '''
        Resize the underlying file (currently only supports growth).

        Example:

            atom.resize(newsize)

        '''
        return self._resize(size)

    def flush(self):
        '''
        Request that all changes are flushed to disk.

        Example:

            atom.flush()

        '''
        return self._flush()

    def _readoff(self, offs, size):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_readoff')

    def _writeoff(self, offs, byts):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_writeoff')

    def _resize(self, size):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_resize')

    def _flush(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_flush')

class AtomFile(AtomBase):
    '''
    Implement generic atomic "seek and read" behavior which some platforms override.
    '''
    def __init__(self, path):

        AtomBase.__init__(self)

        self.fd = s_common.genfile(path)
        self.fd.seek(0, os.SEEK_END)

        self.path = path
        self.size = self.fd.tell()
        self.fileno = self.fd.fileno()

        self.onfini(self.fd.close)

    def _resize(self, size):

        with self.lock:

            if size == self.size:
                return

            if size < self.size:
                self._trunc(size)
                return

            self._grow(size)

    def _flush(self):
        self.fd.flush()

    def _trunc(self, size):
        self.size = size
        self.fd.seek(size)
        self.fd.truncate()

    def _grow(self, size):
        self.size = size
        os.pwrite(self.fileno, b'\x00', size - 1)

    def _readoff(self, offs, size):
        return os.pread(self.fileno, size, offs)

    def _writeoff(self, offs, byts):
        os.pwrite(self.fileno, byts, offs)
        with self.lock:
            self.size = max(self.size, offs + len(byts))

# NOTE: It is a big deal if this changes
# ( it is used for mod math )
ATOM_DIR_FILEMAX = s_const.terabyte

class AtomDir(AtomBase):

    def __init__(self, dirn, filemax=ATOM_DIR_FILEMAX):
        AtomBase.__init__(self)

        self.dirn = dirn
        self.filemax = filemax
        self.atomdirn = s_common.gendir(self.dirn, 'atoms')

        self.atoms = self._getAtomFiles()
        self.size = sum([atom.size for atom in self.atoms])

        def fini():
            [atom.fini() for atom in self.atoms]

        self.onfini(fini)

    def _getAtomFiles(self):

        retn = []

        offs = 0
        while True:

            path = self._getAtomPath(offs)
            offs += self.filemax

            if not os.path.isfile(path):
                break

            retn.append(AtomFile(path))

        return retn

    def _getAtomPath(self, offs):
        return os.path.join(self.atomdirn, '%.16x.atom' % offs)

    def _readoff(self, offs, size):

        retn = b''
        want = size

        while len(retn) < size:

            byts = self._oneread(offs, want)
            if not byts:
                break

            retn += byts

            blen = len(byts)

            offs += blen
            want -= blen

        return retn

    def _oneread(self, offs, size):

        indx, offs = divmod(offs, self.filemax)
        if len(self.atoms) <= indx:
            return b''

        return self.atoms[indx].readoff(offs, size)

    def _writeoff(self, offs, byts):

        with self.lock:

            totl = offs + len(byts)

            while byts:

                size = self._onewrite(offs, byts)

                offs += size
                byts = byts[size:]

            self.size = max(self.size, totl)

    def _onewrite(self, offs, byts):

        indx, offs = divmod(offs, self.filemax)

        while len(self.atoms) <= indx:

            if self.atoms:

                prev = self.atoms[-1]

                if prev.size < self.filemax:
                    prev.writeoff(self.filemax - 1, b'\x00')

            path = self._getAtomPath(len(self.atoms) * self.filemax)
            self.atoms.append(AtomFile(path))

        atom = self.atoms[indx]

        size = len(byts)
        totl = offs + size
        if totl > self.filemax:
            size = self.filemax - offs
            byts = byts[:size]

        atom.writeoff(offs, byts)
        return size

    def _flush(self):
        [atom.flush() for atom in self.atoms]
