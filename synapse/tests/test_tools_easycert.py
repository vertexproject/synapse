
import os


import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
import synapse.tools.easycert as s_easycert


class TestEasyCert(s_t_utils.SynTest):

    def make_testca(self, path):
        '''
        Helper for making a testca named "testca"
        '''
        outp = self.getTestOutp()
        argv = ['--ca', '--certdir', path, 'testca']
        self.eq(s_easycert.main(argv, outp=outp), 0)
        self.true(outp.expect('key saved'))
        self.true(outp.expect('testca.key'))
        self.true(outp.expect('cert saved'))
        self.true(outp.expect('testca.crt'))

    def test_easycert_user_p12(self):
        with self.getTestDir() as path:

            self.make_testca(path)

            outp = self.getTestOutp()
            argv = ['--certdir', path, '--signas', 'testca', 'user@test.com']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('key saved'))
            self.true(outp.expect('user@test.com.key'))
            self.true(outp.expect('cert saved'))
            self.true(outp.expect('user@test.com.crt'))

            outp = self.getTestOutp()
            argv = ['--certdir', path, '--p12', 'user@test.com']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('client cert saved'))
            self.true(outp.expect('user@test.com.p12'))

    def test_easycert_user_sign(self):
        with self.getTestDir() as path:

            self.make_testca(path)

            outp = self.getTestOutp()
            argv = ['--certdir', path, '--signas', 'testca', 'user@test.com']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('key saved'))
            self.true(outp.expect('user@test.com.key'))
            self.true(outp.expect('cert saved'))
            self.true(outp.expect('user@test.com.crt'))

    def test_easycert_server_sign(self):
        with self.getTestDir() as path:

            self.make_testca(path)

            outp = self.getTestOutp()
            argv = ['--certdir', path, '--signas', 'testca', '--server', 'test.vertex.link']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('key saved'))
            self.true(outp.expect('test.vertex.link.key'))
            self.true(outp.expect('cert saved'))
            self.true(outp.expect('test.vertex.link.crt'))

    def test_easycert_csr(self):
        with self.getTestDir() as path:

            outp = self.getTestOutp()
            argv = ['--csr', '--certdir', path, 'user@test.com']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('key saved'))
            self.true(outp.expect('user@test.com.key'))
            self.true(outp.expect('csr saved'))
            self.true(outp.expect('user@test.com.csr'))

            # Generate a server CSR
            outp = self.getTestOutp()
            argv = ['--csr', '--certdir', path, 'wwww.vertex.link', '--server']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('key saved'))
            self.true(outp.expect('www.vertex.link.key'))
            self.true(outp.expect('csr saved'))
            self.true(outp.expect('www.vertex.link.csr'))

            outp = self.getTestOutp()
            argv = ['--csr', '--certdir', path, 'intermed', '--ca']
            self.raises(NotImplementedError, s_easycert.main, argv, outp=outp)

            # Ensure that duplicate files won't be overwritten
            outp = self.getTestOutp()
            argv = ['--csr', '--certdir', path, 'user@test.com']
            self.eq(s_easycert.main(argv, outp=outp), -1)
            self.true(outp.expect('file exists:'))
            self.true(outp.expect('user@test.com.key'))

            self.make_testca(path)

            # Sign the user csr
            outp = self.getTestOutp()
            csrpath = os.path.join(path, 'users', 'user@test.com.csr')
            argv = ['--certdir', path, '--signas', 'testca', '--sign-csr', csrpath, ]
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('cert saved:'))
            self.true(outp.expect('user@test.com.crt'))

            # Ensure we can do server certificate signing
            outp = self.getTestOutp()
            csrpath = os.path.join(path, 'hosts', 'wwww.vertex.link.csr')
            argv = ['--certdir', path, '--signas', 'testca', '--sign-csr', csrpath, '--server']
            self.eq(s_easycert.main(argv, outp=outp), 0)
            self.true(outp.expect('cert saved:'))
            self.true(outp.expect('www.vertex.link.crt'))

            # test nonexistent csr
            outp = self.getTestOutp()
            argv = ['--certdir', path, '--signas', 'testca', '--sign-csr', 'lololol', ]
            self.eq(s_easycert.main(argv, outp=outp), -1)
            self.true(outp.expect('csr not found: lololol'))

            # Test bad input
            outp = self.getTestOutp()
            argv = ['--certdir', path, '--sign-csr', 'lololol', ]
            self.eq(s_easycert.main(argv, outp=outp), -1)
            self.true(outp.expect('--sign-csr requires --signas'))

    def test_easycert_importfile(self):
        with self.getTestDir() as tstpath:

            outp = self.getTestOutp()
            fname = 'coolfile.crt'
            srcpath = s_common.genpath(tstpath, fname)
            ftype = 'cas'
            argv = ['--importfile', ftype, '--certdir', tstpath, srcpath]
            with s_common.genfile(srcpath) as fd:
                self.eq(s_easycert.main(argv, outp=outp), 0)

            outp = self.getTestOutp()
            fname = 'pennywise@vertex.link.crt'
            srcpath = s_common.genpath(tstpath, fname)
            ftype = 'cas'
            argv = ['--importfile', ftype, '--certdir', tstpath, srcpath]
            with s_common.genfile(srcpath) as fd:
                self.eq(s_easycert.main(argv, outp=outp), 0)

            outp = self.getTestOutp()
            argv = ['--importfile', 'cas', '--certdir', tstpath, 'nope']
            self.raises(s_exc.NoSuchFile, s_easycert.main, argv, outp=outp)

    def test_easycert_revokeas(self):

        with self.getTestDir() as dirn:
            outp = self.getTestOutp()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--ca', 'woot'), outp=outp))

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--signas', 'woot', 'newp@newp.newp'), outp=outp))

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--signas', 'woot', '--server', 'newp.newp'), outp=outp))

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--revokeas', 'woot', 'newp@newp.newp'), outp=outp))

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--revokeas', 'woot', '--server', 'newp.newp'), outp=outp))

            outp.clear()
            self.eq(1, s_easycert.main(('--certdir', dirn, '--revokeas', 'woot', 'noexist'), outp=outp))
            outp.expect('Certificate not found: noexist')

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--ca', 'dude'), outp=outp))

            outp.clear()
            self.eq(0, s_easycert.main(('--certdir', dirn, '--signas', 'dude', 'giggle@dude.dude'), outp=outp))

            outp.clear()
            self.eq(1, s_easycert.main(('--certdir', dirn, '--revokeas', 'woot', 'giggle@dude.dude'), outp=outp))
            outp.expect('Failed to validate that certificate was signed by woot')
