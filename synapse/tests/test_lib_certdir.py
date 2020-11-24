
import os
from contextlib import contextmanager

from OpenSSL import crypto, SSL

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
import synapse.lib.certdir as s_certdir


class CertDirTest(s_t_utils.SynTest):

    @contextmanager
    def getCertDir(self):
        '''
        Get a test CertDir object.

        Yields:
            s_certdir.CertDir: A certdir object based out of a temp directory.
        '''
        # create a temp folder and make it a cert dir
        with self.getTestDir() as dirname:
            yield s_certdir.CertDir(path=dirname)

    def basic_assertions(self, cdir, cert, key, cacert=None):
        '''
        test basic certificate assumptions

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        self.nn(cert)
        self.nn(key)

        # Make sure the certs were generated with the expected number of bits
        self.eq(cert.get_pubkey().bits(), cdir.crypto_numbits)
        self.eq(key.bits(), cdir.crypto_numbits)

        # Make sure the certs were generated with the correct version number
        self.eq(cert.get_version(), 2)

        # ensure we can sign / verify data with our keypair
        buf = b'The quick brown fox jumps over the lazy dog.'
        sig = crypto.sign(key, buf, 'sha256')
        sig2 = crypto.sign(key, buf + b'wut', 'sha256')
        self.none(crypto.verify(cert, sig, buf, 'sha256'))
        self.raises(crypto.Error, crypto.verify, cert, sig2, buf, 'sha256')

        # ensure that a ssl context using both cert/key match
        sslcontext = SSL.Context(SSL.TLSv1_2_METHOD)
        sslcontext.use_certificate(cert)
        sslcontext.use_privatekey(key)
        self.none(sslcontext.check_privatekey())

        if cacert:

            # Make sure the cert was signed by the CA
            self.eq(cert.get_issuer().der(), cacert.get_subject().der())

            store = crypto.X509Store()
            ctx = crypto.X509StoreContext(store, cert)

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            store.add_cert(cert)
            self.raises(crypto.X509StoreContextError, ctx.verify_certificate)  # unable to get local issuer certificate

            # Generate a separate CA that did not sign the certificate
            try:
                cdir.genCaCert('otherca')
            except s_exc.DupFileName:
                pass

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            store.add_cert(cdir.getCaCert('otherca'))
            self.raises(crypto.X509StoreContextError, ctx.verify_certificate)  # unable to get local issuer certificate

            # OpenSSL should be able to verify the certificate, once its CA is loaded
            store.add_cert(cacert)
            self.none(ctx.verify_certificate())  # valid

    def p12_assertions(self, cdir, cert, key, p12, cacert=None):
        '''
        test basic p12 certificate bundle assumptions

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            p12 (crypto.PKCS12): PKCS12 object to test
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        self.nn(p12)

        # Pull out the CA cert and keypair data
        p12_cacert = None
        if cacert:
            p12_cacert = p12.get_ca_certificates()
            self.nn(p12_cacert)
            self.len(1, p12_cacert)
            p12_cacert = p12_cacert[0]
            self.eq(crypto.dump_certificate(crypto.FILETYPE_ASN1, cacert), crypto.dump_certificate(crypto.FILETYPE_ASN1, p12_cacert))

        p12_cert = p12.get_certificate()
        p12_key = p12.get_privatekey()
        self.basic_assertions(cdir, p12_cert, p12_key, cacert=p12_cacert)

        # Make sure that the CA cert and keypair files are the same as the CA cert and keypair contained in the p12 file
        self.eq(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert), crypto.dump_certificate(crypto.FILETYPE_ASN1, p12_cert))
        self.eq(crypto.dump_privatekey(crypto.FILETYPE_ASN1, key), crypto.dump_privatekey(crypto.FILETYPE_ASN1, p12_key))

    def user_assertions(self, cdir, cert, key, cacert=None):
        '''
        test basic certificate assumptions for a host certificate

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        nextensions = cert.get_extension_count()
        exts = {ext.get_short_name(): ext.get_data() for ext in [cert.get_extension(i) for i in range(nextensions)]}

        nscertext = crypto.X509Extension(b'nsCertType', False, b'client')
        keyuseext = crypto.X509Extension(b'keyUsage', False, b'digitalSignature')
        extkeyuseext = crypto.X509Extension(b'extendedKeyUsage', False, b'clientAuth')
        basicconext = crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')
        self.eq(exts[b'nsCertType'], nscertext.get_data())
        self.eq(exts[b'keyUsage'], keyuseext.get_data())
        self.eq(exts[b'extendedKeyUsage'], extkeyuseext.get_data())
        self.eq(exts[b'basicConstraints'], basicconext.get_data())
        self.notin(b'subjectAltName', exts)

    def host_assertions(self, cdir, cert, key, cacert=None):
        '''
        test basic certificate assumptions for a host certificate

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        nextensions = cert.get_extension_count()
        exts = {ext.get_short_name(): ext.get_data() for ext in [cert.get_extension(i) for i in range(nextensions)]}

        nscertext = crypto.X509Extension(b'nsCertType', False, b'server')
        keyuseext = crypto.X509Extension(b'keyUsage', False, b'digitalSignature,keyEncipherment')
        extkeyuseext = crypto.X509Extension(b'extendedKeyUsage', False, b'serverAuth')
        basicconext = crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')

        self.eq(exts[b'nsCertType'], nscertext.get_data())
        self.eq(exts[b'keyUsage'], keyuseext.get_data())
        self.eq(exts[b'extendedKeyUsage'], extkeyuseext.get_data())
        self.eq(exts[b'basicConstraints'], basicconext.get_data())
        self.isin(b'subjectAltName', exts)

    def test_certdir_cas(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            inter_name = 'testsyn-intermed'
            base = cdir._getPathJoin()

            # Test that all the methods for loading the certificates return correct values for non-existant files
            self.none(cdir.getCaCert(caname))
            self.none(cdir.getCaKey(caname))
            self.false(cdir.isCaCert(caname))
            self.none(cdir.getCaCertPath(caname))
            self.none(cdir.getCaKeyPath(caname))

            # Generate a self-signed CA =======================================
            cdir.genCaCert(caname)

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getCaCert(caname), crypto.X509)
            self.isinstance(cdir.getCaKey(caname), crypto.PKey)
            self.true(cdir.isCaCert(caname))
            self.eq(cdir.getCaCertPath(caname), base + '/cas/' + caname + '.crt')
            self.eq(cdir.getCaKeyPath(caname), base + '/cas/' + caname + '.key')

            # Run basic assertions on the CA keypair
            cacert = cdir.getCaCert(caname)
            cakey = cdir.getCaKey(caname)
            self.basic_assertions(cdir, cacert, cakey)

            # Generate intermediate CA ========================================
            cdir.genCaCert(inter_name, signas=caname)

            # Run basic assertions, make sure that it was signed by the root CA
            inter_cacert = cdir.getCaCert(inter_name)
            inter_cakey = cdir.getCaKey(inter_name)
            self.basic_assertions(cdir, inter_cacert, inter_cakey, cacert=cacert)

    def test_certdir_hosts(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            hostname = 'visi.vertex.link'
            hostname_unsigned = 'unsigned.vertex.link'
            base = cdir._getPathJoin()

            cdir.genCaCert(caname)

            cacert = cdir.getCaCert(caname)

            # Test that all the methods for loading the certificates return correct values for non-existant files
            self.none(cdir.getHostCert(hostname_unsigned))
            self.none(cdir.getHostKey(hostname_unsigned))
            self.false(cdir.isHostCert(hostname_unsigned))
            self.none(cdir.getHostCertPath(hostname_unsigned))
            self.none(cdir.getHostKeyPath(hostname_unsigned))
            self.none(cdir.getHostCaPath(hostname_unsigned))

            # Generate a self-signed host keypair =============================
            cdir.genHostCert(hostname_unsigned)

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getHostCert(hostname_unsigned), crypto.X509)
            self.isinstance(cdir.getHostKey(hostname_unsigned), crypto.PKey)
            self.true(cdir.isHostCert(hostname_unsigned))
            self.eq(cdir.getHostCertPath(hostname_unsigned), base + '/hosts/' + hostname_unsigned + '.crt')
            self.eq(cdir.getHostKeyPath(hostname_unsigned), base + '/hosts/' + hostname_unsigned + '.key')
            self.none(cdir.getHostCaPath(hostname_unsigned))  # the cert is self-signed, so there is no ca cert

            # Run basic assertions on the host keypair
            cert = cdir.getHostCert(hostname_unsigned)
            key = cdir.getHostKey(hostname_unsigned)
            self.basic_assertions(cdir, cert, key)
            self.host_assertions(cdir, cert, key)

            # Generate a signed host keypair ==================================
            cdir.genHostCert(hostname, signas=caname)

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getHostCert(hostname), crypto.X509)
            self.isinstance(cdir.getHostKey(hostname), crypto.PKey)
            self.true(cdir.isHostCert(hostname))
            self.eq(cdir.getHostCertPath(hostname), base + '/hosts/' + hostname + '.crt')
            self.eq(cdir.getHostKeyPath(hostname), base + '/hosts/' + hostname + '.key')
            self.eq(cdir.getHostCaPath(hostname), base + '/cas/' + caname + '.crt')  # the cert is signed, so there is a ca cert

            # Run basic assertions on the host keypair
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)
            self.basic_assertions(cdir, cert, key, cacert=cacert)
            self.host_assertions(cdir, cert, key, cacert=cacert)

    def test_certdir_users(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            username = 'visi@vertex.link'
            username_unsigned = 'unsigned@vertex.link'
            base = cdir._getPathJoin()

            cdir.genCaCert(caname)
            cacert = cdir.getCaCert(caname)

            # Test that all the methods for loading the certificates return correct values for non-existant files
            self.none(cdir.getUserCert(username_unsigned))
            self.none(cdir.getUserKey(username_unsigned))
            self.none(cdir.getClientCert(username_unsigned))
            self.false(cdir.isUserCert(username_unsigned))
            self.false(cdir.isClientCert(username_unsigned))
            self.none(cdir.getUserCertPath('nope'))
            self.none(cdir.getUserKeyPath('nope'))
            self.none(cdir.getUserCaPath('nope'))
            self.none(cdir.getUserForHost('nope', 'host.vertex.link'))

            # Generate a self-signed user keypair =============================
            cdir.genUserCert(username_unsigned)
            self.raises(s_exc.NoSuchFile, cdir.genClientCert, username_unsigned)

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getUserCert(username_unsigned), crypto.X509)
            self.isinstance(cdir.getUserKey(username_unsigned), crypto.PKey)
            self.none(cdir.getClientCert(username_unsigned))
            self.true(cdir.isUserCert(username_unsigned))
            self.false(cdir.isClientCert(username_unsigned))
            self.eq(cdir.getUserCertPath(username_unsigned), base + '/users/' + username_unsigned + '.crt')
            self.eq(cdir.getUserKeyPath(username_unsigned), base + '/users/' + username_unsigned + '.key')
            self.none(cdir.getUserCaPath(username_unsigned))  # no CA
            self.eq(cdir.getUserForHost('unsigned', 'host.vertex.link'), username_unsigned)

            # Run basic assertions on the host keypair
            cert = cdir.getUserCert(username_unsigned)
            key = cdir.getUserKey(username_unsigned)
            self.basic_assertions(cdir, cert, key)
            self.user_assertions(cdir, cert, key)

            # Generate a signed user keypair ==================================
            cdir.genUserCert(username, signas=caname)
            cdir.genClientCert(username)

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getUserCert(username), crypto.X509)
            self.isinstance(cdir.getUserKey(username), crypto.PKey)
            self.isinstance(cdir.getClientCert(username), crypto.PKCS12)
            self.true(cdir.isUserCert(username))
            self.true(cdir.isClientCert(username))
            self.eq(cdir.getUserCertPath(username), base + '/users/' + username + '.crt')
            self.eq(cdir.getUserKeyPath(username), base + '/users/' + username + '.key')
            self.eq(cdir.getUserCaPath(username), base + '/cas/' + caname + '.crt')
            self.eq(cdir.getUserForHost('visi', 'host.vertex.link'), username)

            # Run basic assertions on the host keypair
            cert = cdir.getUserCert(username)
            key = cdir.getUserKey(username)
            p12 = cdir.getClientCert(username)
            self.basic_assertions(cdir, cert, key, cacert=cacert)
            self.user_assertions(cdir, cert, key, cacert=cacert)
            self.p12_assertions(cdir, cert, key, p12, cacert=cacert)

            # Test missing files for generating a client cert
            os.remove(base + '/users/' + username + '.key')
            self.raises(s_exc.NoSuchFile, cdir.genClientCert, username)  # user key
            os.remove(base + '/cas/' + caname + '.crt')
            self.raises(s_exc.NoSuchFile, cdir.genClientCert, username)  # ca crt
            os.remove(base + '/users/' + username + '.crt')
            self.raises(s_exc.NoSuchFile, cdir.genClientCert, username)  # user crt

    def test_certdir_hosts_sans(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            cdir.genCaCert(caname)

            # Host cert with multiple SANs ====================================
            hostname = 'visi.vertex.link'
            sans = 'DNS:vertex.link,DNS:visi.vertex.link,DNS:vertex.link'
            cdir.genHostCert(hostname, signas=caname, sans=sans)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x1f\x82\x0bvertex.link\x82\x10visi.vertex.link')  # ASN.1 encoded subjectAltName data

            # Host cert with no specified SANs ================================
            hostname = 'visi2.vertex.link'
            cdir.genHostCert(hostname, signas=caname)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x13\x82\x11visi2.vertex.link')  # ASN.1 encoded subjectAltName data

            # Self-signed Host cert with no specified SANs ====================
            hostname = 'visi3.vertex.link'
            cdir.genHostCert(hostname)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x13\x82\x11visi3.vertex.link')  # ASN.1 encoded subjectAltName data

    def test_certdir_hosts_csr(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            hostname = 'visi.vertex.link'

            # Generate CA cert and host CSR
            cdir.genCaCert(caname)
            cdir.genHostCsr(hostname)
            path = cdir._getPathJoin('hosts', hostname + '.csr')
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            pkey, pcert = cdir.signHostCsr(xcsr, caname)
            self.isinstance(pkey, crypto.PKey)
            self.isinstance(pcert, crypto.X509)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)
            self.basic_assertions(cdir, cert, key, cacert=cacert)

    def test_certdir_users_csr(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'syntest'
            username = 'visi@vertex.link'

            # Generate CA cert and user CSR
            cdir.genCaCert(caname)
            cdir.genUserCsr(username)
            path = cdir._getPathJoin('users', username + '.csr')
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            pkey, pcert = cdir.signUserCsr(xcsr, caname)
            self.isinstance(pkey, crypto.PKey)
            self.isinstance(pcert, crypto.X509)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getUserCert(username)
            key = cdir.getUserKey(username)
            self.basic_assertions(cdir, cert, key, cacert=cacert)

    def test_certdir_importfile(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            with self.getTestDir() as testpath:

                # File doesn't exist
                fpath = s_common.genpath(testpath, 'not_real.crt')
                self.raises(s_exc.NoSuchFile, cdir.importFile, fpath, 'cas')

                # File has unsupported extension
                fpath = s_common.genpath(testpath, 'coolpic.bmp')
                with s_common.genfile(fpath) as fd:
                    self.raises(s_exc.BadFileExt, cdir.importFile, fpath, 'cas')

                tests = (
                    ('cas', 'coolca.crt'),
                    ('cas', 'coolca.key'),
                    ('hosts', 'coolhost.crt'),
                    ('hosts', 'coolhost.key'),
                    ('users', 'cooluser.crt'),
                    ('users', 'cooluser.key'),
                    ('users', 'cooluser.p12'),
                )
                for ftype, fname in tests:
                    srcpath = s_common.genpath(testpath, fname)
                    dstpath = s_common.genpath(cdir.certdirs[0], ftype, fname)

                    with s_common.genfile(srcpath) as fd:
                        fd.write(b'arbitrary data')
                        fd.seek(0)

                        # Make sure the file is not there
                        self.raises(s_exc.NoSuchFile, s_common.reqfile, dstpath)

                        # Import it and make sure it exists
                        self.none(cdir.importFile(srcpath, ftype))
                        with s_common.reqfile(dstpath) as dstfd:
                            self.eq(dstfd.read(), b'arbitrary data')

                        # Make sure it can't be overwritten
                        self.raises(s_exc.FileExists, cdir.importFile, srcpath, ftype)

    def test_certdir_valUserCert(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            cdir._getPathJoin()
            cdir.genCaCert('syntest')
            cdir.genCaCert('newp')
            cdir.getCaCerts()
            syntestca = cdir.getCaCert('syntest')
            newpca = cdir.getCaCert('newp')

            self.raises(crypto.Error, cdir.valUserCert, b'')

            cdir.genUserCert('cool')
            path = cdir.getUserCertPath('cool')
            byts = cdir._getPathBytes(path)

            self.raises(crypto.X509StoreContextError, cdir.valUserCert, byts)

            cdir.genUserCert('cooler', signas='syntest')
            path = cdir.getUserCertPath('cooler')
            byts = cdir._getPathBytes(path)
            self.nn(cdir.valUserCert(byts))
            self.nn(cdir.valUserCert(byts, cacerts=(syntestca,)))
            self.raises(crypto.X509StoreContextError, cdir.valUserCert, byts, cacerts=(newpca,))
            self.raises(crypto.X509StoreContextError, cdir.valUserCert, byts, cacerts=())

            cdir.genUserCert('coolest', signas='newp')
            path = cdir.getUserCertPath('coolest')
            byts = cdir._getPathBytes(path)
            self.nn(cdir.valUserCert(byts))
            self.nn(cdir.valUserCert(byts, cacerts=(newpca,)))
            self.raises(crypto.X509StoreContextError, cdir.valUserCert, byts, cacerts=(syntestca,))
            self.raises(crypto.X509StoreContextError, cdir.valUserCert, byts, cacerts=())

    def test_certdir_sslctx(self):

        with self.getCertDir() as cdir:

            with self.raises(s_exc.NoSuchCert):
                cdir.getClientSSLContext(certname='newp')

            with s_common.genfile(cdir.certdirs[0], 'users', 'newp.crt') as fd:
                fd.write(b'asdf')

            with self.raises(s_exc.NoCertKey):
                cdir.getClientSSLContext(certname='newp')
