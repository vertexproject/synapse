import os
import ssl
import datetime
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils
import synapse.tools.storm.pkg.gen as s_genpkg

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

            # Verify the cert was signed by cacert
            try:
                cacert.public_key().verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    c_padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
            except Exception as e:
                self.fail(f'Certificate signature verification failed: {e}')

            # Verify a different CA cannot verify the cert
            try:
                (_, otherca_cert) = cdir.genCaCert('otherca')
            except s_exc.DupFileName:
                otherca_cert = cdir.getCaCert('otherca')

            with self.raises(c_exc.InvalidSignature):
                otherca_cert.public_key().verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    c_padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )

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

            self.true(cdir.delHostCsr(hostname))
            self.false(os.path.isfile(path))
            self.false(cdir.delHostCsr(hostname))

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

            self.true(cdir.delUserCsr(username))
            self.false(os.path.isfile(path))
            self.false(cdir.delUserCsr(username))

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

            # certdir only accepts DSA or RSA private keys; EC keys are rejected.
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

    def _buildExtCaCert(self, name, critical_bc=True):
        '''Build a raw RSA CA cert with configurable BasicConstraints criticality.'''
        key = c_rsa.generate_private_key(65537, 2048)
        now = datetime.datetime.now(datetime.UTC)
        subject = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name)])
        cert = (c_x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(c_x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=critical_bc)
            .sign(key, c_hashes.SHA256()))
        return key, cert

    def _buildUserCert(self, name, cakey, cacert):
        '''Build a raw RSA user cert with CLIENT_AUTH EKU signed by the given CA.'''
        key = c_rsa.generate_private_key(65537, 2048)
        now = datetime.datetime.now(datetime.UTC)
        cert = (c_x509.CertificateBuilder()
            .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name)]))
            .issuer_name(cacert.subject)
            .public_key(key.public_key())
            .serial_number(c_x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
            .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
            .sign(cakey, c_hashes.SHA256()))
        return key, cert

    def _buildCodeCert(self, name, cakey, cacert):
        '''Build a raw code-signing cert signed by the given CA key.'''
        key = c_rsa.generate_private_key(65537, 2048)
        now = datetime.datetime.now(datetime.UTC)
        cert = (c_x509.CertificateBuilder()
            .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name)]))
            .issuer_name(cacert.subject)
            .public_key(key.public_key())
            .serial_number(c_x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
            .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
            .sign(cakey, c_hashes.SHA256()))
        return key, cert

    async def test_certdir_valUserCert_externalCa(self):
        '''External CA with critical=True BasicConstraints is accepted by AGNOSTIC policy.'''
        with self.getCertDir() as cdir:
            cakey, cacert = self._buildExtCaCert('extca', critical_bc=True)
            _, usercert = self._buildUserCert('extuser', cakey, cacert)

            cabyts = cacert.public_bytes(c_serialization.Encoding.PEM)
            userbyts = usercert.public_bytes(c_serialization.Encoding.PEM)

            cdir.saveCaCertByts(cabyts)
            cdir.saveUserCertByts(userbyts)

            result = cdir.valUserCert(userbyts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_codesign_intermediate_revoked(self):
        '''Revoking the intermediate CA cert via the root CRL causes valCodeCert to fail.'''
        with self.getCertDir() as cdir:
            rootname = 'revoke-test-root'
            immname = 'revoke-test-imm'
            codename = 'revoke-test-code'

            cdir.genCaCert(rootname)
            _, immcert = cdir.genCaCert(immname, signas=rootname)
            _, codecert = cdir.genCodeCert(codename, signas=immname)

            fp = cdir.getCodeCertPath(codename)
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            # cert should validate before revocation
            self.nn(cdir.valCodeCert(byts))

            # revoke the intermediate CA via the root CRL
            rootcrl = cdir.genCaCrl(rootname)
            rootcrl.revoke(immcert)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate revoked', cm.exception.get('mesg'))

    async def test_certdir_codesign_deep_chain(self):
        '''A 3-level chain (root -> imm1 -> imm2 -> code cert) validates successfully.'''
        with self.getCertDir() as cdir:
            root = 'deep-root'
            imm1 = 'deep-imm1'
            imm2 = 'deep-imm2'
            codename = 'deep-code'

            cdir.genCaCert(root)
            cdir.genCaCert(imm1, signas=root)
            cdir.genCaCert(imm2, signas=imm1)
            cdir.genCodeCert(codename, signas=imm2)

            fp = cdir.getCodeCertPath(codename)
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_codesign_ec_ca_rejected(self):
        '''A code cert whose issuer CA uses an EC key cannot be verified and raises BadCertVerify.'''
        with self.getCertDir() as cdir:
            eckey = c_ec.generate_private_key(c_ec.SECP256R1())
            now = datetime.datetime.now(datetime.UTC)
            caname = 'ec-ca'
            casubject = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, caname)])
            eccacert = (c_x509.CertificateBuilder()
                .subject_name(casubject)
                .issuer_name(casubject)
                .public_key(eckey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(eckey, c_hashes.SHA256()))

            _, codecert = self._buildCodeCert('ec-signed-code', eckey, eccacert)

            cdir.saveCaCertByts(eccacert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('ec-signed-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_valUserCert_intermediate_chain(self):
        '''PolicyBuilder requires intermediates in the Store; chain-building from untrusted intermediates fails.'''
        with self.getCertDir() as cdir:
            rootname = 'polybuild-root'
            immname = 'polybuild-imm'

            cdir.genCaCert(rootname)
            cdir.genCaCert(immname, signas=rootname)
            _, usercert = cdir.genUserCert('polybuild-user', signas=immname)

            userbyts = usercert.public_bytes(c_serialization.Encoding.PEM)
            rootcert = cdir.getCaCert(rootname)
            immcert = cdir.getCaCert(immname)

            # root alone in cacerts: fails because imm is not a trusted anchor
            with self.raises(s_exc.BadCertVerify):
                cdir.valUserCert(userbyts, cacerts=[rootcert])

            # imm alone in cacerts: succeeds because imm is trusted directly
            self.nn(cdir.valUserCert(userbyts, cacerts=[immcert]))

            # both in cacerts: also succeeds
            self.nn(cdir.valUserCert(userbyts, cacerts=[rootcert, immcert]))

    async def test_certdir_crl_revoke_wrong_ca(self):
        '''Attempting to revoke a cert via the wrong CA raises BadCertVerify.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('wrong-ca1')
            cdir.genCaCert('wrong-ca2')
            _, codecert = cdir.genCodeCert('wrong-ca-code', signas='wrong-ca1')

            crl = cdir.genCaCrl('wrong-ca2')
            with self.raises(s_exc.BadCertVerify) as cm:
                crl.revoke(codecert)
            self.isin('wrong-ca2', cm.exception.get('mesg'))

    async def test_certdir_codesign_no_cacerts(self):
        '''valCodeCert with no CA certs in certdir raises BadCertVerify.'''
        with self.getCertDir() as cdir:
            # generate code cert in a separate certdir so the empty cdir has no CAs
            with self.getCertDir() as srcdir:
                srcdir.genCaCert('src-ca')
                _, codecert = srcdir.genCodeCert('no-ca-code', signas='src-ca')

            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_verifyChain_cert_not_yet_valid(self):
        '''_verifyChain raises BadCertVerify when the cert is not yet valid (not_valid_before in the future).'''
        with self.getCertDir() as cdir:
            caname = 'future-cert-ca'
            cdir.genCaCert(caname)
            cakey = cdir.getCaKey(caname)
            cacert = cdir.getCaCert(caname)

            future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)
            future_end = future + datetime.timedelta(days=365)

            cert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'future-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(future)
                .not_valid_after(future_end)
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(cakey, c_hashes.SHA256()))

            byts = cert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate has expired', cm.exception.get('mesg'))

    async def test_certdir_verifyChain_cert_expired(self):
        '''_verifyChain raises BadCertVerify when the cert validity period is entirely in the past.'''
        with self.getCertDir() as cdir:
            caname = 'expired-cert-ca'
            cdir.genCaCert(caname)
            cakey = cdir.getCaKey(caname)
            cacert = cdir.getCaCert(caname)

            past_start = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            past_end = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)

            cert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'expired-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(past_start)
                .not_valid_after(past_end)
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(cakey, c_hashes.SHA256()))

            byts = cert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate has expired', cm.exception.get('mesg'))

    async def test_certdir_crl_verify_signature_error(self):
        '''Crl._verify wraps non-BadCertVerify exceptions from _verifyCertSignature as BadCertVerify.'''
        with self.getCertDir() as cdir:
            caname = 'bad-sig-ca'
            cdir.genCaCert(caname)
            cacert = cdir.getCaCert(caname)

            # Build a cert whose issuer name matches the CA but signed with a different key.
            # _verify passes the issuer check but _verifyCertSignature raises InvalidSignature,
            # which is caught by the bare except and re-raised as BadCertVerify.
            wrongkey = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            badcert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'bad-sig-cert')]))
                .issuer_name(cacert.subject)
                .public_key(wrongkey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(wrongkey, c_hashes.SHA256()))

            crl = cdir.genCaCrl(caname)
            with self.raises(s_exc.BadCertVerify) as cm:
                crl.revoke(badcert)
            self.isin(caname, cm.exception.get('mesg'))

    # -------------------------------------------------------------------
    # Adversarial scenarios
    # -------------------------------------------------------------------

    def _makeCaCert(self, cn, issuer_cn, signing_key, subject_key, path_length=None, critical_bc=True):
        '''Build a raw CA cert (not self-signed if issuer_cn != cn).'''
        now = datetime.datetime.now(datetime.UTC)
        subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, cn)])
        issuer = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, issuer_cn)])
        return (c_x509.CertificateBuilder()
            .subject_name(subj)
            .issuer_name(issuer)
            .public_key(subject_key.public_key())
            .serial_number(c_x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(c_x509.BasicConstraints(ca=True, path_length=path_length), critical=critical_bc)
            .sign(signing_key, c_hashes.SHA256()))

    async def test_certdir_adversarial_chain_cycle(self):
        '''A mutually-signed chain (A signed by B, B signed by A) causes RecursionError.

        _verifyChain has no cycle detection; this is a known limitation.
        '''
        with self.getCertDir() as cdir:
            key_a = c_rsa.generate_private_key(65537, 2048)
            key_b = c_rsa.generate_private_key(65537, 2048)

            # cert_a: subject=cycle-a, issuer=cycle-b, signed by key_b
            cert_a = self._makeCaCert('adv-cycle-a', 'adv-cycle-b', key_b, key_a)
            # cert_b: subject=cycle-b, issuer=cycle-a, signed by key_a
            cert_b = self._makeCaCert('adv-cycle-b', 'adv-cycle-a', key_a, key_b)

            # code cert issued by cycle-a, signed with key_a
            now = datetime.datetime.now(datetime.UTC)
            codecert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-cycle-code')]))
                .issuer_name(cert_a.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(key_a, c_hashes.SHA256()))

            cdir.saveCaCertByts(cert_a.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(cert_b.public_bytes(c_serialization.Encoding.PEM))

            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('cycle detected', cm.exception.get('mesg'))

    async def test_certdir_adversarial_rogue_ca_injection(self):
        '''An injected rogue CA cert (same CN, different key) exposes two distinct behaviors.

        1. Signature matching is robust: a cert signed by the LEGITIMATE CA still validates
           even when a rogue CA with the same CN is present, because _verifyChain matches on
           signature not just CN.
        2. The rogue CA is itself trusted: a cert signed with the ROGUE key also validates,
           because _verifyChain trusts every cert in cas/.  Write access to cas/ is therefore
           equivalent to root-CA-level trust.
        '''
        with self.getCertDir() as cdir:
            caname = 'adv-rogue-legit'
            cdir.genCaCert(caname)
            _, legitcert = cdir.genCodeCert('adv-rogue-code', signas=caname)

            # Inject a rogue CA with same CN but a different key into the cas/ directory
            roguekey = c_rsa.generate_private_key(65537, 2048)
            roguecert = self._makeCaCert(caname, caname, roguekey, roguekey)
            caspath = os.path.join(cdir.certdirs[0], 'cas')
            with open(os.path.join(caspath, f'{caname}-rogue.crt'), 'wb') as fd:
                fd.write(roguecert.public_bytes(c_serialization.Encoding.PEM))

            # The legitimate cert is still valid: _verifyChain finds the correct CA by signature
            legitbyts = legitcert.public_bytes(c_serialization.Encoding.PEM)
            self.nn(cdir.valCodeCert(legitbyts))

            # A cert forged with the rogue key ALSO validates because the rogue CA is trusted
            _, forgedcert = self._buildCodeCert('adv-rogue-forged', roguekey, roguecert)
            forgedbyts = forgedcert.public_bytes(c_serialization.Encoding.PEM)
            result = cdir.valCodeCert(forgedbyts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_pathlength_bypass(self):
        '''_verifyChain enforces BasicConstraints path_length constraints.

        path_length=0 on a root CA forbids any intermediate CA.  Using one to sign
        a code cert is rejected.  Directly signing the code cert with the same root
        (no intermediate) must still succeed.
        '''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            immkey = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-pl0-root', 'adv-pl0-root', rootkey, rootkey, path_length=0)
            immcert = self._makeCaCert('adv-pl0-imm', 'adv-pl0-root', rootkey, immkey)

            cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(immcert.public_bytes(c_serialization.Encoding.PEM))

            # root → intermediate → code cert: violates path_length=0
            _, codecert_via_imm = self._buildCodeCert('adv-pl0-code-via-imm', immkey, immcert)
            byts_via_imm = codecert_via_imm.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts_via_imm)
            self.isin('path length constraint', cm.exception.get('mesg'))

            # root → code cert directly: valid with path_length=0 (no intermediates)
            _, codecert_direct = self._buildCodeCert('adv-pl0-code-direct', rootkey, rootcert)
            byts_direct = codecert_direct.public_bytes(c_serialization.Encoding.PEM)
            result = cdir.valCodeCert(byts_direct)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_expired_intermediate_detected(self):
        '''A valid code cert whose intermediate CA has expired is rejected by the recursive chain check.'''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            immkey = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-expimm-root', 'adv-expimm-root', rootkey, rootkey)

            # expired intermediate: validity entirely in the past
            past_start = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            past_end = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.UTC)
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-expimm-imm')])
            rootsubj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-expimm-root')])
            expiredimm = (c_x509.CertificateBuilder()
                .subject_name(subj)
                .issuer_name(rootsubj)
                .public_key(immkey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(past_start)
                .not_valid_after(past_end)
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(rootkey, c_hashes.SHA256()))

            cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(expiredimm.public_bytes(c_serialization.Encoding.PEM))

            # code cert itself is valid
            _, codecert = self._buildCodeCert('adv-expimm-code', immkey, expiredimm)
            byts = codecert.public_bytes(c_serialization.Encoding.PEM)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate has expired', cm.exception.get('mesg'))

    async def test_certdir_adversarial_crl_issuer_mismatch(self):
        '''A CRL issued by CA_B containing CA_A serial numbers does not revoke CA_A certs.

        _verifyChain skips CRLs whose issuer does not match the cert's issuer.
        '''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-crl-ca-a')
            cdir.genCaCert('adv-crl-ca-b')
            _, codecert = cdir.genCodeCert('adv-crl-code', signas='adv-crl-ca-a')

            # Revoke the code cert's serial via CA_B's CRL (wrong issuer)
            crl_b = cdir.genCaCrl('adv-crl-ca-b')
            # craft a fake revocation entry for the code cert's serial
            now = datetime.datetime.now(datetime.UTC)
            revoked = (c_x509.RevokedCertificateBuilder()
                .serial_number(codecert.serial_number)
                .revocation_date(now)
                .build())
            crl_b.crlbuilder = crl_b.crlbuilder.add_revoked_certificate(revoked)
            crl_b._save(now)

            # cert should still validate: the CRL issuer is ca-b, not the cert's issuer ca-a
            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_missing_eku(self):
        '''valCodeCert and valUserCert raise ExtensionNotFound for a cert with no EKU extension.

        Neither method guards against a missing EKU extension before calling
        get_extension_for_oid(); the exception propagates uncaught.
        '''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-noeku-ca')
            cakey = cdir.getCaKey('adv-noeku-ca')
            cacert = cdir.getCaCert('adv-noeku-ca')

            now = datetime.datetime.now(datetime.UTC)
            noeku = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-noeku-cert')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(cakey, c_hashes.SHA256()))

            byts = noeku.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.valCodeCert(byts)
            self.isin('not for code signing', cm.exception.get('mesg'))
            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.valUserCert(byts)
            self.isin('not for client auth', cm.exception.get('mesg'))

    async def test_certdir_adversarial_eku_cross_validation(self):
        '''Code certs are rejected by valUserCert; user certs are rejected by valCodeCert.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-eku-ca')
            _, codecert = cdir.genCodeCert('adv-eku-code', signas='adv-eku-ca')
            _, usercert = cdir.genUserCert('adv-eku-user', signas='adv-eku-ca')

            codebyts = codecert.public_bytes(c_serialization.Encoding.PEM)
            userbyts = usercert.public_bytes(c_serialization.Encoding.PEM)

            # code cert passed to valUserCert: EKU check rejects it before any chain verification
            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.valUserCert(codebyts)
            self.isin('not for client auth', cm.exception.get('mesg'))

            # user cert passed to valCodeCert: EKU check rejects it before any chain verification
            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.valCodeCert(userbyts)
            self.isin('not for code signing', cm.exception.get('mesg'))

    async def test_certdir_adversarial_non_ca_cert_as_anchor(self):
        '''_verifyChain rejects a self-signed cert with ca=False as a trust anchor.

        The issuer must have BasicConstraints ca=True; a self-signed cert with ca=False
        is rejected with BadCertVerify even if its signature is cryptographically valid.
        '''
        with self.getCertDir() as cdir:
            key = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-non-ca-anchor')])

            # self-signed cert with ca=False
            noncacert = (c_x509.CertificateBuilder()
                .subject_name(subj)
                .issuer_name(subj)
                .public_key(key.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(key, c_hashes.SHA256()))

            cdir.saveCaCertByts(noncacert.public_bytes(c_serialization.Encoding.PEM))

            _, codecert = self._buildCodeCert('adv-non-ca-code', key, noncacert)
            byts = codecert.public_bytes(c_serialization.Encoding.PEM)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('not a CA certificate', cm.exception.get('mesg'))
