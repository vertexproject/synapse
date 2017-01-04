
from synapse.tests.common import *

import synapse.tools.easycert as s_easycert

    #pars.add_argument('--certdir', default='~/.syn/certs', help='Directory for certs/keys')
    ##pars.add_argument('--signas', help='sign the new cert with the given cert name')
    #pars.add_argument('--ca', default=False, action='store_true', help='mark the certificate as a CA/CRL signer')

class TestEasyCert(SynTest):

    def test_easycert_user_sign(self):
        with self.getTestDir() as path:
            outp = self.getTestOutp()

            argv = ['--ca','--certdir',path,'testca']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            self.assertTrue( str(outp).find('cert saved') )

            argv = ['--certdir',path,'--signas','testca','user@test.com']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            self.assertTrue( str(outp).find('cert saved') )

    def test_easycert_server_sign(self):
        with self.getTestDir() as path:
            outp = self.getTestOutp()

            argv = ['--ca','--certdir',path,'testca']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            self.assertTrue( str(outp).find('cert saved') )

            argv = ['--certdir',path,'--signas','testca','--server','test.vertex.link']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            self.assertTrue( str(outp).find('cert saved') )

    def test_easycert_csr(self):
        with self.getTestDir() as path:

            outp = self.getTestOutp()
            argv = ['--gen-csr','--certdir',path,'user@test.com']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            outp.expect('csr saved:')

            outp = self.getTestOutp()
            argv = ['--ca','--certdir',path,'testca']
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            outp.expect('cert saved:')

            outp = self.getTestOutp()
            csrpath = os.path.join(path,'user@test.com.csr')
            argv = ['--certdir',path,'--signas','testca','--sign-csr',csrpath ]
            self.assertEqual( s_easycert.main(argv,outp=outp), 0)
            outp.expect('cert saved:')
