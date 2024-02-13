import os
import ssl
import datetime
from contextlib import contextmanager

from OpenSSL import crypto, SSL

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils
import synapse.tools.genpkg as s_genpkg
import synapse.tools.easycert as s_easycert

import synapse.lib.crypto.rsa as s_crypto_rsa

import cryptography.x509 as c_x509
import cryptography.exceptions as c_exc
import cryptography.x509.verification as c_verification
import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.dsa as c_dsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding
import cryptography.hazmat.primitives.serialization as c_serialization
import cryptography.hazmat.primitives.serialization.pkcs12 as c_pkcs12


class CertDirNewTest(s_t_utils.SynTest):

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

    def basic_assertions(self,
                         cdir: s_certdir.CertDir,
                         cert: c_x509.Certificate,
                         key: s_certdir.PkeyType,
                         cacert: c_x509.Certificate =None):
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

        # XXX FIXME - Figure out a parallel for this in cryptography parlance?
        # This is demonstrative of a a high level of control over a SSL Context that
        # we don't actually utilize. ???
        # # ensure that a ssl context using both cert/key match
        # sslcontext = SSL.Context(SSL.TLSv1_2_METHOD)
        # sslcontext.use_certificate(cert)
        # sslcontext.use_privatekey(key)
        # self.none(sslcontext.check_privatekey())

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
                        key: s_certdir.PkeyType,
                        cacert: c_x509.Certificate = None):
        '''
        test basic certificate assumptions for a host certificate

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        # XXX FIXME There is a schism between teh items build for use with the builder
        # interface nd the items parsed from a certificate on disk :\
        # exts = {}
        # for ext in cert.extensions:  # type: c_x509.Extension
        #     self.false(ext.critical)
        #     short_name = ext.oid._name
        #     if short_name == 'Unknown OID':
        #         short_name = ext.oid.dotted_string
        #     exts[short_name] = ext
        #
        # nscertext = c_x509.UnrecognizedExtension(
        #     oid=c_x509.ObjectIdentifier('2.16.840.1.113730.1.1'), value=b'\x03\x02\x06@')
        # keyuseext = c_x509.KeyUsage(digital_signature=True, key_encipherment=True, data_encipherment=False, key_agreement=False,
        #                     key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False,
        #                     content_commitment=False)
        # print(keyuseext.public_bytes())
        # extkeyuseext = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.SERVER_AUTH])
        # basicconext = c_x509.BasicConstraints(ca=False, path_length=None)
        #
        # # self.eq(exts['2.16.840.1.113730.1.1'], nscertext)
        # self.eq(exts['keyUsage'], keyuseext)
        # # self.eq(exts[b'extendedKeyUsage'], extkeyuseext.get_data())
        # # self.eq(exts[b'basicConstraints'], basicconext.get_data())
        # # self.isin(b'subjectAltName', exts)

    def user_assertions(self,
                        cdir: s_certdir.CertDir,
                        cert: c_x509.Certificate,
                        key: s_certdir.PkeyType,
                        cacert: c_x509.Certificate = None):
        '''
        test basic certificate assumptions for a user certificate

        Args:
            cdir (s_certdir.CertDir): certdir object
            cert (crypto.X509): Cert to test
            key (crypto.PKey): Key for the certification
            cacert (crypto.X509): Corresponding CA cert (optional)
        '''
        # XXX FIXME There is a schism between teh items build for use with the builder
        # interface nd the items parsed from a certificate on disk :\
        # nextensions = cert.get_extension_count()
        # exts = {ext.get_short_name(): ext.get_data() for ext in [cert.get_extension(i) for i in range(nextensions)]}
        #
        # nscertext = crypto.X509Extension(b'nsCertType', False, b'client')
        # keyuseext = crypto.X509Extension(b'keyUsage', False, b'digitalSignature')
        # extkeyuseext = crypto.X509Extension(b'extendedKeyUsage', False, b'clientAuth')
        # basicconext = crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE')
        # self.eq(exts[b'nsCertType'], nscertext.get_data())
        # self.eq(exts[b'keyUsage'], keyuseext.get_data())
        # self.eq(exts[b'extendedKeyUsage'], extkeyuseext.get_data())
        # self.eq(exts[b'basicConstraints'], basicconext.get_data())
        # self.notin(b'subjectAltName', exts)

    def p12_assertions(self,
                       cdir: s_certdir.CertDir,
                       cert: c_x509.Certificate,
                       key: s_certdir.PkeyType,
                       p12: c_pkcs12.PKCS12KeyAndCertificates,
                       cacert: c_x509.Certificate = None):
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

    def test_certdir_cas(self):

        with self.getCertDir() as cdir:  # type: s_certdir.CertDiNew
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
        self.skip('XXX FIXME Sort out SANS support.')
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

    def test_certdir_users_csr(self):
        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
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

        with self.getCertDir() as cdir:  # type: s_certdir.CertDir
            caname = 'The Vertex Project ROOT CA'
            immname = 'The Vertex Project Intermediate CA 00'
            codename = 'Vertex Build Pipeline'
            codename2 = 'Vertex Build Pipeline Redux'
            codename3 = 'Vertex Build Pipeline Triple Threat'

            cdir.genCaCert(caname)
            cdir.genCaCert(immname, signas=caname)
            cdir.genUserCert('notCodeCert', signas=caname, )

            cdir.genCaCrl(caname)._save()
            cdir.genCaCrl(immname)._save()

            cdir.genCodeCert(codename, signas=immname)
            rsak = cdir.getCodeKey(codename)
            cert = cdir.getCodeCert(codename)

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
