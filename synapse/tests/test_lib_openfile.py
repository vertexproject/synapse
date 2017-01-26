from synapse.tests.common import *

import synapse.lib.openfile as s_openfile

class OpenFileTest(SynTest):

    def test_openfile_abs(self):

        with self.getTestDir() as dirname:

            with genfile(dirname,'foo.bin') as fd:
                fd.write(b'asdfqwer')

            path = genpath(dirname,'foo.bin')
            with s_openfile.openfd(path) as fd:
                self.eq( fd.read(), b'asdfqwer' )

    def test_openfile_relative(self):

        with self.getTestDir() as dirname:

            with genfile(dirname,'foo.bin') as fd:
                fd.write(b'asdfqwer')

            opts = {'file:basedir':dirname}
            with s_openfile.openfd('foo.bin',**opts) as fd:
                self.eq( fd.read(), b'asdfqwer' )

    def test_openfile_http(self):
        self.skipIfNoInternet()
        with s_openfile.openfd('http://data.iana.org/TLD/tlds-alpha-by-domain.txt') as fd:
            self.assertTrue( fd.read().find(b'LINK') != -1 )
