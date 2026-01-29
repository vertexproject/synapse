import os

import synapse
import synapse.lib.datfile as s_datfile

import synapse.tests.utils as s_t_utils

syndir = os.path.dirname(synapse.__file__)

class DatFileTest(s_t_utils.SynTest):

    def test_datfile_basic(self):
        with s_datfile.openDatFile('synapse.tests/files/test.dat') as fd:
            self.nn(fd)
            self.eq(fd.read(), b'woot\n')
