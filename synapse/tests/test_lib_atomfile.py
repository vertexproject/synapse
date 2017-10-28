import tempfile
import unittest

import synapse.lib.atomfile as s_atomfile

from synapse.tests.common import *

class AtomTest(SynTest):

    def _runAtomChecks(self, atom):

        atom.resize(8192)

        self.eq(atom.readoff(100, 20), b'\x00' * 20)

        atom.writeoff(100, b'asdf')
        atom.writeoff(104, b'qwer')

        self.eq(atom.readoff(100, 8), b'asdfqwer')

        # calling resize with the current size does nothing
        self.eq(atom.size, 8192)
        atom.resize(8192)
        self.eq(atom.size, 8192)

        atom.resize(4096)
        self.eq(atom.size, 4096)

    def test_atomfile_base(self):
        fd = self._getTempFile()
        with s_atomfile.AtomFile(fd) as atom:
            self._runAtomChecks(atom)

    def test_atomfile_pread(self):

        if not s_atomfile.haspread:
            raise unittest.SkipTest('platform lacks pread')

        fd = self._getTempFile()
        with s_atomfile.FastAtom(fd) as atom:
            atom = s_atomfile.FastAtom(fd)
            self._runAtomChecks(atom)

    def _getTempFile(self):
        fd = tempfile.TemporaryFile()
        fd.write(b'\x00' * 4096)
        return fd

    def test_atomfile_get(self):
        fd = self._getTempFile()
        with s_atomfile.getAtomFile(fd) as atom:
            self._runAtomChecks(atom)
