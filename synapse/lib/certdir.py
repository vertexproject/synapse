import io
import os
import ssl
import time
import shutil
import socket
import logging
import collections

from OpenSSL import crypto  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.crypto.rsa as s_rsa

defdir_default = '~/.syn/certs'
defdir = os.getenv('SYN_CERT_DIR')
if defdir is None:
    defdir = defdir_default

logger = logging.getLogger(__name__)

TEN_YEARS = 10 * 365 * 24 * 60 * 60


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
        if cipher.get('kea') == 'kx-rsa':   # pragma: no cover
            continue
        _ciphers.append(cipher)

    if len(_ciphers) == 0:  # pragma: no cover
        raise s_exc.SynErr(mesg='No valid TLS ciphers are available for this Python installation.')

    ciphers = ':'.join([c.get('name') for c in _ciphers])

    return ciphers

TLS_SERVER_CIPHERS = _initTLSServerCiphers()

# openssl X509_V_FLAG_PARTIAL_CHAIN flag. This allows a context to treat all loaded
# certificates as trust anchors when doing verification.
_X509_PARTIAL_CHAIN = 0x80000

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

class CRL:

    def __init__(self, certdir, name):

        self.name = name
        self.certdir = certdir
        self.path = certdir.genCrlPath(name)

        if os.path.isfile(self.path):
            with io.open(self.path, 'rb') as fd:
                self.opensslcrl = crypto.load_crl(crypto.FILETYPE_PEM, fd.read())

        else:
            self.opensslcrl = crypto.CRL()

    def revoke(self, cert):
        '''
        Revoke a certificate with the CRL.

        Args:
            cert (cryto.X509): The certificate to revoke.

        Returns:
            None
        '''
        try:
            self._verify(cert)
        except s_exc.BadCertVerify as e:
            raise s_exc.BadCertVerify(mesg=f'Failed to validate that certificate was signed by {self.name}') from e
        timestamp = time.strftime('%Y%m%d%H%M%SZ').encode()
        revoked = crypto.Revoked()
        revoked.set_reason(None)
        revoked.set_rev_date(timestamp)
        revoked.set_serial(b'%x' % cert.get_serial_number())

        self.opensslcrl.add_revoked(revoked)
        self._save(timestamp)

    def _verify(self, cert):
        # Verify the cert was signed by the CA in self.name
        cacert = self.certdir.getCaCert(self.name)
        store = crypto.X509Store()
        store.add_cert(cacert)
        store.set_flags(_X509_PARTIAL_CHAIN)
        ctx = crypto.X509StoreContext(store, cert,)
        try:
            ctx.verify_certificate()
        except crypto.X509StoreContextError as e:
            raise s_exc.BadCertVerify(mesg=_unpackContextError(e)) from None

    def _save(self, timestamp=None):

        if timestamp is None:
            timestamp = time.strftime('%Y%m%d%H%M%SZ').encode()

        pkey = self.certdir.getCaKey(self.name)
        cert = self.certdir.getCaCert(self.name)

        self.opensslcrl.set_lastUpdate(timestamp)
        self.opensslcrl.sign(cert, pkey, b'sha256')

        with s_common.genfile(self.path) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_crl(crypto.FILETYPE_PEM, self.opensslcrl))

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

    def __init__(self, path=None):
        self.crypto_numbits = 4096
        self.signing_digest = 'sha256'

        self.certdirs = []
        self.pathrefs = collections.defaultdict(int)

        if path is None:
            path = (defdir,)

        if not isinstance(path, (list, tuple)):
            path = (path,)

        for p in path:
            self.addCertPath(p)

    def addCertPath(self, *path):

        fullpath = s_common.genpath(*path)
        self.pathrefs[fullpath] += 1

        if self.pathrefs[fullpath] == 1:
            self.certdirs.append(fullpath)

    def delCertPath(self, *path):
        fullpath = s_common.genpath(*path)
        self.pathrefs[fullpath] -= 1
        if self.pathrefs[fullpath] <= 0:
            self.certdirs.remove(fullpath)
            self.pathrefs.pop(fullpath, None)

    def genCaCert(self, name, signas=None, outp=None, save=True):
        '''
        Generates a CA keypair.

        Args:
            name (str): The name of the CA keypair.
            signas (str): The CA keypair to sign the new CA with.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            Make a CA named "myca":

                mycakey, mycacert = cdir.genCaCert('myca')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the private key and certificate objects.
        '''
        pkey, cert = self._genBasePkeyCert(name)
        ext0 = crypto.X509Extension(b'basicConstraints', False, b'CA:TRUE')
        cert.add_extensions([ext0])

        if signas is not None:
            self.signCertAs(cert, signas)
        else:
            self.selfSignCert(cert, pkey)

        if save:

            keypath = self._savePkeyTo(pkey, 'cas', '%s.key' % name)
            if outp is not None:
                outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'cas', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return pkey, cert

    def genHostCert(self, name, signas=None, outp=None, csr=None, sans=None, save=True):
        '''
        Generates a host keypair.

        Args:
            name (str): The name of the host keypair.
            signas (str): The CA keypair to sign the new host keypair with.
            outp (synapse.lib.output.Output): The output buffer.
            csr (OpenSSL.crypto.PKey): The CSR public key when generating the keypair from a CSR.
            sans (list): List of subject alternative names.

        Examples:
            Make a host keypair named "myhost":

                myhostkey, myhostcert = cdir.genHostCert('myhost')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the private key and certificate objects.
        '''
        pkey, cert = self._genBasePkeyCert(name, pkey=csr)

        ext_sans = {'DNS:' + name}
        if isinstance(sans, str):
            ext_sans = ext_sans.union(sans.split(','))
        ext_sans = ','.join(sorted(ext_sans))

        cert.add_extensions([
            crypto.X509Extension(b'nsCertType', False, b'server'),
            crypto.X509Extension(b'keyUsage', False, b'digitalSignature,keyEncipherment'),
            crypto.X509Extension(b'extendedKeyUsage', False, b'serverAuth'),
            crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
            crypto.X509Extension(b'subjectAltName', False, ext_sans.encode('utf-8')),
        ])

        if signas is not None:
            self.signCertAs(cert, signas)
        else:
            self.selfSignCert(cert, pkey)

        if save:
            if not pkey._only_public:
                keypath = self._savePkeyTo(pkey, 'hosts', '%s.key' % name)
                if outp is not None:
                    outp.printf('key saved: %s' % (keypath,))

            crtpath = self._saveCertTo(cert, 'hosts', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

        return pkey, cert

    def genHostCsr(self, name, outp=None):
        '''
        Generates a host certificate signing request.

        Args:
            name (str): The name of the host CSR.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            Generate a CSR for the host key named "myhost":

                cdir.genHostCsr('myhost')

        Returns:
            bytes: The bytes of the CSR.
        '''
        return self._genPkeyCsr(name, 'hosts', outp=outp)

    def genUserCert(self, name, signas=None, outp=None, csr=None, save=True):
        '''
        Generates a user keypair.

        Args:
            name (str): The name of the user keypair.
            signas (str): The CA keypair to sign the new user keypair with.
            outp (synapse.lib.output.Output): The output buffer.
            csr (OpenSSL.crypto.PKey): The CSR public key when generating the keypair from a CSR.

        Examples:
            Generate a user cert for the user "myuser":

                myuserkey, myusercert = cdir.genUserCert('myuser')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the key and certificate objects.
        '''
        pkey, cert = self._genBasePkeyCert(name, pkey=csr)

        cert.add_extensions([
            crypto.X509Extension(b'nsCertType', False, b'client'),
            crypto.X509Extension(b'keyUsage', False, b'digitalSignature'),
            crypto.X509Extension(b'extendedKeyUsage', False, b'clientAuth'),
            crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
        ])

        if signas is not None:
            self.signCertAs(cert, signas)
        else:
            self.selfSignCert(cert, pkey)

        if save:
            crtpath = self._saveCertTo(cert, 'users', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

            if not pkey._only_public:
                keypath = self._savePkeyTo(pkey, 'users', '%s.key' % name)
                if outp is not None:
                    outp.printf('key saved: %s' % (keypath,))

        return pkey, cert

    def genCodeCert(self, name, signas=None, outp=None, save=True):
        '''
        Generates a code signing keypair.

        Args:
            name (str): The name of the code signing cert.
            signas (str): The CA keypair to sign the new code keypair with.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:

            Generate a code signing cert for the name "The Vertex Project":

                myuserkey, myusercert = cdir.genCodeCert('The Vertex Project')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the key and certificate objects.
        '''
        pkey, cert = self._genBasePkeyCert(name)

        cert.add_extensions([
            crypto.X509Extension(b'nsCertType', False, b'objsign'),
            crypto.X509Extension(b'keyUsage', False, b'digitalSignature'),
            crypto.X509Extension(b'extendedKeyUsage', False, b'codeSigning'),
            crypto.X509Extension(b'basicConstraints', False, b'CA:FALSE'),
        ])

        if signas is not None:
            self.signCertAs(cert, signas)

        if save:
            crtpath = self._saveCertTo(cert, 'code', '%s.crt' % name)
            if outp is not None:
                outp.printf('cert saved: %s' % (crtpath,))

            if not pkey._only_public:
                keypath = self._savePkeyTo(pkey, 'code', '%s.key' % name)
                if outp is not None:
                    outp.printf('key saved: %s' % (keypath,))

        return pkey, cert

    def getCodeKeyPath(self, name):
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'code', f'{name}.key')
            if os.path.isfile(path):
                return path

    def getCodeCertPath(self, name):
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'code', f'{name}.crt')
            if os.path.isfile(path):
                return path

    def getCodeKey(self, name):

        path = self.getCodeKeyPath(name)
        if path is None:
            return None

        pkey = self._loadKeyPath(path)
        return s_rsa.PriKey(pkey.to_cryptography_key())

    def getCodeCert(self, name):

        path = self.getCodeCertPath(name)
        if path is None: # pragma: no cover
            return None

        return self._loadCertPath(path)

    def _getCertExt(self, cert, name):
        for i in range(cert.get_extension_count()):
            ext = cert.get_extension(i)
            if ext.get_short_name() == name:
                return ext.get_data()

    def valCodeCert(self, byts):
        '''
        Verify a code cert is valid according to certdir's available CAs and CRLs.

        Args:
            byts (bytes): The certificate bytes.

        Returns:
            OpenSSL.crypto.X509: The certificate.
        '''

        reqext = crypto.X509Extension(b'extendedKeyUsage', False, b'codeSigning')

        cert = self.loadCertByts(byts)
        if self._getCertExt(cert, b'extendedKeyUsage') != reqext.get_data():
            mesg = 'Certificate is not for code signing.'
            raise s_exc.BadCertBytes(mesg=mesg)

        crls = self._getCaCrls()
        cacerts = self.getCaCerts()

        store = crypto.X509Store()
        [store.add_cert(cacert) for cacert in cacerts]

        if crls:

            store.set_flags(crypto.X509StoreFlags.CRL_CHECK | crypto.X509StoreFlags.CRL_CHECK_ALL)

            [store.add_crl(crl) for crl in crls]

        ctx = crypto.X509StoreContext(store, cert)
        try:
            ctx.verify_certificate()  # raises X509StoreContextError if unable to verify
        except crypto.X509StoreContextError as e:
            mesg = _unpackContextError(e)
            raise s_exc.BadCertVerify(mesg=mesg)
        return cert

    def _getCaCrls(self):

        crls = []
        for cdir in self.certdirs:

            crlpath = os.path.join(cdir, 'crls')
            if not os.path.isdir(crlpath):
                continue

            for name in os.listdir(crlpath):

                if not name.endswith('.crl'): # pragma: no cover
                    continue

                fullpath = os.path.join(crlpath, name)
                with io.open(fullpath, 'rb') as fd:
                    crls.append(crypto.load_crl(crypto.FILETYPE_PEM, fd.read()))

        return crls

    def genClientCert(self, name, outp=None):
        '''
        Generates a user PKCS #12 archive.
        Please note that the resulting file will contain private key material.

        Args:
            name (str): The name of the user keypair.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            Make the PKC12 object for user "myuser":

                myuserpkcs12 = cdir.genClientCert('myuser')

        Returns:
            OpenSSL.crypto.PKCS12: The PKCS #12 archive.
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

        ccert = crypto.PKCS12()
        ccert.set_friendlyname(name.encode('utf-8'))
        ccert.set_ca_certificates([cacert])
        ccert.set_certificate(ucert)
        ccert.set_privatekey(ukey)

        crtpath = self._saveP12To(ccert, 'users', '%s.p12' % name)
        if outp is not None:
            outp.printf('client cert saved: %s' % (crtpath,))

    def valUserCert(self, byts, cacerts=None):
        '''
        Validate the PEM encoded x509 user certificate bytes and return it.

        Args:
            byts (bytes): The bytes for the User Certificate.
            cacerts (tuple): A tuple of OpenSSL.crypto.X509 CA Certificates.

        Raises:
            BadCertVerify: If the certificate is not valid.

        Returns:
            OpenSSL.crypto.X509: The certificate, if it is valid.
        '''
        cert = self.loadCertByts(byts)

        if cacerts is None:
            cacerts = self.getCaCerts()

        store = crypto.X509Store()
        [store.add_cert(cacert) for cacert in cacerts]

        ctx = crypto.X509StoreContext(store, cert)
        try:
            ctx.verify_certificate()
        except crypto.X509StoreContextError as e:
            raise s_exc.BadCertVerify(mesg=_unpackContextError(e))
        return cert

    def genUserCsr(self, name, outp=None):
        '''
        Generates a user certificate signing request.

        Args:
            name (str): The name of the user CSR.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            Generate a CSR for the user "myuser":

                cdir.genUserCsr('myuser')

        Returns:
            bytes: The bytes of the CSR.
        '''
        return self._genPkeyCsr(name, 'users', outp=outp)

    def getCaCert(self, name):
        '''
        Loads the X509 object for a given CA.

        Args:
            name (str): The name of the CA keypair.

        Examples:
            Get the certificate for the  CA "myca"

                mycacert = cdir.getCaCert('myca')

        Returns:
            OpenSSL.crypto.X509: The certificate, if exists.
        '''
        return self._loadCertPath(self.getCaCertPath(name))

    def getCaCertBytes(self, name):
        path = self.getCaCertPath(name)
        if os.path.exists(path):
            with open(path, 'rb') as fd:
                return fd.read()

    def getCaCerts(self):
        '''
        Return a list of CA certs from the CertDir.

        Returns:
            [OpenSSL.crypto.X509]: List of CA certificates.
        '''
        retn = []

        for cdir in self.certdirs:

            path = s_common.genpath(cdir, 'cas')
            if not os.path.isdir(path):
                continue

            for name in os.listdir(path):

                if not name.endswith('.crt'): # pragma: no cover
                    continue

                full = s_common.genpath(cdir, 'cas', name)
                retn.append(self._loadCertPath(full))

        return retn

    def getCaCertPath(self, name):
        '''
        Gets the path to a CA certificate.

        Args:
            name (str): The name of the CA keypair.

        Examples:
            Get the path to the CA certificate for the CA "myca":

                mypath = cdir.getCACertPath('myca')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'cas', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getCaKey(self, name):
        '''
        Loads the PKey object for a given CA keypair.

        Args:
            name (str): The name of the CA keypair.

        Examples:
            Get the private key for the CA "myca":

                mycakey = cdir.getCaKey('myca')

        Returns:
            OpenSSL.crypto.PKey: The private key, if exists.
        '''
        return self._loadKeyPath(self.getCaKeyPath(name))

    def getCaKeyPath(self, name):
        '''
        Gets the path to a CA key.

        Args:
            name (str): The name of the CA keypair.

        Examples:
            Get the path to the private key for the CA "myca":

                mypath = cdir.getCAKeyPath('myca')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'cas', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def getClientCert(self, name):
        '''
        Loads the PKCS12 archive object for a given user keypair.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the PKCS12 object for the user "myuser":

                mypkcs12 = cdir.getClientCert('myuser')

        Notes:
            The PKCS12 archive will contain private key material if it was created with CertDir or the easycert tool

        Returns:
            OpenSSL.crypto.PKCS12: The PKCS12 archive, if exists.
        '''
        return self._loadP12Path(self.getClientCertPath(name))

    def getClientCertPath(self, name):
        '''
        Gets the path to a client certificate.

        Args:
            name (str): The name of the client keypair.

        Examples:
            Get the path to the client certificate for "myuser":

                mypath = cdir.getClientCertPath('myuser')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.p12' % name)
            if os.path.isfile(path):
                return path

    def getHostCaPath(self, name):
        '''
        Gets the path to the CA certificate that issued a given host keypair.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Get the path to the CA cert which issue the cert for "myhost":

                mypath = cdir.getHostCaPath('myhost')

        Returns:
            str: The path if exists.
        '''
        cert = self.getHostCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getHostCert(self, name):
        '''
        Loads the X509 object for a given host keypair.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Get the certificate object for the host "myhost":

                myhostcert = cdir.getHostCert('myhost')

        Returns:
            OpenSSL.crypto.X509: The certificate, if exists.
        '''
        return self._loadCertPath(self.getHostCertPath(name))

    def getHostCertHash(self, name):
        cert = self.getHostCert(name)
        if cert is None:
            return None
        return cert.digest('SHA256').decode().lower().replace(':', '')

    def getHostCertPath(self, name):
        '''
        Gets the path to a host certificate.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Get the path to the host certificate for the host "myhost":

                mypath = cdir.getHostCertPath('myhost')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'hosts', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getHostKey(self, name):
        '''
        Loads the PKey object for a given host keypair.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Get the private key object for the host "myhost":

                myhostkey = cdir.getHostKey('myhost')

        Returns:
            OpenSSL.crypto.PKey: The private key, if exists.
        '''
        return self._loadKeyPath(self.getHostKeyPath(name))

    def getHostKeyPath(self, name):
        '''
        Gets the path to a host key.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Get the path to the host key for the host "myhost":

                mypath = cdir.getHostKeyPath('myhost')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'hosts', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def getUserCaPath(self, name):
        '''
        Gets the path to the CA certificate that issued a given user keypair.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the path to the CA cert which issue the cert for "myuser":

                mypath = cdir.getUserCaPath('myuser')

        Returns:
            str: The path if exists.
        '''
        cert = self.getUserCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getUserCert(self, name):
        '''
        Loads the X509 object for a given user keypair.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the certificate object for the user "myuser":

                myusercert = cdir.getUserCert('myuser')

        Returns:
            OpenSSL.crypto.X509: The certificate, if exists.
        '''
        return self._loadCertPath(self.getUserCertPath(name))

    def getUserCertPath(self, name):
        '''
        Gets the path to a user certificate.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the path for the user cert for "myuser":

                mypath = cdir.getUserCertPath('myuser')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.crt' % name)
            if os.path.isfile(path):
                return path

    def getUserForHost(self, user, host):
        '''
        Gets the name of the first existing user cert for a given user and host.

        Args:
            user (str): The name of the user.
            host (str): The name of the host.

        Examples:
            Get the name for the "myuser" user cert at "cool.vertex.link":

                usercertname = cdir.getUserForHost('myuser', 'cool.vertex.link')

        Returns:
            str: The cert name, if exists.
        '''
        for name in iterFqdnUp(host):
            usercert = '%s@%s' % (user, name)
            if self.isUserCert(usercert):
                return usercert

    def getUserKey(self, name):
        '''
        Loads the PKey object for a given user keypair.


        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the key object for the user key for "myuser":

                myuserkey = cdir.getUserKey('myuser')

        Returns:
            OpenSSL.crypto.PKey: The private key, if exists.
        '''
        return self._loadKeyPath(self.getUserKeyPath(name))

    def getUserKeyPath(self, name):
        '''
        Gets the path to a user key.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Get the path to the user key for "myuser":

                mypath = cdir.getUserKeyPath('myuser')

        Returns:
            str: The path if exists.
        '''
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'users', '%s.key' % name)
            if os.path.isfile(path):
                return path

    def importFile(self, path, mode, outp=None):
        '''
        Imports certs and keys into the Synapse cert directory

        Args:
            path (str): The path of the file to be imported.
            mode (str): The certdir subdirectory to import the file into.

        Examples:
            Import CA certifciate 'mycoolca.crt' to the 'cas' directory.

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

    def isCaCert(self, name):
        '''
        Checks if a CA certificate exists.

        Args:
            name (str): The name of the CA keypair.

        Examples:
            Check if the CA certificate for "myca" exists:

                exists = cdir.isCaCert('myca')

        Returns:
            bool: True if the certificate is present, False otherwise.
        '''
        return self.getCaCertPath(name) is not None

    def isClientCert(self, name):
        '''
        Checks if a user client certificate (PKCS12) exists.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Check if the client certificate "myuser" exists:

                exists = cdir.isClientCert('myuser')

        Returns:
            bool: True if the certificate is present, False otherwise.
        '''
        crtpath = self._getPathJoin('users', '%s.p12' % name)
        return os.path.isfile(crtpath)

    def isHostCert(self, name):
        '''
        Checks if a host certificate exists.

        Args:
            name (str): The name of the host keypair.

        Examples:
            Check if the host cert "myhost" exists:

                exists = cdir.isUserCert('myhost')

        Returns:
            bool: True if the certificate is present, False otherwise.
        '''
        return self.getHostCertPath(name) is not None

    def isUserCert(self, name):
        '''
        Checks if a user certificate exists.

        Args:
            name (str): The name of the user keypair.

        Examples:
            Check if the user cert "myuser" exists:

                exists = cdir.isUserCert('myuser')

        Returns:
            bool: True if the certificate is present, False otherwise.
        '''
        return self.getUserCertPath(name) is not None

    def signCertAs(self, cert, signas):
        '''
        Signs a certificate with a CA keypair.

        Args:
            cert (OpenSSL.crypto.X509): The certificate to sign.
            signas (str): The CA keypair name to sign the new keypair with.

        Examples:
            Sign a certificate with the CA "myca":

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

        cert.set_issuer(cacert.get_subject())
        cert.sign(cakey, self.signing_digest)

    def signHostCsr(self, xcsr, signas, outp=None, sans=None, save=True):
        '''
        Signs a host CSR with a CA keypair.

        Args:
            xcsr (OpenSSL.crypto.X509Req): The certificate signing request.
            signas (str): The CA keypair name to sign the CSR with.
            outp (synapse.lib.output.Output): The output buffer.
            sans (list): List of subject alternative names.

        Examples:
            Sign a host key with the CA "myca":

                cdir.signHostCsr(mycsr, 'myca')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)):  Tuple containing the public key and certificate objects.
        '''
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genHostCert(name, csr=pkey, signas=signas, outp=outp, sans=sans, save=save)

    def selfSignCert(self, cert, pkey):
        '''
        Self-sign a certificate.

        Args:
            cert (OpenSSL.crypto.X509): The certificate to sign.
            pkey (OpenSSL.crypto.PKey): The PKey with which to sign the certificate.

        Examples:
            Sign a given certificate with a given private key:

                cdir.selfSignCert(mycert, myotherprivatekey)

        Returns:
            None
        '''
        cert.set_issuer(cert.get_subject())
        cert.sign(pkey, self.signing_digest)

    def signUserCsr(self, xcsr, signas, outp=None, save=True):
        '''
        Signs a user CSR with a CA keypair.

        Args:
            xcsr (OpenSSL.crypto.X509Req): The certificate signing request.
            signas (str): The CA keypair name to sign the CSR with.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            cdir.signUserCsr(mycsr, 'myca')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the public key and certificate objects.
        '''
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genUserCert(name, csr=pkey, signas=signas, outp=outp, save=save)

    def _loadCasIntoSSLContext(self, ctx):

        for cdir in self.certdirs:

            path = s_common.genpath(cdir, 'cas')
            if not os.path.isdir(path):
                continue

            for name in os.listdir(path):
                if name.endswith('.crt'):
                    ctx.load_verify_locations(os.path.join(path, name))

    def getClientSSLContext(self, certname=None):
        '''
        Returns an ssl.SSLContext appropriate for initiating a TLS session

        Args:
            certname:   If specified, use the user certificate with the matching
                        name to authenticate to the remote service.
        Returns:
            ssl.SSLContext: A SSLContext object.
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

    def getServerSSLContext(self, hostname=None, caname=None):
        '''
        Returns an ssl.SSLContext appropriate to listen on a socket

        Args:

            hostname:  If None, the value from socket.gethostname is used to find the key in the servers directory.
                       This name should match the not-suffixed part of two files ending in .key and .crt in the hosts
                       subdirectory.

            caname: If not None, the given name is used to locate a CA certificate used to validate client SSL certs.

        Returns:
            ssl.SSLContext: A SSLContext object.
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

    def getCrlPath(self, name):
        for cdir in self.certdirs:
            path = s_common.genpath(cdir, 'crls', '%s.crl' % name)
            if os.path.isfile(path):
                return path

    def genCrlPath(self, name):
        path = self.getCrlPath(name)
        if path is None:
            s_common.gendir(self.certdirs[0], 'crls')
            path = os.path.join(self.certdirs[0], 'crls', f'{name}.crl')
        return path

    def genCaCrl(self, name):
        '''
        Get the CRL for a given CA.

        Args:
            name (str): The CA name.

        Returns:
            CRL: The CRL object.
        '''
        return CRL(self, name)

    def _getServerSSLContext(self, hostname=None, caname=None):
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
            sslctx.verify_mode = ssl.VerifyMode.CERT_REQUIRED
            sslctx.load_verify_locations(cafile=cafile)

        return sslctx

    def saveCertPem(self, cert, path):
        '''
        Save a certificate in PEM format to a file outside the certdir.
        '''
        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    def savePkeyPem(self, pkey, path):
        '''
        Save a private key in PEM format to a file outside the certdir.
        '''
        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))

    def saveCaCertByts(self, byts):
        cert = self._loadCertByts(byts)
        name = cert.get_subject().CN
        return self._saveCertTo(cert, 'cas', f'{name}.crt')

    def saveHostCertByts(self, byts):
        cert = self._loadCertByts(byts)
        name = cert.get_subject().CN
        return self._saveCertTo(cert, 'hosts', f'{name}.crt')

    def saveUserCertByts(self, byts):
        cert = self._loadCertByts(byts)
        name = cert.get_subject().CN
        return self._saveCertTo(cert, 'users', f'{name}.crt')

    def _checkDupFile(self, path):
        if os.path.isfile(path):
            raise s_exc.DupFileName(mesg=f'Duplicate file {path}', path=path)

    def _genBasePkeyCert(self, name, pkey=None):

        if pkey is None:
            pkey = crypto.PKey()
            pkey.generate_key(crypto.TYPE_RSA, self.crypto_numbits)

        cert = crypto.X509()
        cert.set_pubkey(pkey)
        cert.set_version(2)

        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(TEN_YEARS)  # Certpairs are good for 10 years

        cert.set_serial_number(int(s_common.guid(), 16))
        cert.get_subject().CN = name

        return pkey, cert

    def _genPkeyCsr(self, name, mode, outp=None):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, self.crypto_numbits)

        xcsr = crypto.X509Req()
        xcsr.get_subject().CN = name

        xcsr.set_pubkey(pkey)
        xcsr.sign(pkey, self.signing_digest)

        keypath = self._savePkeyTo(pkey, mode, '%s.key' % name)
        if outp is not None:
            outp.printf('key saved: %s' % (keypath,))

        csrpath = self._getPathJoin(mode, '%s.csr' % name)
        self._checkDupFile(csrpath)

        byts = crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr)

        with s_common.genfile(csrpath) as fd:
            fd.truncate(0)
            fd.write(byts)

        if outp is not None:
            outp.printf('csr saved: %s' % (csrpath,))

        return byts

    def _getCaPath(self, cert):
        subj = cert.get_issuer()
        return self.getCaCertPath(subj.CN)

    def _getPathBytes(self, path):
        if path is None:
            return None
        return s_common.getbytes(path)

    def _getPathJoin(self, *paths):
        return s_common.genpath(self.certdirs[0], *paths)

    def _loadCertPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return self._loadCertByts(byts)

    def loadCertByts(self, byts):
        '''
        Load a X509 certificate from its PEM encoded bytes.

        Args:
            byts (bytes): The PEM encoded bytes of the certificate.

        Returns:
            OpenSSL.crypto.X509: The X509 certificate.

        Raises:
            BadCertBytes: If the certificate bytes are invalid.
        '''
        return self._loadCertByts(byts)

    def _loadCertByts(self, byts: bytes) -> crypto.X509:
        try:
            return crypto.load_certificate(crypto.FILETYPE_PEM, byts)
        except crypto.Error as e:
            # Unwrap pyopenssl's exception_from_error_queue
            estr = ''
            for argv in e.args:
                if estr:  # pragma: no cover
                    estr += ', '
                estr += ' '.join((arg for arg in argv[0] if arg))
            raise s_exc.BadCertBytes(mesg=f'Failed to load bytes: {estr}')

    def _loadCsrPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return self._loadCsrByts(byts)

    def _loadCsrByts(self, byts):
        return crypto.load_certificate_request(crypto.FILETYPE_PEM, byts)

    def _loadKeyPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

    def _loadP12Path(self, path):
        byts = self._getPathBytes(path)
        if byts:
            # This API is deprecrated by PyOpenSSL and will need to be rewritten if pyopenssl is
            # updated from v21.x.x. The APIs that use this are not directly exposed via the
            # easycert tool currently, and are only used in unit tests.
            return crypto.load_pkcs12(byts)

    def _saveCertTo(self, cert, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(self._certToByts(cert))

        return path

    def _certToByts(self, cert):
        return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)

    def _pkeyToByts(self, pkey):
        return crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

    def _savePkeyTo(self, pkey, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(self._pkeyToByts(pkey))

        return path

    def _saveP12To(self, cert, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(cert.export())

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
