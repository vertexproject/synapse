import os

from OpenSSL import crypto

import synapse.common as s_common

defdir = os.getenv('SYN_CERT_DIR')
if defdir is None:
    defdir = '~/.syn/certs'

def iterFqdnUp(fqdn):
    levs = fqdn.split('.')
    for i in range(len(levs)):
        yield '.'.join(levs[i:])

class CertDir:

    def __init__(self, path=None):
        self.crypto_numbits = 4096

        if path is None:
            path = defdir

        s_common.gendir(path, 'cas')
        s_common.gendir(path, 'hosts')
        s_common.gendir(path, 'users')

        self.certdir = s_common.reqdir(path)

    def genCaCert(self, name, signas=None, outp=None):
        pkey, cert = self._genBasePkeyCert(name)
        ext0 = crypto.X509Extension(b'basicConstraints', False, b'CA:TRUE')
        cert.add_extensions([ext0])

        if signas is not None:
            self.signCertAs(cert, signas)
        else:
            self.selfSignCert(cert, pkey)

        keypath = self._savePkeyTo(pkey, 'cas', '%s.key' % name)
        if outp is not None:
            outp.printf('key saved: %s' % (keypath,))

        crtpath = self._saveCertTo(cert, 'cas', '%s.crt' % name)
        if outp is not None:
            outp.printf('cert saved: %s' % (crtpath,))

        return pkey, cert

    def genHostCert(self, name, signas=None, outp=None, pkey=None, sans=None):
        pkey, cert = self._genBasePkeyCert(name, pkey=pkey)

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
        return self._genPkeyCsr(name, 'hosts', outp=outp)

    def genUserCert(self, name, signas=None, outp=None, pkey=None):

        pkey, cert = self._genBasePkeyCert(name, pkey=pkey)

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

        ucert = self.getUserCert(name)
        if not ucert:
            raise s_common.NoSuchFile('missing User cert')

        cacert = self._loadCertPath(self._getCaPath(ucert))
        if not cacert:
            raise s_common.NoSuchFile('missing CA cert')

        ukey = self.getUserKey(name)
        if not ukey:
            raise s_common.NoSuchFile('missing User private key')

        ccert = crypto.PKCS12()
        ccert.set_friendlyname(name.encode('utf-8'))
        ccert.set_ca_certificates([cacert])
        ccert.set_certificate(ucert)
        ccert.set_privatekey(ukey)

        crtpath = self._saveP12To(ccert, 'users', '%s.p12' % name)
        if outp is not None:
            outp.printf('client cert saved: %s' % (crtpath,))

    def genUserCsr(self, name, outp=None):
        return self._genPkeyCsr(name, 'users', outp=outp)

    def getCaCert(self, name):
        return self._loadCertPath(self.getCaCertPath(name))

    def getCaCertPath(self, name):
        path = s_common.genpath(self.certdir, 'cas', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getCaKey(self, name):
        return self._loadKeyPath(self.getCaKeyPath(name))

    def getCaKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'cas', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getClientCert(self, name):
        '''
        Loads the PKCS12 object for a given client certificate.

        Example:
            mypkcs12 = cdir.getClientCert('mycert')

        Args:
            name (str): The name of the client certificate.

        Returns:
            OpenSSL.crypto.PKCS12: The certificate if exists.
        '''
        return self._loadP12Path(self.getClientCertPath(name))

    def getClientCertPath(self, name):
        '''
        Gets the path to a client certificate.

        Example:
            mypath = cdir.getClientCertPath('mycert')

        Args:
            name (str): The name of the client certificate.

        Returns:
            str: The path if exists.
        '''
        path = s_common.genpath(self.certdir, 'users', '%s.p12' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostCaPath(self, name):
        cert = self.getHostCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getHostCert(self, name):
        return self._loadCertPath(self.getHostCertPath(name))

    def getHostCertPath(self, name):
        path = s_common.genpath(self.certdir, 'hosts', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostKey(self, name):
        return self._loadKeyPath(self.getHostKeyPath(name))

    def getHostKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'hosts', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserCaPath(self, name):
        cert = self.getUserCert(name)
        if cert is None:
            return None

        return self._getCaPath(cert)

    def getUserCert(self, name):
        return self._loadCertPath(self.getUserCertPath(name))

    def getUserCertPath(self, name):
        path = s_common.genpath(self.certdir, 'users', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserForHost(self, user, host):
        for name in iterFqdnUp(host):
            usercert = '%s@%s' % (user, name)
            if self.isUserCert(usercert):
                return usercert

    def getUserKey(self, name):
        return self._loadKeyPath(self.getUserKeyPath(name))

    def getUserKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'users', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getPathJoin(self, *paths):
        return s_common.genpath(self.certdir, *paths)

    def isCaCert(self, name):
        crtpath = self.getPathJoin('cas', '%s.crt' % name)
        return os.path.isfile(crtpath)

    def isClientCert(self, name):
        '''
        Checks if a client certificate exists.

        Example:
            exists = cdir.isClientCert('mycert')

        Args:
            name (str): The name of the client certificate.

        Returns:
            bool: True if the certificate is present, False otherwise.
        '''
        crtpath = self.getPathJoin('users', '%s.p12' % name)
        return os.path.isfile(crtpath)

    def isHostCert(self, name):
        crtpath = self.getPathJoin('hosts', '%s.crt' % name)
        return os.path.isfile(crtpath)

    def isUserCert(self, name):
        crtpath = self.getPathJoin('users', '%s.crt' % name)
        return os.path.isfile(crtpath)

    def signCertAs(self, cert, signas):
        cakey = self.getCaKey(signas)
        cacert = self.getCaCert(signas)

        cert.set_issuer(cacert.get_subject())
        cert.sign(cakey, 'sha256')

    def signHostCsr(self, xcsr, signas, outp=None, sans=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genHostCert(name, pkey=pkey, signas=signas, outp=outp, sans=sans)

    def selfSignCert(self, cert, pkey):
        cert.set_issuer(cert.get_subject())
        cert.sign(pkey, 'sha256')

    def signUserCsr(self, xcsr, signas, outp=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genUserCert(name, pkey=pkey, signas=signas, outp=outp)

    def _checkDupFile(self, path):
        if os.path.isfile(path):
            raise s_common.DupFileName(path=path)

    def _genBasePkeyCert(self, name, pkey=None):

        if pkey is None:
            pkey = crypto.PKey()
            pkey.generate_key(crypto.TYPE_RSA, self.crypto_numbits)

        cert = crypto.X509()
        cert.set_pubkey(pkey)
        cert.set_version(2)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)

        cert.set_serial_number(int(s_common.guid(), 16))
        cert.get_subject().CN = name

        return pkey, cert

    def _genPkeyCsr(self, name, mode, outp=None):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, self.crypto_numbits)

        xcsr = crypto.X509Req()
        xcsr.get_subject().CN = name

        xcsr.set_pubkey(pkey)
        xcsr.sign(pkey, 'sha256')

        keypath = self._savePkeyTo(pkey, mode, '%s.key' % name)
        if outp is not None:
            outp.printf('key saved: %s' % (keypath,))

        csrpath = self.getPathJoin(mode, '%s.csr' % name)
        self._checkDupFile(csrpath)

        with s_common.genfile(csrpath) as fd:
            fd.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr))

        if outp is not None:
            outp.printf('csr saved: %s' % (csrpath,))

    def _getCaPath(self, cert):

        subj = cert.get_issuer()
        capath = self.getPathJoin('cas', '%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def _getPathBytes(self, path):
        if path is None:
            return None
        return s_common.getbytes(path)

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
        path = self.getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        return path

    def _savePkeyTo(self, pkey, *paths):
        path = self.getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))

        return path

    def _saveP12To(self, cert, *paths):
        path = self.getPathJoin(*paths)
        self._checkDupFile(path)

        with s_common.genfile(path) as fd:
            fd.write(cert.export())

        return path
