
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
            self.eq( s_easycert.main(argv,outp=outp), 0)
            self.true( str(outp).find('cert saved') )

            argv = ['--certdir',path,'--signas','testca','user@test.com']
            self.eq( s_easycert.main(argv,outp=outp), 0)
            self.true( str(outp).find('cert saved') )

    def test_easycert_server_sign(self):
        with self.getTestDir() as path:
            outp = self.getTestOutp()

            argv = ['--ca','--certdir',path,'testca']
            self.eq( s_easycert.main(argv,outp=outp), 0)
            self.true( str(outp).find('cert saved') )

            argv = ['--certdir',path,'--signas','testca','--server','test.vertex.link']
            self.eq( s_easycert.main(argv,outp=outp), 0)
            self.true( str(outp).find('cert saved') )

    def test_easycert_csr(self):
        with self.getTestDir() as path:

            outp = self.getTestOutp()
            argv = ['--csr','--certdir',path,'user@test.com']
            self.eq( s_easycert.main(argv,outp=outp), 0)
            outp.expect('csr saved:')

            # Generate a server CSR
            outp = self.getTestOutp()
            argv = ['--csr', '--certdir', path, 'wwww.vertex.link', '--server']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            outp.expect('csr saved:')

            # Ensure that duplicate files won't be overwritten
            outp = self.getTestOutp()
            argv = ['--csr','--certdir',path,'user@test.com']
            self.eq( s_easycert.main(argv,outp=outp), -1)
            outp.expect('file exists:')

            outp = self.getTestOutp()
            argv = ['--ca','--certdir',path,'testca']
            self.eq( s_easycert.main(argv,outp=outp), 0)
            outp.expect('cert saved:')

            outp = self.getTestOutp()
            csrpath = os.path.join(path,'users','user@test.com.csr')
            argv = ['--certdir',path,'--signas','testca','--sign-csr',csrpath, ]
            self.eq( s_easycert.main(argv,outp=outp), 0)
            outp.expect('cert saved:')

            # Ensure we can do server certificate signing
            outp = self.getTestOutp()
            csrpath = os.path.join(path,'hosts','wwww.vertex.link.csr')
            argv = ['--certdir',path,'--signas','testca','--sign-csr', csrpath, '--server']
            self.eq(s_easycert.main(argv,outp=outp), 0)
            outp.expect('cert saved:')

            outp = self.getTestOutp()
            argv = ['--certdir',path,'--signas','testca','--sign-csr','lololol', ]
            self.eq( s_easycert.main(argv,outp=outp), -1)
            outp.expect('csr not found')

            # Test bad input
            outp = self.getTestOutp()
            argv = ['--certdir',path, '--sign-csr','lololol', ]
            self.eq( s_easycert.main(argv,outp=outp), -1)
            outp.expect('--sign-csr requires --signas')
