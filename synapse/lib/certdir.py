import os
import time

import synapse.common as s_common

from OpenSSL import crypto

defdir = os.getenv('SYN_CERT_DIR')
if defdir is None:
    defdir = '~/.syn/certs'

def iterFqdnUp(fqdn):
    levs = fqdn.split('.')
    for i in range(len(levs)):
        yield '.'.join(levs[i:])

class CertDir:

    def __init__(self, path=None):

        if path is None:
            path = defdir

        s_common.gendir(path, 'cas')
        s_common.gendir(path, 'hosts')
        s_common.gendir(path, 'users')

        self.certdir = s_common.reqdir(path)

    def getPathJoin(self, *paths):
        return s_common.genpath(self.certdir, *paths)

    def getCaCert(self, name):
        return self._loadCertPath(self.getCaCertPath(name))

    def getHostCert(self, name):
        return self._loadCertPath(self.getHostCertPath(name))

    def getUserCert(self, name):
        return self._loadCertPath(self.getUserCertPath(name))

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

    def getCaKey(self, name):
        return self._loadKeyPath(self.getCaKeyPath(name))

    def getHostKey(self, name):
        return self._loadKeyPath(self.getHostKeyPath(name))

    def getUserKey(self, name):
        return self._loadKeyPath(self.getUserKeyPath(name))

    def _loadKeyPath(self, path):
        if path is None:
            return None

        byts = s_common.getbytes(path)
        if byts is None:
            return None

        return crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

    def _loadCertPath(self, path):
        if path is None:
            return None

        byts = s_common.getbytes(path)
        if byts is None:
            return None

        return crypto.load_certificate(crypto.FILETYPE_PEM, byts)

    def _loadP12Path(self, path):
        if path is None:
            return None

        byts = s_common.getbytes(path)
        if byts is None:
            return None

        return crypto.load_pkcs12(byts)

    #def saveCaCert(self, cert):
    #def saveUserCert(self, cert):
    #def saveHostCert(self, cert):
    #def saveX509Cert(self, cert):
    #def loadX509Cert(self, path):

    def _genBasePkeyCert(self, name, pkey=None):

        if pkey is None:
            pkey = crypto.PKey()
            pkey.generate_key(crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.set_pubkey(pkey)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)

        cert.set_serial_number(int(s_common.guid(), 16))
        cert.get_subject().CN = name

        return pkey, cert

    def _saveCertTo(self, cert, *paths):
        path = self.getPathJoin(*paths)
        if os.path.isfile(path):
            raise s_common.DupFileName(path=path)

        with s_common.genfile(path) as fd:
            fd.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        return path

    def _saveP12To(self, cert, *paths):
        path = self.getPathJoin(*paths)
        if os.path.isfile(path):
            raise s_common.DupFileName(path=path)

        with s_common.genfile(path) as fd:
            fd.write(cert.export())

        return path

    def _savePkeyTo(self, pkey, *paths):
        path = self.getPathJoin(*paths)
        if os.path.isfile(path):
            raise s_common.DupFileName(path=path)

        with s_common.genfile(path) as fd:
            fd.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        return path

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

        if not pkey._only_public:
            keypath = self._savePkeyTo(pkey, 'users', '%s.key' % name)
            if outp is not None:
                outp.printf('key saved: %s' % (keypath,))

        crtpath = self._saveCertTo(cert, 'users', '%s.crt' % name)
        if outp is not None:
            outp.printf('cert saved: %s' % (crtpath,))

        ccert = crypto.PKCS12()
        ccert.set_friendlyname(name.encode('utf-8'))
        ccert.set_certificate(cert)
        ccert.set_privatekey(pkey)

        if signas:
            cacert = self.getCaCert(signas)
            ccert.set_ca_certificates([cacert])

        crtpath = self._saveP12To(ccert, 'users', '%s.p12' % name)
        if outp is not None:
            outp.printf('client cert saved: %s' % (crtpath,))

        return pkey, cert

    def _loadCsrPath(self, path):
        byts = s_common.getbytes(path)
        if byts is None:
            return None
        return crypto.load_certificate_request(crypto.FILETYPE_PEM, byts)

    def genUserCsr(self, name, outp=None):
        return self._genPkeyCsr(name, 'users', outp=outp)

    def genHostCsr(self, name, outp=None):
        return self._genPkeyCsr(name, 'hosts', outp=outp)

    def signUserCsr(self, xcsr, signas, outp=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genUserCert(name, pkey=pkey, signas=signas, outp=outp)

    def signHostCsr(self, xcsr, signas, outp=None, sans=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genHostCert(name, pkey=pkey, signas=signas, outp=outp, sans=sans)

    def _genPkeyCsr(self, name, mode, outp=None):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 2048)

        xcsr = crypto.X509Req()
        xcsr.get_subject().CN = name

        xcsr.set_pubkey(pkey)
        xcsr.sign(pkey, 'sha256')

        keypath = self._savePkeyTo(pkey, mode, '%s.key' % name)
        if outp is not None:
            outp.printf('key saved: %s' % (keypath,))

        csrpath = self.getPathJoin(mode, '%s.csr' % name)
        if os.path.isfile(csrpath):
            raise s_common.DupFileName(path=csrpath)

        with s_common.genfile(csrpath) as fd:
            fd.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr))

        if outp is not None:
            outp.printf('csr saved: %s' % (csrpath,))

    def signCertAs(self, cert, signas):
        cakey = self.getCaKey(signas)
        cacert = self.getCaCert(signas)

        cert.set_issuer(cacert.get_subject())
        cert.sign(cakey, 'sha256')

    def selfSignCert(self, cert, pkey):
        cert.set_issuer(cert.get_subject())
        cert.sign(pkey, 'sha256')

    def getUserForHost(self, user, host):
        for name in iterFqdnUp(host):
            usercert = '%s@%s' % (user, name)
            if self.isUserCert(usercert):
                return usercert

    def getCaCertPath(self, name):
        path = s_common.genpath(self.certdir, 'cas', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getCaKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'cas', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostCertPath(self, name):
        path = s_common.genpath(self.certdir, 'hosts', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'hosts', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserCertPath(self, name):
        path = s_common.genpath(self.certdir, 'users', '%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

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

    def getUserKeyPath(self, name):
        path = s_common.genpath(self.certdir, 'users', '%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserCaPath(self, name):
        cert = self.getUserCert(name)
        if cert is None:
            return None

        subj = cert.get_issuer()

        capath = self.getPathJoin('cas', '%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def getHostCaPath(self, name):
        cert = self.getHostCert(name)
        if cert is None:
            return None

        subj = cert.get_issuer()

        capath = self.getPathJoin('cas', '%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def isUserCert(self, name):
        crtpath = self.getPathJoin('users', '%s.crt' % name)
        return os.path.isfile(crtpath)

    def isCaCert(self, name):
        crtpath = self.getPathJoin('cas', '%s.crt' % name)
        return os.path.isfile(crtpath)

    def isHostCert(self, name):
        crtpath = self.getPathJoin('hosts', '%s.crt' % name)
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
