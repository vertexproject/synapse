import os
import unittest

import synapse
import synapse.datfile as s_datfile
import synapse.mindmeld as s_mindmeld

syndir = os.path.dirname( synapse.__file__ )

class DatFileTest(unittest.TestCase):

    def test_datfile_basic(self):
        with s_datfile.openDatFile('synapse.tests/test.dat') as fd:
            self.assertIsNotNone(fd)
            self.assertEqual(fd.read(), b'woot\n')

    def test_datfile_mindmeld(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyPath(syndir,datfiles=True)

        with meld.openDatFile('synapse.tests/test.dat') as fd:
            self.assertIsNotNone(fd)
            self.assertEqual(fd.read(), b'woot\n')
