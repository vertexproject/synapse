import os
import ssl
import shutil
import socket

from OpenSSL import crypto  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common

defdir = os.getenv('SYN_CERT_DIR')
if defdir is None:
    defdir = '~/.syn/certs'

def iterFqdnUp(fqdn):
    levs = fqdn.split('.')
    for i in range(len(levs)):
        yield '.'.join(levs[i:])

TEN_YEARS = 10 * 365 * 24 * 60 * 60

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
        * All certificates will be loaded from and written to ~/.syn/certs by default. Set the envvar SYN_CERT_DIR to
          override.
        * All certificate generation methods create 4096 bit RSA keypairs.
        * All certificate signing methods use sha256 as the signature algorithm.
        * CertDir does not currently support signing CA CSRs.
    '''

    def __init__(self, path=None):
        self.crypto_numbits = 4096
        self.signing_digest = 'sha256'

        if path is None:
            path = defdir

        s_common.gendir(path, 'cas')
        s_common.gendir(path, 'hosts')
        s_common.gendir(path, 'users')

        self.certdir = s_common.reqdir(path)
        self.path = path

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

    def genHostCert(self, name, signas=None, outp=None, csr=None, sans=None):
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
            None
        '''
        return self._genPkeyCsr(name, 'hosts', outp=outp)

    def genUserCert(self, name, signas=None, outp=None, csr=None):
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

        crtpath = self._saveCertTo(cert, 'users', '%s.crt' % name)
        if outp is not None:
            outp.printf('cert saved: %s' % (crtpath,))

        if not pkey._only_public:
            keypath = self._savePkeyTo(pkey, 'users', '%s.key' % name)
            if outp is not None:
                outp.printf('key saved: %s' % (keypath,))

        return pkey, cert

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
            raise s_exc.NoSuchFile('missing User cert')

        cacert = self._loadCertPath(self._getCaPath(ucert))
        if not cacert:
            raise s_exc.NoSuchFile('missing CA cert')

        ukey = self.getUserKey(name)
        if not ukey:
            raise s_exc.NoSuchFile('missing User private key')

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
            OpenSSL.crypto.X509StoreContextError: If the certificate is not valid.

        Returns:
            OpenSSL.crypto.X509: The certificate, if it is valid.

        '''
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, byts)

        if cacerts is None:
            cacerts = self.getCaCerts()

        store = crypto.X509Store()
        [store.add_cert(cacert) for cacert in cacerts]

        ctx = crypto.X509StoreContext(store, cert)
        ctx.verify_certificate()  # raises X509StoreContextError if unable to verify
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
            None
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

    def getCaCerts(self):
        '''
        Return a list of CA certs from the CertDir.

        Returns:
            [OpenSSL.crypto.X509]: List of CA certificates.
        '''
        retn = []

        path = s_common.genpath(self.certdir, 'cas')

        for name in os.listdir(path):
            if not name.endswith('.crt'):
                continue

            full = s_common.genpath(self.certdir, 'cas', name)
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
        path = s_common.genpath(self.certdir, 'cas', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'cas', '%s.key' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'users', '%s.p12' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'hosts', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'hosts', '%s.key' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'users', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
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
        path = s_common.genpath(self.certdir, 'users', '%s.key' % name)
        if not os.path.isfile(path):
            return None
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
            raise s_exc.NoSuchFile('File does not exist')

        fname = os.path.split(path)[1]
        parts = fname.rsplit('.', 1)
        ext = parts[1] if len(parts) == 2 else None

        if not ext or ext not in ('crt', 'key', 'p12'):
            mesg = 'importFile only supports .crt, .key, .p12 extensions'
            raise s_exc.BadFileExt(mesg=mesg, ext=ext)

        newpath = s_common.genpath(self.certdir, mode, fname)
        if os.path.isfile(newpath):
            raise s_exc.FileExists('File already exists')

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
        crtpath = self._getPathJoin('cas', '%s.crt' % name)
        return os.path.isfile(crtpath)

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
        crtpath = self._getPathJoin('hosts', '%s.crt' % name)
        return os.path.isfile(crtpath)

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
        crtpath = self._getPathJoin('users', '%s.crt' % name)
        return os.path.isfile(crtpath)

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
            raise s_exc.NoCertKey('Missing .key for %s' % signas)
        cacert = self.getCaCert(signas)
        if cacert is None:
            raise s_exc.NoCertKey('Missing .crt for %s' % signas)

        cert.set_issuer(cacert.get_subject())
        cert.sign(cakey, self.signing_digest)

    def signHostCsr(self, xcsr, signas, outp=None, sans=None):
        '''
        Signs a host CSR with a CA keypair.

        Args:
            cert (OpenSSL.crypto.X509Req): The certificate signing request.
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
        return self.genHostCert(name, csr=pkey, signas=signas, outp=outp, sans=sans)

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

    def signUserCsr(self, xcsr, signas, outp=None):
        '''
        Signs a user CSR with a CA keypair.

        Args:
            cert (OpenSSL.crypto.X509Req): The certificate signing request.
            signas (str): The CA keypair name to sign the CSR with.
            outp (synapse.lib.output.Output): The output buffer.

        Examples:
            cdir.signUserCsr(mycsr, 'myca')

        Returns:
            ((OpenSSL.crypto.PKey, OpenSSL.crypto.X509)): Tuple containing the public key and certificate objects.
        '''
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genUserCert(name, csr=pkey, signas=signas, outp=outp)

    def _loadCasIntoSSLContext(self, ctx):
        path = s_common.genpath(self.certdir, 'cas')
        for name in os.listdir(path):
            if name.endswith('.crt'):
                ctx.load_verify_locations(os.path.join(path, name))

    def getClientSSLContext(self):
        '''
        Returns an ssl.SSLContext appropriate for initiating a TLS session
        '''
        sslctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self._loadCasIntoSSLContext(sslctx)

        return sslctx

    def getServerSSLContext(self, hostname=None):
        '''
        Returns an ssl.SSLContext appropriate to listen on a socket

        Args:
            hostname:  if None, the value from socket.gethostname is used to find the key in the servers directory.
            This name should match the not-suffixed part of two files ending in .key and .crt in the hosts subdirectory

        '''
        sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        if hostname is None:
            hostname = socket.gethostname()
        certfile = self.getHostCertPath(hostname)
        if certfile is None:
            raise s_exc.NoCertKey('Missing .crt for %s' % hostname)
        keyfile = self.getHostKeyPath(hostname)
        if keyfile is None:
            raise s_exc.NoCertKey('Missing .key for %s' % hostname)

        sslctx.load_cert_chain(certfile, keyfile)

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

    def _checkDupFile(self, path):
        if os.path.isfile(path):
            raise s_exc.DupFileName(path=path)

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

        with s_common.genfile(csrpath) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr))

        if outp is not None:
            outp.printf('csr saved: %s' % (csrpath,))

    def _getCaPath(self, cert):

        subj = cert.get_issuer()
        capath = self._getPathJoin('cas', '%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def _getPathBytes(self, path):
        if path is None:
            return None
        return s_common.getbytes(path)

    def _getPathJoin(self, *paths):
        return s_common.genpath(self.certdir, *paths)

    def _loadCertPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return crypto.load_certificate(crypto.FILETYPE_PEM, byts)

    def _loadCsrPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return crypto.load_certificate_request(crypto.FILETYPE_PEM, byts)

    def _loadKeyPath(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

    def _loadP12Path(self, path):
        byts = self._getPathBytes(path)
        if byts:
            return crypto.load_pkcs12(byts)

    def _saveCertTo(self, cert, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        return path

    def _savePkeyTo(self, pkey, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))

        return path

    def _saveP12To(self, cert, *paths):
        path = self._getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.truncate(0)
            fd.write(cert.export())

        return path
