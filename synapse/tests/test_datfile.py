import os
import unittest

import synapse
import synapse.mindmeld as s_mindmeld
import synapse.lib.datfile as s_datfile

from synapse.tests.common import *

syndir = os.path.dirname(synapse.__file__)

class DatFileTest(SynTest):

    def test_datfile_basic(self):
        with s_datfile.openDatFile('synapse.tests/test.dat') as fd:
            self.nn(fd)
            self.eq(fd.read(), b'woot\n')

    def test_datfile_mindmeld(self):
        meld = s_mindmeld.MindMeld()
        meld.addPyPath(syndir, datfiles=True)

        with meld.openDatFile('synapse.tests/test.dat') as fd:
            self.nn(fd)
            self.eq(fd.read(), b'woot\n')
