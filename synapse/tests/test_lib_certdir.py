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

            # Verify the cert's signature against the CA's public key
            capubkey = cacert.public_key()
            self.none(capubkey.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                c_padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            ))

            # Generate a separate CA that did not sign the certificate
            try:
                (_, otherca_cert) = cdir.genCaCert('otherca')
            except s_exc.DupFileName:
                otherca_cert = cdir.getCaCert('otherca')

            # A different CA should NOT be able to verify the certificate
            otherpubkey = otherca_cert.public_key()
            with self.raises(c_exc.InvalidSignature):
                otherpubkey.verify(
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

            # Backwards compatibility with sans specifiers from easycert
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

            # Loading a pkey is expected to be a DSA or RSA key.
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

    # -------------------------------------------------------------------
    # Test helpers for adversarial / edge-case tests
    # -------------------------------------------------------------------

    def _makeCaCert(self, cn, issuer_cn, signing_key, subject_key, path_length=None, critical_bc=True):
        '''Build a raw CA cert with configurable BasicConstraints.'''
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

    # -------------------------------------------------------------------
    # Adversarial scenarios
    # -------------------------------------------------------------------

    async def test_certdir_adversarial_chain_cycle(self):
        '''Two CAs that sign each other are detected as a cycle.'''
        with self.getCertDir() as cdir:
            key_a = c_rsa.generate_private_key(65537, 2048)
            key_b = c_rsa.generate_private_key(65537, 2048)

            cert_a = self._makeCaCert('adv-cycle-a', 'adv-cycle-b', key_b, key_a)
            cert_b = self._makeCaCert('adv-cycle-b', 'adv-cycle-a', key_a, key_b)

            cdir.saveCaCertByts(cert_a.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(cert_b.public_bytes(c_serialization.Encoding.PEM))

            _, codecert = self._buildCodeCert('adv-cycle-code', key_a, cert_a)
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-cycle-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('cycle detected', cm.exception.get('mesg'))

    async def test_certdir_adversarial_rogue_ca_injection(self):
        '''Rogue CA with same CN but different key. Signature-based matching handles both.'''
        with self.getCertDir() as cdir:
            caname = 'adv-rogue-legit'
            cdir.genCaCert(caname)
            _, legitcert = cdir.genCodeCert('adv-rogue-code', signas=caname)

            roguekey = c_rsa.generate_private_key(65537, 2048)
            roguecert = self._makeCaCert(caname, caname, roguekey, roguekey)
            caspath = os.path.join(cdir.certdirs[0], 'cas')
            with open(os.path.join(caspath, f'{caname}-rogue.crt'), 'wb') as fd:
                fd.write(roguecert.public_bytes(c_serialization.Encoding.PEM))

            # Legitimate cert still validates via signature match
            legitbyts = legitcert.public_bytes(c_serialization.Encoding.PEM)
            self.nn(cdir.valCodeCert(legitbyts))

            # Rogue-signed cert also validates (write access to cas/ = trust)
            _, forgedcert = self._buildCodeCert('adv-rogue-forged', roguekey, roguecert)
            cdir.saveCodeCertBytes(forgedcert.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-rogue-forged')
            with s_common.genfile(fp) as fd:
                forgedbyts = fd.read()
            result = cdir.valCodeCert(forgedbyts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_pathlength_bypass(self):
        '''path_length=0 on root CA forbids intermediates.'''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            immkey = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-pl0-root', 'adv-pl0-root', rootkey, rootkey, path_length=0)
            immcert = self._makeCaCert('adv-pl0-imm', 'adv-pl0-root', rootkey, immkey)

            cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(immcert.public_bytes(c_serialization.Encoding.PEM))

            # root -> intermediate -> code cert: violates path_length=0
            _, codecert_via_imm = self._buildCodeCert('adv-pl0-code-via-imm', immkey, immcert)
            cdir.saveCodeCertBytes(codecert_via_imm.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-pl0-code-via-imm')
            with s_common.genfile(fp) as fd:
                byts_via_imm = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts_via_imm)
            self.isin('path length constraint', cm.exception.get('mesg'))

            # root -> code cert directly: valid with path_length=0
            _, codecert_direct = self._buildCodeCert('adv-pl0-code-direct', rootkey, rootcert)
            cdir.saveCodeCertBytes(codecert_direct.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-pl0-code-direct')
            with s_common.genfile(fp) as fd:
                byts_direct = fd.read()
            result = cdir.valCodeCert(byts_direct)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_pathlength_depth_exceeded(self):
        '''path_length=1 on root allows 1 intermediate but not 2.'''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            imm1key = c_rsa.generate_private_key(65537, 2048)
            imm2key = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-pl1-root', 'adv-pl1-root', rootkey, rootkey, path_length=1)
            imm1cert = self._makeCaCert('adv-pl1-imm1', 'adv-pl1-root', rootkey, imm1key)
            imm2cert = self._makeCaCert('adv-pl1-imm2', 'adv-pl1-imm1', imm1key, imm2key)

            cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(imm1cert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(imm2cert.public_bytes(c_serialization.Encoding.PEM))

            # root -> imm1 -> imm2 -> code: violates path_length=1
            _, codecert_deep = self._buildCodeCert('adv-pl1-code-deep', imm2key, imm2cert)
            cdir.saveCodeCertBytes(codecert_deep.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-pl1-code-deep')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('path length constraint', cm.exception.get('mesg'))

            # root -> imm1 -> code: valid with path_length=1
            _, codecert_ok = self._buildCodeCert('adv-pl1-code-ok', imm1key, imm1cert)
            cdir.saveCodeCertBytes(codecert_ok.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-pl1-code-ok')
            with s_common.genfile(fp) as fd:
                byts = fd.read()
            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_pathlength_intermediate_constraint(self):
        '''path_length=0 on an intermediate CA forbids sub-intermediates.'''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            immkey = c_rsa.generate_private_key(65537, 2048)
            subimmkey = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-plimm-root', 'adv-plimm-root', rootkey, rootkey)
            immcert = self._makeCaCert('adv-plimm-imm', 'adv-plimm-root', rootkey, immkey, path_length=0)
            subimmcert = self._makeCaCert('adv-plimm-subimm', 'adv-plimm-imm', immkey, subimmkey)

            cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(immcert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCaCertByts(subimmcert.public_bytes(c_serialization.Encoding.PEM))

            # root -> imm(pl=0) -> subimm -> code: violates intermediate constraint
            _, codecert = self._buildCodeCert('adv-plimm-code', subimmkey, subimmcert)
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-plimm-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('path length constraint', cm.exception.get('mesg'))

            # root -> imm(pl=0) -> code directly: valid
            _, codecert_ok = self._buildCodeCert('adv-plimm-code-direct', immkey, immcert)
            cdir.saveCodeCertBytes(codecert_ok.public_bytes(c_serialization.Encoding.PEM))
            fp = cdir.getCodeCertPath('adv-plimm-code-direct')
            with s_common.genfile(fp) as fd:
                byts = fd.read()
            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_adversarial_expired_intermediate_detected(self):
        '''Expired intermediate CA is rejected by the recursive chain check.'''
        with self.getCertDir() as cdir:
            rootkey = c_rsa.generate_private_key(65537, 2048)
            immkey = c_rsa.generate_private_key(65537, 2048)

            rootcert = self._makeCaCert('adv-expimm-root', 'adv-expimm-root', rootkey, rootkey)

            past_start = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            past_end = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
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

            _, codecert = self._buildCodeCert('adv-expimm-code', immkey, expiredimm)
            byts = codecert.public_bytes(c_serialization.Encoding.PEM)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('issuer certificate has expired', cm.exception.get('mesg'))

    async def test_certdir_adversarial_missing_eku(self):
        '''Cert with no EKU extension raises BadCertBytes.'''
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

    async def test_certdir_adversarial_eku_cross_validation(self):
        '''User cert (CLIENT_AUTH) is rejected by valCodeCert EKU check.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-eku-ca')
            _, usercert = cdir.genUserCert('adv-eku-user', signas='adv-eku-ca')

            userbyts = usercert.public_bytes(c_serialization.Encoding.PEM)

            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.valCodeCert(userbyts)
            self.isin('not for code signing', cm.exception.get('mesg'))

    async def test_certdir_adversarial_non_ca_cert_as_anchor(self):
        '''Self-signed cert with ca=False used as trust anchor is rejected.'''
        with self.getCertDir() as cdir:
            key = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-non-ca-anchor')])
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
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-non-ca-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('not a CA certificate', cm.exception.get('mesg'))

    async def test_certdir_adversarial_forged_issuer_name(self):
        '''Cert with correct issuer name but signed by a different key is rejected.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-forgery-ca')
            cacert = cdir.getCaCert('adv-forgery-ca')

            wrongkey = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            forgedcert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-forged-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(wrongkey, c_hashes.SHA256()))

            byts = forgedcert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_adversarial_self_signed_code_cert(self):
        '''Self-signed code cert is not in the CA store and fails verification.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-ss-ca')
            cdir.genCodeCert('adv-ss-code')  # self-signed, no signas

            fp = cdir.getCodeCertPath('adv-ss-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_codesign_ec_ca_rejected(self):
        '''EC key CA is rejected by _verifyCertSignature (RSA-only policy).'''
        with self.getCertDir() as cdir:
            eckey = c_ec.generate_private_key(c_ec.SECP256R1())
            now = datetime.datetime.now(datetime.UTC)
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-ec-ca')])
            eccacert = (c_x509.CertificateBuilder()
                .subject_name(subj)
                .issuer_name(subj)
                .public_key(eckey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(eckey, c_hashes.SHA256()))

            _, codecert = self._buildCodeCert('adv-ec-code', eckey, eccacert)
            cdir.saveCaCertByts(eccacert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-ec-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_codesign_deep_chain(self):
        '''A deep chain (root -> imm1 -> imm2 -> imm3 -> code cert) validates with no path constraints.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-deep-root')
            cdir.genCaCert('adv-deep-imm1', signas='adv-deep-root')
            cdir.genCaCert('adv-deep-imm2', signas='adv-deep-imm1')
            cdir.genCaCert('adv-deep-imm3', signas='adv-deep-imm2')
            cdir.genCodeCert('adv-deep-code', signas='adv-deep-imm3')

            fp = cdir.getCodeCertPath('adv-deep-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_codesign_intermediate_revoked(self):
        '''Revoking an intermediate CA via root CRL causes valCodeCert to fail.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-revimm-root')
            _, immcert = cdir.genCaCert('adv-revimm-imm', signas='adv-revimm-root')
            cdir.genCodeCert('adv-revimm-code', signas='adv-revimm-imm')

            cdir.genCaCrl('adv-revimm-imm')._save()

            fp = cdir.getCodeCertPath('adv-revimm-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            # cert validates before revocation
            self.nn(cdir.valCodeCert(byts))

            # revoke the intermediate via root CRL
            rootcrl = cdir.genCaCrl('adv-revimm-root')
            rootcrl.revoke(immcert)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate revoked', cm.exception.get('mesg'))

    async def test_certdir_crl_verify_signature_error(self):
        '''Crl._verify rejects a cert with matching issuer name but wrong signature.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-badsig-ca')
            cacert = cdir.getCaCert('adv-badsig-ca')

            wrongkey = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            badcert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-badsig-cert')]))
                .issuer_name(cacert.subject)
                .public_key(wrongkey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(wrongkey, c_hashes.SHA256()))

            crl = cdir.genCaCrl('adv-badsig-ca')
            with self.raises(s_exc.BadCertVerify) as cm:
                crl.revoke(badcert)
            self.isin('adv-badsig-ca', cm.exception.get('mesg'))

    async def test_certdir_verifyChain_cert_validity(self):
        '''_verifyChain checks both not-yet-valid and expired certs with distinct messages.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-validity-ca')
            cakey = cdir.getCaKey('adv-validity-ca')
            cacert = cdir.getCaCert('adv-validity-ca')

            # Not-yet-valid cert
            future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)
            future_end = future + datetime.timedelta(days=365)
            futurecert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-future-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(future)
                .not_valid_after(future_end)
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(cakey, c_hashes.SHA256()))

            byts = futurecert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate is not yet valid', cm.exception.get('mesg'))

            # Expired cert
            past_start = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            past_end = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
            expiredcert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-expired-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(past_start)
                .not_valid_after(past_end)
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(cakey, c_hashes.SHA256()))

            byts = expiredcert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('certificate has expired', cm.exception.get('mesg'))

    async def test_certdir_adversarial_crl_issuer_mismatch(self):
        '''CRL from CA_B does not revoke certs signed by CA_A.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-crl-ca-a')
            cdir.genCaCert('adv-crl-ca-b')
            _, codecert = cdir.genCodeCert('adv-crl-code', signas='adv-crl-ca-a')

            cdir.genCaCrl('adv-crl-ca-a')._save()
            crl_b = cdir.genCaCrl('adv-crl-ca-b')

            now = datetime.datetime.now(datetime.UTC)
            revoked = (c_x509.RevokedCertificateBuilder()
                .serial_number(codecert.serial_number)
                .revocation_date(now)
                .build())
            crl_b.crlbuilder = crl_b.crlbuilder.add_revoked_certificate(revoked)
            crl_b._save(now)

            # cert should still validate: the CRL issuer is ca-b, not ca-a
            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            result = cdir.valCodeCert(byts)
            self.isinstance(result, c_x509.Certificate)

    async def test_certdir_codesign_no_cacerts(self):
        '''Code cert from external certdir where the CA is not present fails.'''
        with self.getCertDir() as cdir:
            with self.getCertDir() as srcdir:
                srcdir.genCaCert('adv-src-ca')
                _, codecert = srcdir.genCodeCert('adv-no-ca-code', signas='adv-src-ca')

            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))

    async def test_certdir_external_ca_critical_bc(self):
        '''External CA certs with critical=True and critical=False BasicConstraints both work.'''
        with self.getCertDir() as cdir:
            # critical=True
            cakey_crit = c_rsa.generate_private_key(65537, 2048)
            cacert_crit = self._makeCaCert('adv-ext-crit-ca', 'adv-ext-crit-ca', cakey_crit, cakey_crit, critical_bc=True)
            _, codecert_crit = self._buildCodeCert('adv-ext-crit-code', cakey_crit, cacert_crit)

            cdir.saveCaCertByts(cacert_crit.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCodeCertBytes(codecert_crit.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-ext-crit-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()
            self.isinstance(cdir.valCodeCert(byts), c_x509.Certificate)

            # critical=False
            cakey_nc = c_rsa.generate_private_key(65537, 2048)
            cacert_nc = self._makeCaCert('adv-ext-nc-ca', 'adv-ext-nc-ca', cakey_nc, cakey_nc, critical_bc=False)
            _, codecert_nc = self._buildCodeCert('adv-ext-nc-code', cakey_nc, cacert_nc)

            cdir.saveCaCertByts(cacert_nc.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCodeCertBytes(codecert_nc.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-ext-nc-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()
            self.isinstance(cdir.valCodeCert(byts), c_x509.Certificate)

    async def test_certdir_external_ca_missing_bc(self):
        '''External CA cert with NO BasicConstraints extension is rejected.'''
        with self.getCertDir() as cdir:
            cakey = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-nobc-ca')])
            cacert = (c_x509.CertificateBuilder()
                .subject_name(subj)
                .issuer_name(subj)
                .public_key(cakey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .sign(cakey, c_hashes.SHA256()))

            _, codecert = self._buildCodeCert('adv-nobc-code', cakey, cacert)
            cdir.saveCaCertByts(cacert.public_bytes(c_serialization.Encoding.PEM))
            cdir.saveCodeCertBytes(codecert.public_bytes(c_serialization.Encoding.PEM))

            fp = cdir.getCodeCertPath('adv-nobc-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('BasicConstraints', cm.exception.get('mesg'))

    async def test_certdir_crl_two_chains_one_with_crls(self):
        '''Two independent CA chains. Only one has CRLs. Both must validate.'''
        with self.getCertDir() as cdir:
            # Chain A with CRLs
            cdir.genCaCert('ChainA Root CA')
            cdir.genCaCert('ChainA Intermediate CA', signas='ChainA Root CA')
            cdir.genCodeCert('ChainA Code Signer', signas='ChainA Intermediate CA')
            cdir.genCaCrl('ChainA Root CA')._save()
            cdir.genCaCrl('ChainA Intermediate CA')._save()

            fp = cdir.getCodeCertPath('ChainA Code Signer')
            with s_common.genfile(fp) as fd:
                bytsA = fd.read()
            self.nn(cdir.valCodeCert(bytsA))

            # Chain B without CRLs
            cdir.genCaCert('ChainB Root CA')
            cdir.genCaCert('ChainB Intermediate CA', signas='ChainB Root CA')
            _, codecertB = cdir.genCodeCert('ChainB Code Signer', signas='ChainB Intermediate CA')

            fp = cdir.getCodeCertPath('ChainB Code Signer')
            with s_common.genfile(fp) as fd:
                bytsB = fd.read()

            # Chain B must validate despite Chain A's CRLs being present
            self.nn(cdir.valCodeCert(bytsB))

            # Chain A's revocation still works
            crl = cdir.genCaCrl('ChainA Intermediate CA')
            chainA_codecert = cdir.getCodeCert('ChainA Code Signer')
            crl.revoke(chainA_codecert)

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(bytsA)
            self.isin('certificate revoked', cm.exception.get('mesg'))

    async def test_certdir_adversarial_max_chain_depth(self):
        '''A chain exceeding the maximum depth of 8 is rejected.'''
        with self.getCertDir() as cdir:
            # Build a chain with 9 CAs (root + 8 intermediates) to exceed the default max depth of 8
            prev_name = 'adv-maxdepth-root'
            cdir.genCaCert(prev_name)
            for i in range(8):
                name = f'adv-maxdepth-imm{i}'
                cdir.genCaCert(name, signas=prev_name)
                prev_name = name

            cdir.genCodeCert('adv-maxdepth-code', signas=prev_name)

            fp = cdir.getCodeCertPath('adv-maxdepth-code')
            with s_common.genfile(fp) as fd:
                byts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('maximum depth', cm.exception.get('mesg'))

    async def test_certdir_crl_revoke_wrong_ca(self):
        '''Crl._verify rejects a cert whose issuer name does not match the CRL CA.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('crl-wrong-ca1')
            cdir.genCaCert('crl-wrong-ca2')
            _, codecert = cdir.genCodeCert('crl-wrong-code', signas='crl-wrong-ca1')

            # Attempt to revoke a cert signed by ca1 via ca2's CRL
            crl = cdir.genCaCrl('crl-wrong-ca2')
            with self.raises(s_exc.BadCertVerify) as cm:
                crl.revoke(codecert)
            self.isin('crl-wrong-ca2', cm.exception.get('mesg'))

    async def test_certdir_crl_revoke_unsupported_key(self):
        '''Crl._verify re-raises BadCertVerify from _verifyCertSignature for unsupported key types.'''
        with self.getCertDir() as cdir:
            # Create an EC CA and save it where certdir can find it
            eckey = c_ec.generate_private_key(c_ec.SECP256R1())
            now = datetime.datetime.now(datetime.UTC)
            caname = 'crl-eckey-ca'
            subj = c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, caname)])
            eccacert = (c_x509.CertificateBuilder()
                .subject_name(subj)
                .issuer_name(subj)
                .public_key(eckey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(eckey, c_hashes.SHA256()))

            cdir.saveCaCertByts(eccacert.public_bytes(c_serialization.Encoding.PEM))

            # Save the EC private key so genCaCrl can load it
            eckey_pem = eckey.private_bytes(
                encoding=c_serialization.Encoding.PEM,
                format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=c_serialization.NoEncryption(),
            )
            keypath = os.path.join(cdir.certdirs[0], 'cas', f'{caname}.key')
            with open(keypath, 'wb') as fd:
                fd.write(eckey_pem)

            # Build a cert that is genuinely signed by the EC CA
            certkey = c_rsa.generate_private_key(65537, 2048)
            cert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'crl-eckey-cert')]))
                .issuer_name(eccacert.subject)
                .public_key(certkey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(eckey, c_hashes.SHA256()))

            # _verify will fail because _verifyCertSignature rejects EC keys
            crl = cdir.genCaCrl(caname)
            with self.raises(s_exc.BadCertVerify) as cm:
                crl.revoke(cert)
            self.isin(caname, cm.exception.get('mesg'))

    async def test_certdir_verifyChain_cert_missing_bc(self):
        '''_verifyChain rejects a cert that lacks BasicConstraints extension.'''
        with self.getCertDir() as cdir:
            cdir.genCaCert('nobc-leaf-root')
            cakey = cdir.getCaKey('nobc-leaf-root')
            cacert = cdir.getCaCert('nobc-leaf-root')

            # Build a code cert WITHOUT BasicConstraints
            now = datetime.datetime.now(datetime.UTC)
            codecert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'nobc-leaf-code')]))
                .issuer_name(cacert.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                # No BasicConstraints extension
                .sign(cakey, c_hashes.SHA256()))

            byts = codecert.public_bytes(c_serialization.Encoding.PEM)
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('missing BasicConstraints', cm.exception.get('mesg'))

    async def test_certdir_adversarial_root_ca_validity(self):
        '''Self-signed root CA validity dates are checked.'''
        with self.getCertDir() as cdir:
            now = datetime.datetime.now(datetime.UTC)

            def _makeRootAndCode(rootname, codename, rootkey, not_valid_before, not_valid_after):
                rootcert = (c_x509.CertificateBuilder()
                    .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, rootname)]))
                    .issuer_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, rootname)]))
                    .public_key(rootkey.public_key())
                    .serial_number(c_x509.random_serial_number())
                    .not_valid_before(not_valid_before)
                    .not_valid_after(not_valid_after)
                    .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .sign(rootkey, c_hashes.SHA256()))

                cdir.saveCaCertByts(rootcert.public_bytes(c_serialization.Encoding.PEM))

                codecert = (c_x509.CertificateBuilder()
                    .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, codename)]))
                    .issuer_name(rootcert.subject)
                    .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                    .serial_number(c_x509.random_serial_number())
                    .not_valid_before(now)
                    .not_valid_after(now + datetime.timedelta(days=3650))
                    .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                    .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                    .sign(rootkey, c_hashes.SHA256()))

                return codecert.public_bytes(c_serialization.Encoding.PEM)

            # Expired root CA — direct code cert
            expkey = c_rsa.generate_private_key(65537, 2048)
            byts = _makeRootAndCode('adv-exproot', 'adv-exproot-code', expkey,
                                    datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
                                    datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc))
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('issuer certificate has expired', cm.exception.get('mesg'))

            # Expired root CA — with intermediate chain (root -> imm1 -> imm2 -> code)
            # Save the expired root's key so genCaCert can sign intermediates with it
            cdir._savePkeyTo(expkey, 'cas', 'adv-exproot.key')
            cdir.genCaCert('adv-exproot-imm1', signas='adv-exproot')
            cdir.genCaCert('adv-exproot-imm2', signas='adv-exproot-imm1')
            cdir.genCodeCert('adv-exproot-deep-code', signas='adv-exproot-imm2')

            fp = cdir.getCodeCertPath('adv-exproot-deep-code')
            with s_common.genfile(fp) as fd:
                deepbyts = fd.read()

            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(deepbyts)
            self.isin('issuer certificate has expired', cm.exception.get('mesg'))

            # Not-yet-valid root CA
            futkey = c_rsa.generate_private_key(65537, 2048)
            future = now + datetime.timedelta(days=365)
            byts = _makeRootAndCode('adv-futroot', 'adv-futroot-code', futkey,
                                    future, future + datetime.timedelta(days=3650))
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('issuer certificate is not yet valid', cm.exception.get('mesg'))

    async def test_certdir_adversarial_empty_subject_ca(self):
        '''A CA cert with an empty subject Name can match any cert with an empty issuer.

        saveCaCertByts rejects empty-subject certs (IndexError on CN lookup).
        Even if manually placed in cas/, the signature check prevents cross-signing.
        '''
        with self.getCertDir() as cdir:
            now = datetime.datetime.now(datetime.UTC)

            # Create a legitimate CA and code cert
            cdir.genCaCert('adv-emptysub-legit')
            cdir.genCodeCert('adv-emptysub-code', signas='adv-emptysub-legit')

            fp = cdir.getCodeCertPath('adv-emptysub-code')
            with s_common.genfile(fp) as fd:
                legitbyts = fd.read()

            # Legitimate cert validates
            self.nn(cdir.valCodeCert(legitbyts))

            # saveCaCertByts rejects a cert with an empty subject
            emptykey = c_rsa.generate_private_key(65537, 2048)
            emptycacert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([]))
                .issuer_name(c_x509.Name([]))
                .public_key(emptykey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(emptykey, c_hashes.SHA256()))

            with self.raises(s_exc.BadCertBytes) as cm:
                cdir.saveCaCertByts(emptycacert.public_bytes(c_serialization.Encoding.PEM))
            self.isin('Common Name', cm.exception.get('mesg'))

            # Manually place the empty-subject CA into cas/
            caspath = os.path.join(cdir.certdirs[0], 'cas')
            with open(os.path.join(caspath, 'empty-subject.crt'), 'wb') as fd:
                fd.write(emptycacert.public_bytes(c_serialization.Encoding.PEM))

            # Build a code cert with an empty issuer signed by the empty-subject CA
            emptyissuercert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-emptyissuer-code')]))
                .issuer_name(c_x509.Name([]))
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(emptykey, c_hashes.SHA256()))

            emptybyts = emptyissuercert.public_bytes(c_serialization.Encoding.PEM)

            # This validates because the empty-subject CA is in cas/ and the signature is valid
            self.nn(cdir.valCodeCert(emptybyts))

            # The legitimate cert is NOT affected — the empty-subject CA does not match its issuer
            self.nn(cdir.valCodeCert(legitbyts))

    async def test_certdir_adversarial_deceptive_selfsigned(self):
        '''A cert signed by its own key but with issuer != subject is not treated as a root.

        _verifyChain uses issuer == subject to identify self-signed roots. A cert
        that is cryptographically self-signed but has a mismatched issuer field
        will not terminate the chain walk and instead fails because no CA
        matching the fake issuer name exists in the store.
        '''
        with self.getCertDir() as cdir:
            cdir.genCaCert('adv-deceptive-legit')

            deceptivekey = c_rsa.generate_private_key(65537, 2048)
            now = datetime.datetime.now(datetime.UTC)

            # Self-signed by key but issuer != subject
            deceptiveca = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-deceptive-root')]))
                .issuer_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-fake-issuer')]))
                .public_key(deceptivekey.public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .sign(deceptivekey, c_hashes.SHA256()))

            # Place in cas/ manually
            caspath = os.path.join(cdir.certdirs[0], 'cas')
            with open(os.path.join(caspath, 'adv-deceptive-root.crt'), 'wb') as fd:
                fd.write(deceptiveca.public_bytes(c_serialization.Encoding.PEM))

            # Code cert signed by the deceptive CA
            codecert = (c_x509.CertificateBuilder()
                .subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, 'adv-deceptive-code')]))
                .issuer_name(deceptiveca.subject)
                .public_key(c_rsa.generate_private_key(65537, 2048).public_key())
                .serial_number(c_x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + datetime.timedelta(days=3650))
                .add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]), critical=False)
                .add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
                .sign(deceptivekey, c_hashes.SHA256()))

            byts = codecert.public_bytes(c_serialization.Encoding.PEM)

            # _verifyChain finds deceptive CA as issuer of the code cert,
            # but then tries to verify the deceptive CA itself. Since
            # issuer != subject, it recurses looking for 'adv-fake-issuer'
            # which does not exist in the store.
            with self.raises(s_exc.BadCertVerify) as cm:
                cdir.valCodeCert(byts)
            self.isin('unable to get local issuer certificate', cm.exception.get('mesg'))
