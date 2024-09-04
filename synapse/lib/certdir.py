import io
import os
import ssl
import time
import shutil
import socket
import logging
import datetime
import collections

from typing import List, Tuple, Union

from OpenSSL import crypto  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.const as s_const
import synapse.lib.output as s_output
import synapse.lib.crypto.rsa as s_rsa

import cryptography.x509 as c_x509
import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.dsa as c_dsa
import cryptography.hazmat.primitives.asymmetric.types as c_types
import cryptography.hazmat.primitives.serialization as c_serialization
import cryptography.hazmat.primitives.serialization.pkcs12 as c_pkcs12

defdir_default = '~/.syn/certs'
defdir = os.getenv('SYN_CERT_DIR')
if defdir is None:
    defdir = defdir_default

logger = logging.getLogger(__name__)

NSCERTTYPE_OID = '2.16.840.1.113730.1.1'
NSCERTTYPE_CLIENT = b'\x03\x02\x07\x80'   # client
NSCERTTYPE_SERVER = b'\x03\x02\x06@'      # server
NSCERTTYPE_OBJSIGN = b'\x03\x02\x04\x10'  # objsign

TEN_YEARS = 10 * s_const.year  # 10 years in milliseconds
TEN_YEARS_TD = datetime.timedelta(milliseconds=TEN_YEARS)

StrOrNone = Union[str | None]
BytesOrNone = Union[bytes | None]
OutPutOrNone = Union[s_output.OutPut | None]
CertOrNone = Union[c_x509.Certificate | None]
PkeyOrNone = Union[c_rsa.RSAPrivateKey | c_dsa.DSAPrivateKey | None]
PkeyAndCert = Tuple[c_rsa.RSAPrivateKey, c_x509.Certificate]
PkeyAndBuilder = Tuple[c_rsa.RSAPrivateKey, c_x509.CertificateBuilder]
PrivKeyPubKeyBuilder = Tuple[Union[c_rsa.RSAPrivateKey | None], c_types.PublicKeyTypes, c_x509.CertificateBuilder]
Pkey = Union[c_rsa.RSAPrivateKey | c_dsa.DSAPrivateKey]
Pkcs12OrNone = Union[c_pkcs12.PKCS12KeyAndCertificates | None]
PkeyOrNoneAndCert = Tuple[Union[c_rsa.RSAPrivateKey | None], c_x509.Certificate]
# Used for handling CSRs
PubKeyOrNone = Union[c_types.PublicKeyTypes | None]

def iterFqdnUp(fqdn):
    levs = fqdn.split('.')
    for i in range(len(levs)):
        yield '.'.join(levs[i:])

def _initTLSServerCiphers():
    '''
    Create a cipher string that supports TLS 1.2 and TLS 1.3 ciphers which do not use RSA.

    Note:
        The results of this may be dynamic depending on the interpreter version and OpenSSL library in use.
        For Python 3.8 and below, the cipher list is a subset of the normal default ciphers which commonly available.
        For Python 3.10+, the changes should be negligible.

        The resulting string is cached in the module global TLS_SERVER_CIPHERS and called at import time.

    Returns:
        str: A OpenSSL Cipher string.
    '''
    ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)  # type: ssl.SSLContext
    _ciphers = []
    for cipher in ctx.get_ciphers():  # pragma: no cover
        if cipher.get('protocol') not in ('TLSv1.2', 'TLSv1.3'):
            continue
        if cipher.get('kea') == 'kx-rsa':  # pragma: no cover
            continue
        _ciphers.append(cipher)

    if len(_ciphers) == 0:  # pragma: no cover
        raise s_exc.SynErr(mesg='No valid TLS ciphers are available for this Python installation.')

    ciphers = ':'.join([c.get('name') for c in _ciphers])

    return ciphers

TLS_SERVER_CIPHERS = _initTLSServerCiphers()

def _unpackContextError(e: crypto.X509StoreContextError) -> str:
    # account for backward incompatible change in pyopenssl v22.1.0
    if e.args:
        if isinstance(e.args[0], str):
            errstr = e.args[0]
        else:  # pragma: no cover
            errstr = e.args[0][2]  # pyopenssl < 22.1.0
        mesg = f'{errstr}'
    else:  # pragma: no cover
        mesg = 'Certficate failed to verify.'
    return mesg

class Crl:

    def __init__(self, cdir, name):

        self.name = name
        self.certdir = cdir
        self.path = self.certdir.genCrlPath(name)

        self.crlbuilder = c_x509.CertificateRevocationListBuilder().issuer_name(c_x509.Name([
            c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name),
        ]))

        if os.path.isfile(self.path):
            with io.open(self.path, 'rb') as fd:
                crl = c_x509.load_pem_x509_crl(fd.read())
                for revc in crl:
                    self.crlbuilder = self.crlbuilder.add_revoked_certificate(revc)

    def revoke(self, cert: c_x509.Certificate) -> None:
        '''
        Revoke a certificate with the CRL.

        Args:
            cert: The certificate to revoke.

        Returns:
            None
        '''
        try:
            self._verify(cert)
        except s_exc.BadCertVerify as e:
            raise s_exc.BadCertVerify(mesg=f'Failed to validate that certificate was signed by {self.name}') from e

        now = datetime.datetime.now(datetime.UTC)
        builder = c_x509.RevokedCertificateBuilder()
        builder = builder.serial_number(cert.serial_number)
        builder = builder.revocation_date(now)
        builder = builder.add_extension(c_x509.CRLReason(c_x509.ReasonFlags.unspecified), critical=False)
        revoked_cert = builder.build()

        self.crlbuilder = self.crlbuilder.add_revoked_certificate(revoked_cert)
        self._save(now)

    def _verify(self, cert):
        # Verify the cert was signed by the CA in self.name
        cacert = self.certdir.getCaCert(self.name)
        store = crypto.X509Store()
        store.add_cert(crypto.X509.from_cryptography(cacert))
        store.set_flags(crypto.X509StoreFlags.PARTIAL_CHAIN)
        ctx = crypto.X509StoreContext(store, crypto.X509.from_cryptography(cert))
        try:
            ctx.verify_certificate()
        except crypto.X509StoreContextError as e:
            raise s_exc.BadCertVerify(mesg=_unpackContextError(e)) from None

    def _save(self, timestamp: [datetime.datetime | None] = None) -> None:

        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.UTC)

        self.crlbuilder = self.crlbuilder.last_update(timestamp)
        # We have to have a next updated time; but we set it to be >=  the lifespan of our certificates in general.
        self.crlbuilder = self.crlbuilder.next_update(timestamp + TEN_YEARS_TD)
        prvkey = self.certdir.getCaKey(self.name)
        crl = self.crlbuilder.sign(private_key=prvkey, algorithm=c_hashes.SHA256())

        with s_common.genfile(self.path) as fd:
            fd.truncate(0)
            fd.write(crl.public_bytes(c_serialization.Encoding.PEM))

def getServerSSLContext() -> ssl.SSLContext:
    '''
    Get a server SSLContext object.

    This object has a minimum TLS version of 1.2, a subset of ciphers in use, and disabled client renegotiation.

    This object has no certificates loaded in it.

    Returns:
        ssl.SSLContext: The context object.
    '''
    sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sslctx.minimum_version = ssl.TLSVersion.TLSv1_2
    sslctx.set_ciphers(TLS_SERVER_CIPHERS)
    # Disable client renegotiation if available.
    sslctx.options |= getattr(ssl, "OP_NO_RENEGOTIATION", 0)
    return sslctx

class CertDir:
    '''
    Certificate loading/generation/signing utilities.

    Features:
        * Locates and load certificates, keys, and certificate signing requests (CSRs).
        * Generates keypairs for users, hosts, and certificate authorities (CAs), supports both signed and self-signed.
        * Generates certificate signing requests (CSRs) for users, hosts, and certificate authorities (CAs).
        * Signs certificate signing requests (CSRs).
        * Generates PKCS#12 archives for use in browser.

    Args:
        path (str): Optional path which can override the default path directory.

    Notes:
        * All certificates will be loaded from and written to ~/.syn/certs by default. Set the environment variable
          SYN_CERT_DIR to override.
        * All certificate generation methods create 4096 bit RSA keypairs.
        * All certificate signing methods use sha256 as the signature algorithm.
        * CertDir does not currently support signing CA CSRs.
    '''

    def __init__(self, path: StrOrNone = None):
        self.crypto_numbits = 4096
        self.signing_digest = c_hashes.SHA256

        self.certdirs = []
        self.pathrefs = collections.defaultdict(int)

        if path is None:
            path = (defdir,)

        if not isinstance(path, (list, tuple)):
            path = (path,)

        for p in path:
            self.addCertPath(p)

    def addCertPath(self, *path: str):

        fullpath = s_common.genpath(*path)
        self.pathrefs[fullpath] += 1

        if self.pathrefs[fullpath] == 1:
            self.certdirs.append(fullpath)

    def delCertPath(self, *path: str):
        fullpath = s_common.genpath(*path)
        self.pathrefs[fullpath] -= 1
        if self.pathrefs[fullpath] <= 0:
            self.certdirs.remove(fullpath)
            self.pathrefs.pop(fullpath, None)

    def genCaCert(self, name: str,
                  signas: StrOrNone = None,
                  outp: OutPutOrNone = None,
                  save: bool = True) -> PkeyAndCert:
        '''
        Generates a CA keypair.

        Args:
            name: The name of the CA keypair.
            signas: The CA keypair to sign the new CA with.
            outp: The output buffer.
            save: Save the certificate and key to disk.

        Examples:
            Make a CA named "myca"::

                mycakey, mycacert = cdir.genCaCert('myca')

        Returns:
            Tuple containing the private key and certificate objects.
        '''
        prvkey = self._genPrivKey()
        builder = self._genCertBuilder(name, prvkey.public_key())
        builder = builder.add_extension(
            c_x509.BasicConstraints(ca=True, path_length=None), critical=False,
        )

        if signas is not None:
            cert = self.signCertAs(builder, signas)
        else:
            cert = self.selfSignCert(builder, prvkey)

        if save:

            keypath = self._savePkeyTo(prvkey, 'cas', '%s.key' % name)
            if outp is not None:
                outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'cas', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return prvkey, cert

    def genHostCert(self, name: str,
                    signas: StrOrNone = None,
                    outp: OutPutOrNone = None,
                    csr: PubKeyOrNone = None,
                    sans: StrOrNone = None,
                    save: bool = True) -> PkeyOrNoneAndCert:
        '''
        Generates a host keypair.

        Args:
            name: The name of the host keypair.
            signas: The CA keypair to sign the new host keypair with.
            outp: The output buffer.
            csr: The CSR public key when generating the keypair from a CSR.
            sans: String of comma separated alternative names.

        Examples:
            Make a host keypair named "myhost"::

                myhostkey, myhostcert = cdir.genHostCert('myhost')

        Returns:
            Tuple containing the private key and certificate objects. Private key may be None when signing a CSR.
        '''
        if csr is None:
            prvkey = self._genPrivKey()
            pubkey = prvkey.public_key()
        else:
            prvkey = None
            pubkey = csr

        builder = self._genCertBuilder(name, pubkey)

        ext_sans = collections.defaultdict(set)
        ext_sans['dns'].add(name)
        sans_ctors = {'dns': c_x509.DNSName,
                      'email': c_x509.RFC822Name,
                      'uri': c_x509.UniformResourceIdentifier}
        if sans:
            sans = sans.split(',')
            for san in sans:
                if san.startswith('DNS:'):
                    san = san[4:]
                    ext_sans['dns'].add(san)
                elif san.startswith('email:'):
                    san = san[6:]
                    ext_sans['email'].add(san)
                elif san.startswith('URI:'):
                    san = san[4:]
                    ext_sans['uri'].add(san)
                else:
                    raise s_exc.BadArg(mesg=f'Unsupported san value: {san}')
        sans = []
        for key, ctor in sans_ctors.items():
            values = sorted(ext_sans[key])
            for valu in values:
                sans.append(ctor(valu))

        builder = builder.add_extension(c_x509.UnrecognizedExtension(
            oid=c_x509.ObjectIdentifier(NSCERTTYPE_OID), value=NSCERTTYPE_SERVER),
            critical=False,
        )
        builder = builder.add_extension(
            c_x509.KeyUsage(digital_signature=True, key_encipherment=True, data_encipherment=False,
                            key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False,
                            decipher_only=False, content_commitment=False),
            critical=False,
        )
        builder = builder.add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                                        critical=False)
        builder = builder.add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)
        builder = builder.add_extension(c_x509.SubjectAlternativeName(sans), critical=False)

        if signas is not None:
            cert = self.signCertAs(builder, signas)
        else:
            cert = self.selfSignCert(builder, prvkey)

        if save:
            if prvkey is not None:
                keypath = self._savePkeyTo(prvkey, 'hosts', '%s.key' % name)
                if outp is not None:
                    outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'hosts', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return prvkey, cert

    def genHostCsr(self, name: str, outp: OutPutOrNone = None) -> bytes:
        '''
        Generates a host certificate signing request.

        Args:
            name: The name of the host CSR.
            outp: The output buffer.

        Examples:
            Generate a CSR for the host key named "myhost"::

                cdir.genHostCsr('myhost')

        Returns:
            The bytes of the CSR.
        '''
        return self._genPkeyCsr(name, 'hosts', outp=outp)

    def genUserCert(self,
                    name: str,
                    signas: StrOrNone = None,
                    outp: OutPutOrNone = None,
                    csr: PubKeyOrNone = None,
                    save: bool = True) -> PkeyOrNoneAndCert:
        '''
        Generates a user keypair.

        Args:
            name: The name of the user keypair.
            signas: The CA keypair to sign the new user keypair with.
            outp: The output buffer.
            csr: The CSR public key when generating the keypair from a CSR.

        Examples:
            Generate a user cert for the user "myuser"::

                myuserkey, myusercert = cdir.genUserCert('myuser')

        Returns:
            Tuple containing the key and certificate objects.
        '''
        if csr is None:
            prvkey = self._genPrivKey()
            pubkey = prvkey.public_key()
        else:
            prvkey = None
            pubkey = csr

        builder = self._genCertBuilder(name, pubkey)
        builder = builder.add_extension(c_x509.UnrecognizedExtension(
            oid=c_x509.ObjectIdentifier(NSCERTTYPE_OID), value=NSCERTTYPE_CLIENT),
            critical=False,
        )
        builder = builder.add_extension(
            c_x509.KeyUsage(digital_signature=True, key_encipherment=False, data_encipherment=False,
                            key_agreement=False,
                            key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False,
                            content_commitment=False),
            critical=False,
        )
        builder = builder.add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
                                        critical=False)
        builder = builder.add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)

        if signas is not None:
            cert = self.signCertAs(builder, signas)
        else:
            cert = self.selfSignCert(builder, prvkey)

        if save:
            if prvkey is not None:
                keypath = self._savePkeyTo(prvkey, 'users', '%s.key' % name)
                if outp is not None:
                    outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'users', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return prvkey, cert

    def genCodeCert(self, name: str, signas: StrOrNone = None, outp: OutPutOrNone = None, save: bool = True) \
            -> PkeyAndCert:
        '''
        Generates a code signing keypair.

        Args:
            name: The name of the code signing cert.
            signas: The CA keypair to sign the new code keypair with.
            outp: The output buffer.

        Examples:

            Generate a code signing cert for the name "The Vertex Project"::

                myuserkey, myusercert = cdir.genCodeCert('The Vertex Project')

        Returns:
            Tuple containing the key and certificate objects.
        '''
        prvkey = self._genPrivKey()
        pubkey = prvkey.public_key()

        builder = self._genCertBuilder(name, pubkey)
        builder = builder.add_extension(c_x509.UnrecognizedExtension(
            oid=c_x509.ObjectIdentifier(NSCERTTYPE_OID), value=NSCERTTYPE_OBJSIGN),
            critical=False,
        )
        builder = builder.add_extension(
            c_x509.KeyUsage(digital_signature=True, key_encipherment=False, data_encipherment=False,
                            key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False,
                            decipher_only=False, content_commitment=False),
            critical=False,
        )
        builder = builder.add_extension(c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]),
                                        critical=False)
        builder = builder.add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=False)

        if signas is not None:
            cert = self.signCertAs(builder, signas)
        else:
            cert = self.selfSignCert(builder, prvkey)

        if save:
            keypath = self._savePkeyTo(prvkey, 'code', '%s.key' % name)
            if outp is not None:
                outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'code', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return prvkey, cert

    def getCodeKeyPath(self, name: str) -> StrOrNone:
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'code', f'{name}.key')
            if os.path.isfile(path):
                return path

    def getCodeCertPath(self, name: str) -> StrOrNone:
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'code', f'{name}.crt')
            if os.path.isfile(path):
                return path

    def getCodeKey(self, name: str) -> Union[s_rsa.PriKey | None]:

        path = self.getCodeKeyPath(name)
        if path is None:
            return None

        pkey = self._loadKeyPath(path)
        return s_rsa.PriKey(pkey)

    def getCodeCert(self, name: str) -> CertOrNone:

        path = self.getCodeCertPath(name)
        if path is None:  # pragma: no cover
            return None

        return self._loadCertPath(path)

    def valCodeCert(self, byts: bytes) -> c_x509.Certificate:
        '''
        Verify a code cert is valid according to certdir's available CAs and CRLs.

        Args:
            byts: The certificate bytes.

        Raises:
            s_exc.BadCertVerify if we are unable to verify the certificate.

        Returns:
            The certificate.
        '''
        reqext = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CODE_SIGNING])

        cert = self.loadCertByts(byts)
        eku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE)
        if reqext != eku.value:
            mesg = 'Certificate is not for code signing.'
            raise s_exc.BadCertBytes(mesg=mesg)

        crls = self._getCaCrls()
        cacerts = self.getCaCerts()

        store = crypto.X509Store()
        [store.add_cert(crypto.X509.from_cryptography(cacert)) for cacert in cacerts]

        if crls:
            store.set_flags(crypto.X509StoreFlags.CRL_CHECK | crypto.X509StoreFlags.CRL_CHECK_ALL)
            [store.add_crl(crypto.CRL.from_cryptography(crl)) for crl in crls]

        ctx = crypto.X509StoreContext(store, crypto.X509.from_cryptography(cert))
        try:
            ctx.verify_certificate()  # raises X509StoreContextError if unable to verify
        except crypto.X509StoreContextError as e:
            mesg = _unpackContextError(e)
            raise s_exc.BadCertVerify(mesg=mesg)
        return cert

    def _getCaCrls(self) -> List[c_x509.CertificateRevocationList]:

        crls = []
        for cdir in self.certdirs:

            crlpath = os.path.join(cdir, 'crls')
            if not os.path.isdir(crlpath):
                continue

            for name in os.listdir(crlpath):

                if not name.endswith('.crl'):  # pragma: no cover
                    continue

                fullpath = os.path.join(crlpath, name)
                with io.open(fullpath, 'rb') as fd:
                    crl = c_x509.load_pem_x509_crl(fd.read())
                    crls.append(crl)

        return crls

    def genClientCert(self, name: str, outp: OutPutOrNone = None) -> None:
        '''
        Generates a user PKCS #12 archive.

        Please note that the resulting file will contain private key material.

        Args:
            name (str): The name of the user keypair.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            Make the PKC12 object for user "myuser"::

                myuserpkcs12 = cdir.genClientCert('myuser')

        Returns:
            None
        '''
        ucert = self.getUserCert(name)
        if not ucert:
            raise s_exc.NoSuchFile(mesg='missing User cert', name=name)

        capath = self._getCaPath(ucert)
        cacert = self._loadCertPath(capath)
        if not cacert:
            raise s_exc.NoSuchFile(mesg='missing CA cert', path=capath)

        ukey = self.getUserKey(name)
        if not ukey:
            raise s_exc.NoSuchFile(mesg='missing User private key', name=name)

        byts = c_pkcs12.serialize_key_and_certificates(name=name.encode('utf-8'),
                                                       key=ukey,
                                                       cert=ucert,
                                                       cas=[cacert],
                                                       encryption_algorithm=c_serialization.NoEncryption())
        crtpath = self._saveP12To(byts, 'users', '%s.p12' % name)
        if outp is not None:
            outp.printf('client cert saved: %s' % (crtpath,))

    def valUserCert(self, byts: bytes, cacerts: Union[List[c_x509.Certificate] | None] = None) -> c_x509.Certificate:
        '''
        Validate the PEM encoded x509 user certificate bytes and return it.

        Args:
            byts: The bytes for the User Certificate.
            cacerts: A tuple of CA Certificates to use for validating the user cert.

        Raises:
            BadCertVerify: If the certificate is not valid.

        Returns:
            The certificate, if it is valid.
        '''
        reqext = c_x509.ExtendedKeyUsage([c_x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH])

        cert = self.loadCertByts(byts)
        eku = cert.extensions.get_extension_for_oid(c_x509.oid.ExtensionOID.EXTENDED_KEY_USAGE)

        if reqext != eku.value:
            mesg = 'Certificate is not for client auth.'
            raise s_exc.BadCertBytes(mesg=mesg)
        cert = self.loadCertByts(byts)

        if cacerts is None:
            cacerts = self.getCaCerts()

        store = crypto.X509Store()
        [store.add_cert(crypto.X509.from_cryptography(cacert)) for cacert in cacerts]

        ctx = crypto.X509StoreContext(store, crypto.X509.from_cryptography(cert))
        try:
            ctx.verify_certificate()
        except crypto.X509StoreContextError as e:
            raise s_exc.BadCertVerify(mesg=_unpackContextError(e))
        return cert

    def genUserCsr(self, name: str, outp: OutPutOrNone = None) -> bytes:
        '''
        Generates a user certificate signing request.

        Args:
            name: The name of the user CSR.
            outp: The output buffer.

        Examples:
            Generate a CSR for the user "myuser"::

                cdir.genUserCsr('myuser')

        Returns:
            The bytes of the CSR.
        '''
        return self._genPkeyCsr(name, 'users', outp=outp)

    def getCaCert(self, name: str) -> CertOrNone:
        '''
        Loads the X509 object for a given CA.

        Args:
            name: The name of the CA keypair.

        Examples:

            Get the certificate for the  CA "myca"::

                mycacert = cdir.getCaCert('myca')

        Returns:
            The certificate, if exists.
        '''
        return self._loadCertPath(self.getCaCertPath(name))

    def getCaCertBytes(self, name: str) -> bytes:
        path = self.getCaCertPath(name)
        if os.path.exists(path):
            with open(path, 'rb') as fd:
                return fd.read()

    def getCaCerts(self) -> List[c_x509.Certificate]:
        '''
        Return a list of CA certs from the CertDir.

        Returns:
            List of CA certificates.
        '''
        retn = []

        for cdir in self.certdirs:

            path = s_common.genpath(cdir, 'cas')
            if not os.path.isdir(path):
                continue

            for name in os.listdir(path):

                if not name.endswith('.crt'):  # pragma: no cover
                    continue

                full = s_common.genpath(cdir, 'cas', name)
                retn.append(self._loadCertPath(full))

        return retn

    def getCaCertPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a CA certificate.

        Args:
            name: The name of the CA keypair.

        Examples:
            Get the path to the CA certificate for the CA "myca"::

                mypath = cdir.getCACertPath('myca')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'cas', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getCaKey(self, name) -> PkeyOrNone:
        '''
        Loads the PKey object for a given CA keypair.

        Args:
            name: The name of the CA keypair.

        Examples:
            Get the private key for the CA "myca"::

                mycakey = cdir.getCaKey('myca')

        Returns:
            The private key, if exists.
        '''
        return self._loadKeyPath(self.getCaKeyPath(name))

    def getCaKeyPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a CA key.

        Args:
            name: The name of the CA keypair.

        Examples:
            Get the path to the private key for the CA "myca"::

                mypath = cdir.getCAKeyPath('myca')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'cas', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def getClientCert(self, name: str) -> Pkcs12OrNone:
        '''
        Loads the PKCS12 archive object for a given user keypair.

        Args:
            name: The name of the user keypair.

        Examples:
            Get the PKCS12 object for the user "myuser"::

                mypkcs12 = cdir.getClientCert('myuser')

        Notes:
            The PKCS12 archive will contain private key material if it was created with CertDir or the easycert tool

        Returns:
            The PKCS12 archive, if exists.
        '''
        return self._loadP12Path(self.getClientCertPath(name))

    def getClientCertPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a client certificate.

        Args:
            name: The name of the client keypair.

        Examples:
            Get the path to the client certificate for "myuser"::

                mypath = cdir.getClientCertPath('myuser')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.p12' % name)
            if os.path.isfile(path):
                return path

    def getHostCaPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to the CA certificate that issued a given host keypair.

        Args:
            name: The name of the host keypair.

        Examples:

            Get the path to the CA cert which issue the cert for "myhost"::

                mypath = cdir.getHostCaPath('myhost')

        Returns:
            The path, if exists.
        '''
        cert = self.getHostCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getHostCert(self, name: str) -> CertOrNone:
        '''
        Loads the X509 object for a given host keypair.

        Args:
            name: The name of the host keypair.

        Examples:
            Get the certificate object for the host "myhost"::

                myhostcert = cdir.getHostCert('myhost')

        Returns:
            The certificate, if exists.
        '''
        return self._loadCertPath(self.getHostCertPath(name))

    def getHostCertHash(self, name: str) -> StrOrNone:
        cert = self.getHostCert(name)
        if cert is None:
            return None
        return s_common.ehex(cert.fingerprint(c_hashes.SHA256()))

    def getHostCertPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a host certificate.

        Args:
            name: The name of the host keypair.

        Examples:
            Get the path to the host certificate for the host "myhost"::

                mypath = cdir.getHostCertPath('myhost')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'hosts', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getHostKey(self, name: str) -> PkeyOrNone:
        '''
        Loads the PKey object for a given host keypair.

        Args:
            name: The name of the host keypair.

        Examples:
            Get the private key object for the host "myhost"::

                myhostkey = cdir.getHostKey('myhost')

        Returns:
            The private key, if exists.
        '''
        return self._loadKeyPath(self.getHostKeyPath(name))

    def getHostKeyPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a host key.

        Args:
            name: The name of the host keypair.

        Examples:
            Get the path to the host key for the host "myhost"::

                mypath = cdir.getHostKeyPath('myhost')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'hosts', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def getUserCaPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to the CA certificate that issued a given user keypair.

        Args:
            name: The name of the user keypair.

        Examples:
            Get the path to the CA cert which issue the cert for "myuser"::

                mypath = cdir.getUserCaPath('myuser')

        Returns:
            The path, if exists.
        '''
        cert = self.getUserCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getUserCert(self, name: str) -> CertOrNone:
        '''
        Loads the X509 object for a given user keypair.

        Args:
            name: The name of the user keypair.

        Examples:
            Get the certificate object for the user "myuser"::

                myusercert = cdir.getUserCert('myuser')

        Returns:
            The certificate, if exists.
        '''
        return self._loadCertPath(self.getUserCertPath(name))

    def getUserCertPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a user certificate.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the path for the user cert for "myuser"::

                mypath = cdir.getUserCertPath('myuser')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getUserForHost(self, user: str, host: str) -> StrOrNone:
        '''
        Gets the name of the first existing user cert for a given user and host.

        Args:
            user: The name of the user.
            host: The name of the host.

        Examples:
            Get the name for the "myuser" user cert at "cool.vertex.link"::

                usercertname = cdir.getUserForHost('myuser', 'cool.vertex.link')

        Returns:
            str: The cert name, if exists.
        '''
        for name in iterFqdnUp(host):
            usercert = '%s@%s' % (user, name)
            if self.isUserCert(usercert):
                return usercert

    def getUserKey(self, name: str) -> PkeyOrNone:
        '''
        Loads the PKey object for a given user keypair.


        Args:
            name: The name of the user keypair.

        Examples:
            Get the key object for the user key for "myuser"::

                myuserkey = cdir.getUserKey('myuser')

        Returns:
            The private key, if exists.
        '''
        return self._loadKeyPath(self.getUserKeyPath(name))

    def getUserKeyPath(self, name: str) -> StrOrNone:
        '''
        Gets the path to a user key.

        Args:
            name: The name of the user keypair.

        Examples:
            Get the path to the user key for "myuser"::

                mypath = cdir.getUserKeyPath('myuser')

        Returns:
            The path, if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def getUserCsrPath(self, name: str) -> StrOrNone:
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.csr' % name)
            if os.path.isfile(path):
                return path

    def getHostCsrPath(self, name: str) -> StrOrNone:
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'hosts', '%s.csr' % name)
            if os.path.isfile(path):
                return path

    def importFile(self, path: str, mode: str, outp: OutPutOrNone = None) -> None:
        '''
        Imports certs and keys into the Synapse cert directory

        Args:
            path: The path of the file to be imported.
            mode: The certdir subdirectory to import the file into.

        Examples:
            Import CA certifciate 'mycoolca.crt' to the 'cas' directory::

                certdir.importFile('mycoolca.crt', 'cas')

        Notes:
            importFile does not perform any validation on the files it imports.

        Returns:
            None
        '''
        if not os.path.isfile(path):
            raise s_exc.NoSuchFile(mesg=f'File {path} does not exist', path=path)

        fname = os.path.split(path)[1]
        parts = fname.rsplit('.', 1)
        ext = parts[1] if len(parts) == 2 else None

        if not ext or ext not in ('crt', 'key', 'p12'):
            mesg = 'importFile only supports .crt, .key, .p12 extensions'
            raise s_exc.BadFileExt(mesg=mesg, ext=ext)

        newpath = s_common.genpath(self.certdirs[0], mode, fname)
        if os.path.isfile(newpath):
            raise s_exc.FileExists(mesg=f'File {newpath} already exists', path=path)

        s_common.gendir(os.path.dirname(newpath))

        shutil.copy(path, newpath)
        if outp is not None:
            outp.printf('copied %s to %s' % (path, newpath))

    def isCaCert(self, name: str) -> bool:
        '''
        Checks if a CA certificate exists.

        Args:
            name: The name of the CA keypair.

        Examples:
            Check if the CA certificate for "myca" exists::

                exists = cdir.isCaCert('myca')

        Returns:
            True if the certificate is present, False otherwise.
        '''
        return self.getCaCertPath(name) is not None

    def isClientCert(self, name: str) -> bool:
        '''
        Checks if a user client certificate (PKCS12) exists.

        Args:
            name: The name of the user keypair.

        Examples:
            Check if the client certificate "myuser" exists::

                exists = cdir.isClientCert('myuser')

        Returns:
            True if the certificate is present, False otherwise.
        '''
        crtpath = self._getPathJoin('users', '%s.p12' % name)
        return os.path.isfile(crtpath)

    def isHostCert(self, name: str) -> bool:
        '''
        Checks if a host certificate exists.

        Args:
            name: The name of the host keypair.

        Examples:
            Check if the host cert "myhost" exists::

                exists = cdir.isUserCert('myhost')

        Returns:
            True if the certificate is present, False otherwise.
        '''
        return self.getHostCertPath(name) is not None

    def isUserCert(self, name: str) -> bool:
        '''
        Checks if a user certificate exists.

        Args:
            name: The name of the user keypair.

        Examples:
            Check if the user cert "myuser" exists::

                exists = cdir.isUserCert('myuser')

        Returns:
            True if the certificate is present, False otherwise.
        '''
        return self.getUserCertPath(name) is not None

    def isCodeCert(self, name: str) -> bool:
        '''
        Checks if a code certificate exists.

        Args:
            name: The name of the code keypair.

        Examples:
            Check if the code cert "mypipeline" exists::

                exists = cdir.isCodeCert('mypipeline')

        Returns:
            True if the certificate is present, False otherwise.
        '''
        return self.getCodeCert(name) is not None

    def signCertAs(self, builder: c_x509.CertificateBuilder, signas: str) -> c_x509.Certificate:
        '''
        Signs a certificate with a CA keypair.

        Args:
            cert: The certificate to sign.
            signas: The CA keypair name to sign the new keypair with.

        Examples:
            Sign a certificate with the CA "myca"::

                cdir.signCertAs(mycert, 'myca')

        Returns:
            None
        '''
        cakey = self.getCaKey(signas)
        if cakey is None:
            raise s_exc.NoCertKey(mesg=f'Missing .key for {signas}')
        cacert = self.getCaCert(signas)
        if cacert is None:
            raise s_exc.NoCertKey(mesg=f'Missing .crt for {signas}')

        attr = cacert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value

        builder = builder.issuer_name(c_x509.Name([
            c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name),
        ]))
        certificate = builder.sign(
            private_key=cakey, algorithm=self.signing_digest(),
        )
        return certificate

    def signHostCsr(self, xcsr: c_x509.CertificateSigningRequest,
                    signas: str,
                    outp: OutPutOrNone = None,
                    sans: StrOrNone = None,
                    save: bool = True) -> PkeyOrNoneAndCert:
        '''
        Signs a host CSR with a CA keypair.

        Args:
            xcsr: The certificate signing request.
            signas: The CA keypair name to sign the CSR with.
            outp: The output buffer.
            sans: List of subject alternative names.

        Examples:
            Sign a host key with the CA "myca"::

                cdir.signHostCsr(mycsr, 'myca')

        Returns:
            Tuple containing the public key and certificate objects.
        '''
        pkey = xcsr.public_key()
        attr = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        return self.genHostCert(name, csr=pkey, signas=signas, outp=outp, sans=sans, save=save)

    def selfSignCert(self, builder: c_x509.CertificateBuilder, pkey: Pkey) -> c_x509.Certificate:
        '''
        Self-sign a certificate.

        Args:
            cert: The certificate to sign.
            pkey: The PKey with which to sign the certificate.

        Examples:
            Sign a given certificate with a given private key::

                cdir.selfSignCert(mycert, myotherprivatekey)

        Returns:
            None
        '''
        attr = builder._subject_name.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        builder = builder.issuer_name(c_x509.Name([
            c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name),
        ]))
        certificate = builder.sign(
            private_key=pkey, algorithm=self.signing_digest(),
        )
        return certificate

    def signUserCsr(self, xcsr: c_x509.CertificateSigningRequest,
                    signas: str,
                    outp: OutPutOrNone = None,
                    save: bool = True) -> PkeyOrNoneAndCert:
        '''
        Signs a user CSR with a CA keypair.

        Args:
            xcsr: The certificate signing request.
            signas: The CA keypair name to sign the CSR with.
            outp: The output buffer.

        Examples:

            Sign a user CSR with "myca"::

                cdir.signUserCsr(mycsr, 'myca')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the public key and certificate objects.
        '''
        pkey = xcsr.public_key()
        name = xcsr.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = name.value
        return self.genUserCert(name, csr=pkey, signas=signas, outp=outp, save=save)

    def _loadCasIntoSSLContext(self, ctx):

        for cdir in self.certdirs:

            path = s_common.genpath(cdir, 'cas')
            if not os.path.isdir(path):
                continue

            for name in os.listdir(path):
                if name.endswith('.crt'):
                    ctx.load_verify_locations(os.path.join(path, name))

    def getClientSSLContext(self, certname: StrOrNone = None) -> ssl.SSLContext:
        '''
        Returns an ssl.SSLContext appropriate for initiating a TLS session

        Args:
            certname:   If specified, use the user certificate with the matching
                        name to authenticate to the remote service.
        Returns:
             A SSLContext object.
        '''
        sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        sslctx.minimum_version = ssl.TLSVersion.TLSv1_2
        self._loadCasIntoSSLContext(sslctx)

        if certname is not None:

            username = certname
            if username.find('@') != -1:
                user, host = username.split('@', 1)
                username = self.getUserForHost(user, host)

            if username is None:
                mesg = f'User certificate not found: {certname}'
                raise s_exc.NoSuchCert(mesg=mesg)

            certpath = self.getUserCertPath(username)
            if certpath is None:
                mesg = f'User certificate not found: {certname}'
                raise s_exc.NoSuchCert(mesg=mesg)

            keypath = self.getUserKeyPath(username)
            if keypath is None:
                mesg = f'User private key not found: {certname}'
                raise s_exc.NoCertKey(mesg=mesg)

            sslctx.load_cert_chain(certpath, keypath)

        return sslctx

    def getServerSSLContext(self, hostname: StrOrNone = None, caname: StrOrNone = None) -> ssl.SSLContext:
        '''
        Returns an ssl.SSLContext appropriate to listen on a socket

        Args:

            hostname:  If None, the value from socket.gethostname is used to find the key in the servers directory.
                       This name should match the not-suffixed part of two files ending in .key and .crt in the hosts
                       subdirectory.

            caname: If not None, the given name is used to locate a CA certificate used to validate client SSL certs.

        Returns:
            A SSLContext object.
        '''
        if hostname is not None and hostname.find(',') != -1:
            # multi-hostname SNI routing has been requested
            ctxs = {}
            names = hostname.split(',')
            for name in names:
                ctxs[name] = self._getServerSSLContext(name, caname=caname)

            def snifunc(sslsock, sslname, origctx):
                sslsock.context = ctxs.get(sslname, origctx)
                return None

            sslctx = ctxs.get(names[0])
            sslctx.sni_callback = snifunc
            return sslctx

        return self._getServerSSLContext(hostname=hostname, caname=caname)

    def getCrlPath(self, name: str) -> StrOrNone:
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'crls', '%s.crl' % name)
            if os.path.isfile(path):
                return path

    def genCrlPath(self, name: str) -> str:
        path = self.getCrlPath(name)
        if path is None:
            s_common.gendir(self.certdirs[0], 'crls')
            path = os.path.join(self.certdirs[0], 'crls', f'{name}.crl')
        return path

    def genCaCrl(self, name: str) -> Crl:
        '''
        Get the CRL for a given CA.

        Args:
            name: The CA name.

        Returns:
            The CRL object.
        '''
        return Crl(self, name)

    def _getServerSSLContext(self, hostname=None, caname=None) -> ssl.SSLContext:
        sslctx = getServerSSLContext()

        if hostname is None:
            hostname = socket.gethostname()

        certfile = self.getHostCertPath(hostname)
        if certfile is None:
            mesg = f'Missing TLS certificate file for host: {hostname}'
            raise s_exc.NoCertKey(mesg=mesg)

        keyfile = self.getHostKeyPath(hostname)
        if keyfile is None:
            mesg = f'Missing TLS key file for host: {hostname}'
            raise s_exc.NoCertKey(mesg=mesg)

        sslctx.load_cert_chain(certfile, keyfile)

        if caname is not None:
            cafile = self.getCaCertPath(caname)
            if cafile is None:
                mesg = f'Missing CA Certificate for {caname}'
                raise s_exc.NoSuchCert(mesg=mesg)
            sslctx.verify_mode = ssl.VerifyMode.CERT_REQUIRED
            sslctx.load_verify_locations(cafile=cafile)

        return sslctx

    def saveCertPem(self, cert: c_x509.Certificate, path: str) -> None:
        '''
        Save a certificate in PEM format to a file outside the certdir.
        '''
        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(cert.public_bytes(c_serialization.Encoding.PEM))

    def savePkeyPem(self, pkey: c_types.PrivateKeyTypes, path: str) -> None:
        '''
        Save a private key in PEM format to a file outside the certdir.
        '''
        byts = pkey.private_bytes(encoding=c_serialization.Encoding.PEM,
                                  format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                                  encryption_algorithm=c_serialization.NoEncryption(),
                                  )
        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(byts)

    def saveCaCertByts(self, byts: bytes) -> str:
        cert = self._loadCertByts(byts)
        attr = cert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        return self._saveCertTo(cert, 'cas', f'{name}.crt')

    def saveHostCertByts(self, byts: bytes) -> str:
        cert = self._loadCertByts(byts)
        attr = cert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        return self._saveCertTo(cert, 'hosts', f'{name}.crt')

    def saveUserCertByts(self, byts: bytes) -> str:
        cert = self._loadCertByts(byts)
        attr = cert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        return self._saveCertTo(cert, 'users', f'{name}.crt')

    def saveCodeCertBytes(self, byts: bytes) -> str:
        cert = self._loadCertByts(byts)
        attr = cert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        name = attr.value
        return self._saveCertTo(cert, 'code', f'{name}.crt')

    def _checkDupFile(self, path) -> None:
        if os.path.isfile(path):
            raise s_exc.DupFileName(mesg=f'Duplicate file {path}', path=path)

    def _genPrivKey(self) -> c_rsa.RSAPrivateKey:
        return c_rsa.generate_private_key(65537, self.crypto_numbits)

    def _genCertBuilder(self, name: str, pubkey: c_types.PublicKeyTypes) -> c_x509.CertificateBuilder:

        if not 1 <= len(name.encode('utf-8')) <= 64:
            mesg = f'Certificate name values must be between 1-64 bytes when utf8-encoded. got name={name}, len={len(name.encode("utf-8"))}'
            raise s_exc.CryptoErr(mesg=mesg)

        builder = c_x509.CertificateBuilder()
        builder = builder.subject_name(c_x509.Name([
            c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name),
        ]))

        now = datetime.datetime.now(datetime.UTC)
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + TEN_YEARS_TD)  # certificates are good for 10 years
        builder = builder.serial_number(int(s_common.guid(), 16))
        builder = builder.public_key(pubkey)
        return builder

    def _genPkeyCsr(self, name: str, mode: str, outp: OutPutOrNone = None) -> bytes:

        if not 1 <= len(name.encode('utf-8')) <= 64:
            mesg = f'CSR name values must be between 1-64 bytes when utf8-encoded. got name={name}, len={len(name.encode("utf-8"))}'
            raise s_exc.CryptoErr(mesg=mesg)

        pkey = self._genPrivKey()

        builder = c_x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(c_x509.Name([c_x509.NameAttribute(c_x509.NameOID.COMMON_NAME, name), ]))
        builder = builder.add_extension(c_x509.BasicConstraints(ca=False, path_length=None), critical=True)
        request = builder.sign(pkey, c_hashes.SHA256())

        keypath = self._savePkeyTo(pkey, mode, '%s.key' % name)
        if outp is not None:
            outp.printf('key saved: %s' % (keypath,))

        csrpath = self._getPathJoin(mode, '%s.csr' % name)
        self._checkDupFile(csrpath)
        byts = request.public_bytes(c_serialization.Encoding.PEM)

        with s_common.genfile(csrpath) as fd:
            fd.truncate(0)
            fd.write(byts)

        if outp is not None:
            outp.printf('csr saved: %s' % (csrpath,))

        return byts

    def _getCaPath(self, cert: c_x509.Certificate) -> StrOrNone:
        issuer = cert.issuer.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0]
        return self.getCaCertPath(issuer.value)

    def _getPathBytes(self, path: str) -> BytesOrNone:
        if path is None:
            return None
        return s_common.getbytes(path)

    #
    def _getPathJoin(self, *paths: str) -> str:
        '''Get the base certdir path + paths'''
        return s_common.genpath(self.certdirs[0], *paths)

    def _loadCertPath(self, path: str) -> CertOrNone:
        byts = self._getPathBytes(path)
        if byts:
            return self._loadCertByts(byts)

    def loadCertByts(self, byts: bytes) -> c_x509.Certificate:
        '''
        Load a X509 certificate from its PEM encoded bytes.

        Args:
            byts: The PEM encoded bytes of the certificate.

        Returns:
            The X509 certificate.

        Raises:
            BadCertBytes: If the certificate bytes are invalid.
        '''
        return self._loadCertByts(byts)

    def _loadCertByts(self, byts: bytes) -> c_x509.Certificate:
        try:
            return c_x509.load_pem_x509_certificate(byts)
        except Exception as e:
            raise s_exc.BadCertBytes(mesg=f'Failed to load bytes: {e}') from None

    def _loadCsrPath(self, path: str) -> Union[c_x509.CertificateSigningRequest | None]:
        byts = self._getPathBytes(path)
        if byts:
            return self._loadCsrByts(byts)

    def _loadCsrByts(self, byts: bytes) -> c_x509.CertificateSigningRequest:
        return c_x509.load_pem_x509_csr(byts)

    def _loadKeyPath(self, path: str) -> PkeyOrNone:
        byts = self._getPathBytes(path)
        if byts:
            pkey = c_serialization.load_pem_private_key(byts, password=None)
            if isinstance(pkey, (c_rsa.RSAPrivateKey, c_dsa.DSAPrivateKey)):
                return pkey
            raise s_exc.BadCertBytes(mesg=f'Key is {pkey.__class__.__name__}, expected a DSA or RSA key, {path=}',
                                     path=path)

    def _loadP12Path(self, path: str) -> Pkcs12OrNone:
        byts = self._getPathBytes(path)
        if byts:
            p12 = c_pkcs12.load_pkcs12(byts, password=None)
            return p12

    def _saveCertTo(self, cert: c_x509.Certificate, *paths: str) -> str:
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(self._certToByts(cert))

        return path

    def _certToByts(self, cert: c_x509.Certificate):
        return cert.public_bytes(encoding=c_serialization.Encoding.PEM)

    def _pkeyToByts(self, pkey: Pkey) -> bytes:
        return pkey.private_bytes(encoding=c_serialization.Encoding.PEM,
                                  format=c_serialization.PrivateFormat.TraditionalOpenSSL,
                                  encryption_algorithm=c_serialization.NoEncryption(),
                                  )

    def _savePkeyTo(self, pkey: Pkey, *paths: str):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(self._pkeyToByts(pkey))

        return path

    def _saveP12To(self, byts: bytes, *paths: str):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(byts)

        return path

certdir = CertDir()

def getCertDir() -> CertDir:
    '''
    Get the singleton CertDir instance.

    Returns:
        CertDir: A certdir object.
    '''
    return certdir

def addCertPath(path):
    return certdir.addCertPath(path)

def delCertPath(path):
    return certdir.delCertPath(path)

def getCertDirn() -> str:
    '''
    Get the expanded default path used by the singleton CertDir instance.

    Returns:
        str: The path string.
    '''
    return s_common.genpath(defdir)
