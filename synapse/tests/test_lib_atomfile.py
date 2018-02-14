import tempfile
import unittest

import synapse.lib.atomfile as s_atomfile

from synapse.tests.common import *

class AtomTest(SynTest):

    def _runAtomChecks(self, atom):

        atom.resize(8192)

        byts = atom.readoff(100, 20)

        self.eq(len(byts), 20)
        self.eq(byts, b'\x00' * 20)

        atom.writeoff(100, b'asdf')
        atom.writeoff(104, b'qwer')

        self.eq(atom.readoff(100, 8), b'asdfqwer')

        # calling resize with the current size does nothing
        self.eq(atom.size, 8192)
        atom.resize(8192)
        self.eq(atom.size, 8192)

        atom.resize(4096)
        self.eq(atom.size, 4096)

    def test_atomfile_file(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'atom')

            with s_atomfile.AtomFile(path) as atom:
                self._runAtomChecks(atom)

    def test_atomfile_dir(self):

        with self.getTestDir() as dirn:

            with s_atomfile.AtomDir(dirn, filemax=12) as atom:

                atom.writeoff(3, b'asdf')
                self.eq(atom.readoff(0, 7), b'\x00\x00\x00asdf')

                self.len(1, atom.atoms)

                # across an AtomFile boundary...
                atom.writeoff(10, b'visi')
                self.eq(atom.readoff(10, 4), b'visi')
                self.eq(atom.atoms[0].size, 12)
                self.eq(atom.atoms[1].size, 2)

                # skip a whole file...
                atom.writeoff(40, b'hehe')

                self.eq(atom.size, 44)

                self.eq(atom.atoms[0].size, 12)
                self.eq(atom.atoms[1].size, 12)
                self.eq(atom.atoms[2].size, 12)
                self.eq(atom.atoms[3].size, 8)

                self.len(4, atom.atoms)

            with s_atomfile.AtomDir(dirn, filemax=12) as atom:
                self.eq(44, atom.size)
                self.len(4, atom.atoms)
