import os
import ssl
import contextlib

from OpenSSL import crypto

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils
import synapse.tools.genpkg as s_genpkg

import cryptography.x509 as c_x509
import cryptography.exceptions as c_exc
import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.ec as c_ec
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding
import cryptography.hazmat.primitives.serialization as c_serialization
import cryptography.hazmat.primitives.serialization.pkcs12 as c_pkcs12


class CertDirTest(s_t_utils.SynTest):

    @contextlib.contextmanager
    def getCertDir(self) -> contextlib.AbstractContextManager[s_certdir.CertDir, None, None]:
        '''
        Get a test CertDir object.

        Yields:
            A certdir object based out of a temp directory.
        '''
        # create a temp folder and make it a cert dir
        with self.getTestDir() as dirname:
            yield s_certdir.CertDir(path=dirname)

    def basic_assertions(self,
                         cdir: s_certdir.CertDir,
                         cert: c_x509.Certificate,
                         key: s_certdir.Pkey,
                         cacert: c_x509.Certificate =None):
        '''
        test basic certificate assumptions

        Args:
            cdir: certdir object
            cert: Cert to test
            key: Key for the certification
            cacert: Corresponding CA cert (optional)
        '''
        self.nn(cert)
        self.nn(key)

        pubkey = cert.public_key()

        # Make sure the certs were generated with the expected number of bits
        self.eq(pubkey.key_size, cdir.crypto_numbits)
        self.eq(key.key_size, cdir.crypto_numbits)

        # Make sure the certs were generated with the correct version number
        self.eq(cert.version.value, 2)

        # ensure we can sign / verify data with our keypair
        buf = b'The quick brown fox jumps over the lazy dog.'

        sig = key.sign(data=buf,
                       padding=c_padding.PSS(mgf=c_padding.MGF1(c_hashes.SHA256()),
                                             salt_length=c_padding.PSS.MAX_LENGTH),
                       algorithm=c_hashes.SHA256(),
                       )
        sig2 = key.sign(data=buf + b'wut',
                       padding=c_padding.PSS(mgf=c_padding.MGF1(c_hashes.SHA256()),
                                             salt_length=c_padding.PSS.MAX_LENGTH),
                       algorithm=c_hashes.SHA256(),
                       )

        result = pubkey.verify(signature=sig,
                               data=buf,
                               padding=c_padding.PSS(mgf=c_padding.MGF1(c_hashes.SHA256()),
                                                     salt_length=c_padding.PSS.MAX_LENGTH),
                               algorithm=c_hashes.SHA256(),)
        self.none(result)

        with self.raises(c_exc.InvalidSignature):
            pubkey.verify(signature=sig2,
                          data=buf,
                          padding=c_padding.PSS(mgf=c_padding.MGF1(c_hashes.SHA256()),
                                                salt_length=c_padding.PSS.MAX_LENGTH),
                          algorithm=c_hashes.SHA256(), )

        self.eq(key.public_key(), pubkey)

        if cacert:

            # Make sure the cert was signed by the CA
            cert_issuer = cert.issuer.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
            cacert_subj = cacert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
            self.eq(cert_issuer, cacert_subj)

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            pyopenssl_cert = crypto.X509.from_cryptography(cert)
            pyopenssl_cacert = crypto.X509.from_cryptography(cacert)

            store = crypto.X509Store()
            ctx = crypto.X509StoreContext(store, pyopenssl_cert)

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            store.add_cert(pyopenssl_cert)

            with self.raises(crypto.X509StoreContextError) as cm:
                ctx.verify_certificate()

            self.isin('unable to get local issuer certificate', str(cm.exception))

            # Generate a separate CA that did not sign the certificate
            try:
                (_, otherca_cert) = cdir.genCaCert('otherca')
            except s_exc.DupFileName as e:
                otherca_cert = cdir.getCaCert('otherca')
            pyopenssl_otherca_cert = crypto.X509.from_cryptography(otherca_cert)

            # OpenSSL should NOT be able to verify the certificate if its CA is not loaded
            store.add_cert(pyopenssl_otherca_cert)
            with self.raises(crypto.X509StoreContextError) as cm:
                # unable to get local issuer certificate
                ctx.verify_certificate()
            self.isin('unable to get local issuer certificate', str(cm.exception))

            # OpenSSL should be able to verify the certificate, once its CA is loaded
            store.add_cert(pyopenssl_cacert)
            self.none(ctx.verify_certificate())  # valid

    def host_assertions(self,
                        cdir: s_certdir.CertDir,
                        cert: c_x509.Certificate,
                        key: s_certdir.Pkey,
                        cacert: c_x509.Certificate = None):
        '''
        test basic certificate assumptions for a host certificate

        Args:
            cdir: certdir object
            cert: Cert to test
            key: Key for the certification
            cacert: Corresponding CA cert (optional)
        '''

        reqbc = c_x509.BasicConstraints(ca=False, path_length=None)
        reqeku = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.SERVER_AUTH])
        reqku = c_x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
                                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                crl_sign=False, encipher_only=False, decipher_only=False)
        reqnstype = c_x509.UnrecognizedExtension(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID),
                                                 value=s_certdir.NSCERTTYPE_SERVER)

        bc = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS)
        self.eq(reqbc, bc.value)

        ku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.KEY_USAGE)
        self.eq(reqku, ku.value)

        eku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE)
        self.eq(reqeku, eku.value)

        nstype = cert.extensions.get_extension_for_oid(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID))
        self.eq(reqnstype, nstype.value)

        expected_oids = sorted([
            c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS.dotted_string,
            c_x509.oid.ExtensionOID.KEY_USAGE.dotted_string,
            c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE.dotted_string,
            c_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME.dotted_string,
            s_certdir.NSCERTTYPE_OID,
        ])

        ext_oids = sorted([ext.oid.dotted_string for ext in cert.extensions])
        self.eq(expected_oids, ext_oids)

    def user_assertions(self,
                        cdir: s_certdir.CertDir,
                        cert: c_x509.Certificate,
                        key: s_certdir.Pkey,
                        cacert: c_x509.Certificate = None):
        '''
        test basic certificate assumptions for a user certificate

        Args:
            cdir: certdir object
            cert: Cert to test
            key: Key for the certification
            cacert: Corresponding CA cert (optional)
        '''
        reqbc = c_x509.BasicConstraints(ca=False, path_length=None)
        reqeku = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH])
        reqku = c_x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                crl_sign=False, encipher_only=False, decipher_only=False)
        reqnstype = c_x509.UnrecognizedExtension(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID),
                                                 value=s_certdir.NSCERTTYPE_CLIENT)

        bc = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS)
        self.eq(reqbc, bc.value)

        ku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.KEY_USAGE)
        self.eq(reqku, ku.value)

        eku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE)
        self.eq(reqeku, eku.value)

        nstype = cert.extensions.get_extension_for_oid(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID))
        self.eq(reqnstype, nstype.value)

        expected_oids = sorted([
            c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS.dotted_string,
            c_x509.oid.ExtensionOID.KEY_USAGE.dotted_string,
            c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE.dotted_string,
            s_certdir.NSCERTTYPE_OID,
        ])

        ext_oids = sorted([ext.oid.dotted_string for ext in cert.extensions])
        self.eq(expected_oids, ext_oids)

    def p12_assertions(self,
                       cdir: s_certdir.CertDir,
                       cert: c_x509.Certificate,
                       key: s_certdir.Pkey,
                       p12: c_pkcs12.PKCS12KeyAndCertificates,
                       cacert: c_x509.Certificate = None):
        '''
        test basic p12 certificate bundle assumptions

        Args:
            cdir: certdir object
            cert: Cert to test
            key: Key for the certification
            p12: PKCS12 object to test
            cacert: Corresponding CA cert (optional)
        '''
        self.nn(p12)

        # Pull out the CA cert and keypair data
        p12_cacert = None
        if cacert:
            p12_cacert = p12.additional_certs
            self.nn(p12_cacert)
            self.len(1, p12_cacert)
            p12_cacert = p12_cacert[0].certificate
            _pb = p12_cacert.public_bytes(c_serialization.Encoding.PEM)
            _cb = cacert.public_bytes(c_serialization.Encoding.PEM)
            self.eq(_cb, _pb)

        p12_cert = p12.cert.certificate
        p12_key = p12.key
        self.basic_assertions(cdir, p12_cert, p12_key, cacert=p12_cacert)

        # Make sure that the CA cert and keypair files are the same as the CA cert and keypair contained in the p12 file
        _pb = p12_cert.public_bytes(c_serialization.Encoding.PEM)
        _cb = cert.public_bytes(c_serialization.Encoding.PEM)
        self.eq(_cb, _pb)

        _pb = p12_key.private_bytes(encoding=c_serialization.Encoding.PEM,
                                    format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                                    encryption_algorithm=c_serialization.NoEncryption())
        _cb = key.private_bytes(encoding=c_serialization.Encoding.PEM,
                                    format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                                    encryption_algorithm=c_serialization.NoEncryption())
        self.eq(_cb, _pb)

    def code_assertions(self,
                        cdir: s_certdir.CertDir,
                        cert: c_x509.Certificate,
                        key: s_certdir.Pkey,
                        cacert: c_x509.Certificate = None
                        ):
        reqbc = c_x509.BasicConstraints(ca=False, path_length=None)
        reqeku = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING])
        reqku = c_x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                crl_sign=False, encipher_only=False, decipher_only=False)
        reqnstype = c_x509.UnrecognizedExtension(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID),
                                                 value=s_certdir.NSCERTTYPE_OBJSIGN)

        bc = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS)
        self.eq(reqbc, bc.value)

        ku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.KEY_USAGE)
        self.eq(reqku, ku.value)

        eku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE)
        self.eq(reqeku, eku.value)

        nstype = cert.extensions.get_extension_for_oid(c_x509.ObjectIdentifier(s_certdir.NSCERTTYPE_OID))
        self.eq(reqnstype, nstype.value)

        expected_oids = sorted([
            c_x509.oid.ExtensionOID.BASIC_CONSTRAINTS.dotted_string,
            c_x509.oid.ExtensionOID.KEY_USAGE.dotted_string,
            c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE.dotted_string,
            s_certdir.NSCERTTYPE_OID,
        ])

        ext_oids = sorted([ext.oid.dotted_string for ext in cert.extensions])
        self.eq(expected_oids, ext_oids)

    def test_certdir_cas(self):

        with self.getCertDir() as cdir:
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
            self.isinstance(cdir.getCaCert(caname), c_x509.Certificate)
            self.isinstance(cdir.getCaKey(caname), c_rsa.RSAPrivateKey)  # We do RSA private keys out of the box
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

            # Per RFC5280 common-name has a length of 1 to 64 characters
            # https://datatracker.ietf.org/doc/html/rfc5280#appendix-A.1
            c64 = 'V' * 64
            cakey64, cacert64 = cdir.genCaCert(c64)
            self.basic_assertions(cdir, cacert64, cakey64)

            c1 = 'V' * 1
            cakey1, cacert1 = cdir.genCaCert(c1)
            self.basic_assertions(cdir, cacert1, cakey1)

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genCaCert('V' * 65)

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genCaCert('')

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genCaCert('V' * 63 + 'ॐ')

    def test_certdir_hosts(self):
        with self.getCertDir() as cdir:
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
            self.isinstance(cdir.getHostCert(hostname_unsigned), c_x509.Certificate)
            self.isinstance(cdir.getHostKey(hostname_unsigned), c_rsa.RSAPrivateKey)
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
            self.isinstance(cdir.getHostCert(hostname), c_x509.Certificate)
            self.isinstance(cdir.getHostKey(hostname), c_rsa.RSAPrivateKey)
            self.true(cdir.isHostCert(hostname))
            self.eq(cdir.getHostCertPath(hostname), base + '/hosts/' + hostname + '.crt')
            self.eq(cdir.getHostKeyPath(hostname), base + '/hosts/' + hostname + '.key')
            self.eq(cdir.getHostCaPath(hostname), base + '/cas/' + caname + '.crt')  # the cert is signed, so there is a ca cert

            # Run basic assertions on the host keypair
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)
            self.basic_assertions(cdir, cert, key, cacert=cacert)
            self.host_assertions(cdir, cert, key, cacert=cacert)

            # Get cert host hashes
            self.none(cdir.getHostCertHash('newp.host'))
            chash = cdir.getHostCertHash(hostname)
            self.isinstance(chash, str)
            self.len(64, chash)

    def test_certdir_users(self):
        with self.getCertDir() as cdir:
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
            self.isinstance(cdir.getUserCert(username_unsigned), c_x509.Certificate)
            self.isinstance(cdir.getUserKey(username_unsigned), c_rsa.RSAPrivateKey)
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
            self.isinstance(cdir.getUserCert(username), c_x509.Certificate)
            self.isinstance(cdir.getUserKey(username), c_rsa.RSAPrivateKey)
            self.isinstance(cdir.getClientCert(username), c_pkcs12.PKCS12KeyAndCertificates)
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
        with self.getCertDir() as cdir:
            caname = 'syntest'
            cdir.genCaCert(caname)

            # Host cert with multiple SANs ====================================
            hostname = 'visi.vertex.link'
            sans = 'DNS:vertex.link,DNS:visi.vertex.link,DNS:vertex.link'
            cdir.genHostCert(hostname, signas=caname, sans=sans)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            ext = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            self.len(2, ext.value)
            self.eq(ext.value.get_values_for_type(c_x509.DNSName), ['vertex.link', 'visi.vertex.link'])

            # Host cert with no specified SANs ================================
            hostname = 'visi2.vertex.link'
            cdir.genHostCert(hostname, signas=caname)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            ext = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            self.len(1, ext.value)
            self.eq(ext.value.get_values_for_type(c_x509.DNSName), ['visi2.vertex.link'])

            # Self-signed Host cert with no specified SANs ====================
            hostname = 'visi3.vertex.link'
            cdir.genHostCert(hostname)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            ext = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            self.len(1, ext.value)
            self.eq(ext.value.get_values_for_type(c_x509.DNSName), ['visi3.vertex.link'])

            # Backwards compatibility with pyopenssl sans specifiers which we can get from easycert
            hostname = 'stuff.vertex.link'
            sans = 'DNS:wow.com,email:clown@vertex.link,URI:https://hehe.haha.vertex.link,email:hehe@vertex.link'
            cdir.genHostCert(hostname, signas=caname, sans=sans)

            cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            cdir.getHostKey(hostname)

            ext = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            self.len(5, ext.value)
            self.eq(ext.value.get_values_for_type(c_x509.DNSName), ['stuff.vertex.link', 'wow.com'])
            self.eq(ext.value.get_values_for_type(c_x509.RFC822Name), ['clown@vertex.link', 'hehe@vertex.link'])
            self.eq(ext.value.get_values_for_type(c_x509.UniformResourceIdentifier), ['https://hehe.haha.vertex.link'])

            hostname = 'newp.vertex.link'
            sans = 'DNS:wow.com,email:clown@vertex.link,HAHA:yeahRight!'
            with self.raises(s_exc.BadArg):
                cdir.genHostCert(hostname, signas=caname, sans=sans)

    def test_certdir_hosts_csr(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            hostname = 'visi.vertex.link'

            # Generate CA cert and host CSR
            cdir.genCaCert(caname)
            cdir.genHostCsr(hostname)
            self.none(cdir.getHostCsrPath('newp'))
            path = cdir.getHostCsrPath(hostname)
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            pkey, pcert = cdir.signHostCsr(xcsr, caname)
            self.none(pkey)
            self.isinstance(pcert, c_x509.Certificate)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getHostCert(hostname)
            key = cdir.getHostKey(hostname)
            self.basic_assertions(cdir, cert, key, cacert=cacert)

            # Per RFC5280 common-name has a length of 1 to 64 characters
            # Do not generate CSRs which exceed that name range.
            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genHostCsr('V' * 65)

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genHostCsr('')

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genHostCsr('V' * 63 + 'ॐ')

    def test_certdir_users_csr(self):
        with self.getCertDir() as cdir:
            caname = 'syntest'
            username = 'visi@vertex.link'

            # Generate CA cert and user CSR
            cdir.genCaCert(caname)
            cdir.genUserCsr(username)
            self.none(cdir.getUserCsrPath('newp'))
            path = cdir.getUserCsrPath(username)
            xcsr = cdir._loadCsrPath(path)

            # Sign the CSR as the CA
            pkey, pcert = cdir.signUserCsr(xcsr, caname)
            self.none(pkey)
            self.isinstance(pcert, c_x509.Certificate)

            # Validate the keypair
            cacert = cdir.getCaCert(caname)
            cert = cdir.getUserCert(username)
            key = cdir.getUserKey(username)
            self.basic_assertions(cdir, cert, key, cacert=cacert)

            # Per RFC5280 common-name has a length of 1 to 64 characters
            # Do not generate CSRs which exceed that name range.
            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genUserCsr('V' * 65)

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genUserCsr('')

            with self.raises(s_exc.CryptoErr) as cm:
                cdir.genUserCsr('V' * 63 + 'ॐ')

    def test_certdir_importfile(self):
        with self.getCertDir() as cdir:
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
        with self.getCertDir() as cdir:
            cdir._getPathJoin()
            cdir.genCaCert('syntest')
            cdir.genCaCert('newp')
            cdir.getCaCerts()
            syntestca = cdir.getCaCert('syntest')
            newpca = cdir.getCaCert('newp')

            with self.raises(s_exc.BadCertBytes):
                cdir.valUserCert(b'')

            cdir.genUserCert('cool')
            path = cdir.getUserCertPath('cool')
            byts = cdir._getPathBytes(path)

            self.raises(s_exc.BadCertVerify, cdir.valUserCert, byts)

            cdir.genUserCert('cooler', signas='syntest')
            path = cdir.getUserCertPath('cooler')
            byts = cdir._getPathBytes(path)
            self.nn(cdir.valUserCert(byts))
            self.nn(cdir.valUserCert(byts, cacerts=(syntestca,)))
            self.raises(s_exc.BadCertVerify, cdir.valUserCert, byts, cacerts=(newpca,))
            self.raises(s_exc.BadCertVerify, cdir.valUserCert, byts, cacerts=())

            cdir.genUserCert('coolest', signas='newp')
            path = cdir.getUserCertPath('coolest')
            byts = cdir._getPathBytes(path)
            self.nn(cdir.valUserCert(byts))
            self.nn(cdir.valUserCert(byts, cacerts=(newpca,)))
            self.raises(s_exc.BadCertVerify, cdir.valUserCert, byts, cacerts=(syntestca,))
            self.raises(s_exc.BadCertVerify, cdir.valUserCert, byts, cacerts=())

    def test_certdir_sslctx(self):

        with self.getCertDir() as cdir:

            with self.raises(s_exc.NoSuchCert):
                cdir.getClientSSLContext(certname='newp')

            with s_common.genfile(cdir.certdirs[0], 'users', 'newp.crt') as fd:
                fd.write(b'asdf')

            with self.raises(s_exc.NoCertKey):
                cdir.getClientSSLContext(certname='newp')

            caname = 'syntest'
            hostname = 'visi.vertex.link'
            cdir.genCaCert(caname)
            cdir.genHostCert(hostname, signas=caname)

            ctx = cdir.getServerSSLContext(hostname, caname)
            self.eq(ctx.verify_mode, ssl.VerifyMode.CERT_REQUIRED)

            ctx = cdir.getServerSSLContext(hostname)
            self.eq(ctx.verify_mode, ssl.VerifyMode.CERT_NONE)

            with self.raises(s_exc.NoCertKey):
                cdir.getServerSSLContext('haha.newp.com')

            with self.raises(s_exc.NoSuchCert):
                cdir.getServerSSLContext(hostname, 'newpca')

    async def test_certdir_codesign(self):

        with self.getCertDir() as cdir:
            caname = 'The Vertex Project ROOT CA'
            immname = 'The Vertex Project Intermediate CA 00'
            codename = 'Vertex Build Pipeline'
            codename2 = 'Vertex Build Pipeline Redux'
            codename3 = 'Vertex Build Pipeline Triple Threat'

            cdir.genCaCert(caname)
            _, cacert = cdir.genCaCert(immname, signas=caname)
            cdir.genUserCert('notCodeCert', signas=caname, )

            cdir.genCaCrl(caname)._save()
            cdir.genCaCrl(immname)._save()

            pkey, cert = cdir.genCodeCert(codename, signas=immname)
            self.code_assertions(cdir, cert, pkey, cacert)

            rsak = cdir.getCodeKey(codename)
            cert = cdir.getCodeCert(codename)
            self.isinstance(cert, c_x509.Certificate)

            rsap = rsak.public()

            self.eq(rsak.iden(), rsap.iden())

            sign = rsak.signitem({'foo': 'bar', 'baz': 'faz'})
            self.true(rsap.verifyitem({'baz': 'faz', 'foo': 'bar'}, sign))
            self.false(rsap.verifyitem({'baz': 'faz', 'foo': 'gronk'}, sign))

            fp = cdir.getCodeCertPath(codename)
            with s_common.genfile(fp) as fd:
                byts = fd.read()
            vcrt = cdir.valCodeCert(byts)
            self.isinstance(vcrt, c_x509.Certificate)

            fp = cdir.getUserCertPath('notCodeCert')
            with s_common.genfile(fp) as fd:
                bad_byts = fd.read()
            with self.raises(s_exc.BadCertBytes):
                cdir.valCodeCert(bad_byts)

            crl = cdir.genCaCrl(immname)
            crl.revoke(vcrt)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate revoked', cm.exception.get('mesg'))

            # Ensure we can continue to revoke certs and old certs stay revoked.
            _, codecert2 = cdir.genCodeCert(codename2, signas=immname)
            _, codecert3 = cdir.genCodeCert(codename3, signas=immname)

            crl = cdir.genCaCrl(immname)
            crl.revoke(codecert2)

            fp = cdir.getCodeCertPath(codename2)
            with s_common.genfile(fp) as fd:
                byts2 = fd.read()

            fp = cdir.getCodeCertPath(codename3)
            with s_common.genfile(fp) as fd:
                byts3 = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts2)

            cdir.valCodeCert(byts3)

    async def test_cortex_codesign(self):

        async with self.getTestCore() as core:

            caname = 'Test ROOT CA'
            immname = 'Test Intermediate CA 00'
            codename = 'Test Build Pipeline'

            certpath = s_common.genpath(core.dirn, 'certs')

            core.certdir.genCaCert(caname)
            core.certdir.genCaCert(immname, signas=caname)
            core.certdir.genUserCert('notCodeCert', signas=caname, )

            crl = core.certdir.genCaCrl(caname)
            crl._save()

            crl = core.certdir.genCaCrl(immname)
            crl._save()

            _, codecert = core.certdir.genCodeCert(codename, signas=immname)

            with self.getTestDir() as dirn:

                yamlpath = s_common.genpath(dirn, 'vertex-test.yaml')
                jsonpath = s_common.genpath(dirn, 'vertex-test.json')

                s_common.yamlsave({
                    'name': 'vertex-test',
                    'version': '0.0.1',
                }, yamlpath)

                await s_genpkg.main((
                    '--signas', codename,
                    '--certdir', certpath,
                    '--push', core.getLocalUrl(), '--push-verify',
                    yamlpath))

                await s_genpkg.main((
                    '--signas', codename,
                    '--certdir', certpath,
                    '--save', jsonpath,
                    yamlpath))

                pkgdef = s_common.yamlload(jsonpath)
                pkgorig = s_msgpack.deepcopy(pkgdef)

                opts = {'vars': {'pkgdef': pkgdef}}
                self.none(await core.callStorm('return($lib.pkg.add($pkgdef, verify=$lib.true))', opts=opts))

                with self.raises(s_exc.BadPkgDef) as exc:
                    pkgdef['version'] = '0.0.2'
                    await core.addStormPkg(pkgdef, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package signature does not match!')

                with self.raises(s_exc.BadPkgDef) as exc:
                    opts = {'vars': {'pkgdef': pkgdef}}
                    await core.callStorm('return($lib.pkg.add($pkgdef, verify=$lib.true))', opts=opts)
                self.eq(exc.exception.get('mesg'), 'Storm package signature does not match!')

                with self.raises(s_exc.BadPkgDef) as exc:
                    pkgdef['codesign'].pop('sign', None)
                    await core.addStormPkg(pkgdef, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package has no signature!')

                with self.raises(s_exc.BadPkgDef) as exc:
                    pkgdef['codesign'].pop('cert', None)
                    await core.addStormPkg(pkgdef, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package has no certificate!')

                with self.raises(s_exc.BadPkgDef) as exc:
                    pkgdef.pop('codesign', None)
                    await core.addStormPkg(pkgdef, verify=True)

                self.eq(exc.exception.get('mesg'), 'Storm package is not signed!')

                with self.raises(s_exc.BadPkgDef) as exc:
                    await core.addStormPkg({'codesign': {'cert': 'foo', 'sign': 'bar'}}, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package has malformed certificate!')

                cert = '''-----BEGIN CERTIFICATE-----\nMIIE9jCCAt6'''
                with self.raises(s_exc.BadPkgDef) as exc:
                    await core.addStormPkg({'codesign': {'cert': cert, 'sign': 'bar'}}, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package has malformed certificate!')

                usercertpath = core.certdir.getUserCertPath('notCodeCert')
                with s_common.genfile(usercertpath) as fd:
                    cert = fd.read().decode()
                with self.raises(s_exc.BadCertBytes) as exc:
                    await core.addStormPkg({'codesign': {'cert': cert, 'sign': 'bar'}}, verify=True)
                self.eq(exc.exception.get('mesg'), 'Certificate is not for code signing.')

                # revoke our code signing cert and attempt to load
                crl = core.certdir.genCaCrl(immname)
                crl.revoke(codecert)

                with self.raises(s_exc.BadPkgDef) as exc:
                    await core.addStormPkg(pkgorig, verify=True)
                self.eq(exc.exception.get('mesg'), 'Storm package has invalid certificate: certificate revoked')

    def test_certdir_save_load(self):

        with self.getCertDir() as cdir:
            caname = 'TestCA'
            hostname = 'wee.wow.com'
            username = 'dude@wow.com'
            codename = 'wow pipe'

            pkey, cert = cdir.genCaCert(caname)
            cdir.genHostCert(hostname, signas=caname)
            cdir.genUserCert(username, signas=caname)
            cdir.genCodeCert(codename, signas=caname)

            with self.getTestDir() as dirn:
                cert_path = s_common.genpath(dirn, 'ca.crt')
                cdir.saveCertPem(cert, cert_path)
                with s_common.genfile(cert_path) as fd:
                    cert_copy = fd.read()

                key_path = s_common.genpath(dirn, 'ca.key')
                cdir.savePkeyPem(pkey, key_path)
                with s_common.genfile(key_path) as fd:
                    pkey_copy = fd.read()
                with s_common.genfile(cdir.getCaKeyPath(caname)) as fd:
                    cdir_pkey_bytes = fd.read()

                self.eq(cert_copy, cdir.getCaCertBytes(caname))
                self.eq(pkey_copy, cdir_pkey_bytes)

            ca_path = cdir.getCaCertPath(caname)
            h_path = cdir.getHostCertPath(hostname)
            u_path = cdir.getUserCertPath(username)
            co_path = cdir.getCodeCertPath(codename)

            with self.getCertDir() as cdir2:

                with s_common.genfile(ca_path) as fd:
                    byts = fd.read()
                cdir2.saveCaCertByts(byts)

                with s_common.genfile(h_path) as fd:
                    byts = fd.read()
                cdir2.saveHostCertByts(byts)

                with s_common.genfile(u_path) as fd:
                    byts = fd.read()
                cdir2.saveUserCertByts(byts)

                with s_common.genfile(co_path) as fd:
                    byts = fd.read()
                cdir2.saveCodeCertBytes(byts)

                self.true(cdir2.isCaCert(caname))
                self.true(cdir2.isHostCert(hostname))
                self.true(cdir2.isUserCert(username))
                self.true(cdir2.isCodeCert(codename))

            # older PyOpenSSL code assumed loading a pkey was always a DSA or RSA key.
            pkey = c_ec.generate_private_key(c_ec.SECP384R1())
            byts = pkey.private_bytes(encoding=c_serialization.Encoding.PEM,
                                      format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                                      encryption_algorithm=c_serialization.NoEncryption(), )
            path = cdir._getPathJoin('newp', 'ec.key')
            with s_common.genfile(path) as fd:
                fd.write(byts)
            with self.raises(s_exc.BadCertBytes) as cm:
                cdir._loadKeyPath(path)
            self.isin('Key is ECPrivateKey, expected a DSA or RSA key', cm.exception.get('mesg'))
