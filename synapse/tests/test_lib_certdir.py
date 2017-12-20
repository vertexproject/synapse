from contextlib import contextmanager

from OpenSSL import crypto

from synapse.tests.common import *
import synapse.lib.certdir as s_certdir

class CertDirTest(SynTest):

    @contextmanager
    def getCertDir(self):
        # create a temp folder and make it a cert dir
        with self.getTestDir() as dirname:
            cdir = s_certdir.CertDir(path=dirname)
            yield cdir

    def basic_assertions(self, cdir, cert, key, cacert=None):
        self.nn(cert)
        self.nn(key)

        # Make sure the certs were generated with the expected number of bits
        self.eq(cert.get_pubkey().bits(), cdir.crypto_numbits)
        self.eq(key.bits(), cdir.crypto_numbits)

        # Make sure the certs were generated with the correct version number
        self.eq(cert.get_version(), 2)

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
            except DupFileName:
                pass

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            store.add_cert(cdir.getCaCert('otherca'))
            self.raises(crypto.X509StoreContextError, ctx.verify_certificate)  # unable to get local issuer certificate

            # OpenSSL should be able to verify the certificate, once its CA is loaded
            store.add_cert(cacert)
            self.none(ctx.verify_certificate())  # valid

    def p12_assertions(self, cdir, cert, key, p12, cacert=None):
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

    def test_certdir_cas(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            inter_name = 'testsyn-intermed'
            base = cdir.getPathJoin()

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
        with self.getCertDir() as cdir:
            caname = 'syntest'
            hostname = 'visi.vertex.link'
            hostname_unsigned = 'unsigned.vertex.link'
            base = cdir.getPathJoin()

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

    def test_certdir_users(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            username = 'visi@vertex.link'
            username_unsigned = 'unsigned@vertex.link'
            base = cdir.getPathJoin()

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

            # Test that all the methods for loading the certificates work
            self.isinstance(cdir.getUserCert(username_unsigned), crypto.X509)
            self.isinstance(cdir.getUserKey(username_unsigned), crypto.PKey)
            self.isinstance(cdir.getClientCert(username_unsigned), crypto.PKCS12)
            self.true(cdir.isUserCert(username_unsigned))
            self.true(cdir.isClientCert(username_unsigned))
            self.eq(cdir.getUserCertPath(username_unsigned), base + '/users/' + username_unsigned + '.crt')
            self.eq(cdir.getUserKeyPath(username_unsigned), base + '/users/' + username_unsigned + '.key')
            self.none(cdir.getUserCaPath(username_unsigned))  # no CA
            self.eq(cdir.getUserForHost('unsigned', 'host.vertex.link'), username_unsigned)

            # Run basic assertions on the host keypair
            cert = cdir.getUserCert(username_unsigned)
            key = cdir.getUserKey(username_unsigned)
            p12 = cdir.getClientCert(username_unsigned)
            self.basic_assertions(cdir, cert, key)
            self.p12_assertions(cdir, cert, key, p12)

            # Generate a signed user keypair ==================================
            cdir.genUserCert(username, signas=caname)

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
            self.p12_assertions(cdir, cert, key, p12, cacert=cacert)

    def test_certdir_hosts_sans(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            cdir.genCaCert(caname)

            # Host cert with multiple SANs ====================================
            hostname = 'visi.vertex.link'
            sans = 'DNS:vertex.link,DNS:visi.vertex.link,DNS:vertex.link'
            cdir.genHostCert(hostname, signas=caname, sans=sans)

            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x1f\x82\x0bvertex.link\x82\x10visi.vertex.link')  # ASN.1 encoded subjectAltName data

            # Host cert with no specified SANs ================================
            hostname = 'visi2.vertex.link'
            cdir.genHostCert(hostname, signas=caname)

            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x13\x82\x11visi2.vertex.link')  # ASN.1 encoded subjectAltName data

            # Self-signed Host cert with no specified SANs ====================
            hostname = 'visi3.vertex.link'
            cdir.genHostCert(hostname)

            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)

            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x13\x82\x11visi3.vertex.link')  # ASN.1 encoded subjectAltName data

    def test_certdir_hosts_csr(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            hostname = 'visi.vertex.link'

            # Generate CA cert and host CSR
            cdir.genCaCert(caname)
            cdir.genHostCsr(hostname)
            path = cdir.getPathJoin('hosts', hostname + '.csr')
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            cdir.signHostCsr(xcsr, caname)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)
            self.basic_assertions(cdir, cert, key, cacert=cacert)

    def test_certdir_users_csr(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            username = 'visi@vertex.link'

            # Generate CA cert and user CSR
            cdir.genCaCert(caname)
            cdir.genUserCsr(username)
            path = cdir.getPathJoin('users', username + '.csr')
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            cdir.signUserCsr(xcsr, caname)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getUserCert(username)
            key = cdir.getUserKey(username)
            self.basic_assertions(cdir, cert, key, cacert=cacert)
