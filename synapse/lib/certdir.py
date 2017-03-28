import os

from OpenSSL import crypto

import synapse.lib.tags as s_tags

from synapse.common import *

defdir = os.getenv('SYN_CERT_DIR')
if defdir == None:
    defdir = '~/.syn/certs'

def iterFqdnUp(fqdn):
    levs = fqdn.split('.')
    for i in range(len(levs)):
        yield '.'.join( levs[i:] )

class CertDir:

    def __init__(self, path=None):

        if path == None:
            path = defdir

        gendir(path,'cas')
        gendir(path,'hosts')
        gendir(path,'users')

        self.certdir = reqdir(path)

    def getPathJoin(self, *paths):
        return genpath(self.certdir,*paths)

    def getCaCert(self, name):
        return self._loadCertPath( self.getCaCertPath(name) )

    def getHostCert(self, name):
        return self._loadCertPath( self.getHostCertPath(name) )

    def getUserCert(self, name):
        return self._loadCertPath( self.getUserCertPath(name) )

    def getCaKey(self, name):
        return self._loadKeyPath( self.getCaKeyPath(name) )

    def getHostKey(self, name):
        return self._loadKeyPath( self.getHostKeyPath(name) )

    def getUserKey(self, name):
        return self._loadKeyPath( self.getUserKeyPath(name) )

    def _loadKeyPath(self, path):
        if path == None:
            return None

        byts = getbytes(path)
        if byts == None:
            return None

        return crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

    def _loadCertPath(self, path):
        if path == None:
            return None

        byts = getbytes(path)
        if byts == None:
            return None

        return crypto.load_certificate(crypto.FILETYPE_PEM, byts)

    #def saveCaCert(self, cert):
    #def saveUserCert(self, cert):
    #def saveHostCert(self, cert):
    #def saveX509Cert(self, cert):
    #def loadX509Cert(self, path):

    def _genBasePkeyCert(self, name, pkey=None):

        if pkey == None:
            pkey = crypto.PKey()
            pkey.generate_key(crypto.TYPE_RSA, 2048)

        cert = crypto.X509()
        cert.set_pubkey(pkey)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_serial_number( int(time.time()) )

        cert.get_subject().CN = name

        return pkey,cert

    def _saveCertTo(self, cert, *paths):
        path = self.getPathJoin(*paths)
        if os.path.isfile(path):
            raise DupFileName(path=path)

        with genfile(path) as fd:
            fd.write( crypto.dump_certificate(crypto.FILETYPE_PEM, cert) )
        return path

    def _savePkeyTo(self, pkey, *paths):
        path = self.getPathJoin(*paths)
        if os.path.isfile(path):
            raise DupFileName(path=path)

        with genfile(path) as fd:
            fd.write( crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey) )
        return path

    def genCaCert(self, name, signas=None, outp=None):
        pkey,cert = self._genBasePkeyCert(name)
        ext0 = crypto.X509Extension(b'basicConstraints',False,b'CA:TRUE')
        cert.add_extensions([ext0])

        if signas != None:
            self.signCertAs(cert,signas)
        else:
            self.selfSignCert(cert,pkey)

        keypath = self._savePkeyTo(pkey, 'cas','%s.key' % name)
        if outp != None:
            outp.printf('key saved: %s' % (keypath,))

        crtpath = self._saveCertTo(cert, 'cas','%s.crt' % name)
        if outp != None:
            outp.printf('cert saved: %s' % (crtpath,))

        return pkey,cert

    def genHostCert(self, name, signas=None, outp=None, pkey=None):
        pkey,cert = self._genBasePkeyCert(name,pkey=pkey)

        certtype = b'server'
        extuse = [b'serverAuth']
        keyuse = [b'digitalSignature',b'keyEncipherment']

        ext0 = crypto.X509Extension(b'nsCertType',False,certtype)
        ext1 = crypto.X509Extension(b'keyUsage',False,b','.join(keyuse))

        extuse = b','.join(extuse)
        ext2 = crypto.X509Extension(b'extendedKeyUsage',False,extuse)
        ext3 = crypto.X509Extension(b'basicConstraints',False,b'CA:FALSE')

        cert.add_extensions([ext0,ext1,ext2,ext3])

        if signas != None:
            self.signCertAs(cert,signas)
        else:
            self.selfSignCert(cert,pkey)

        if not pkey._only_public:
            keypath = self._savePkeyTo(pkey, 'hosts','%s.key' % name)
            if outp != None:
                outp.printf('key saved: %s' % (keypath,))

        crtpath = self._saveCertTo(cert, 'hosts','%s.crt' % name)
        if outp != None:
            outp.printf('cert saved: %s' % (crtpath,))

        return pkey,cert

    def genUserCert(self, name, signas=None, outp=None, pkey=None):

        pkey,cert = self._genBasePkeyCert(name, pkey=pkey)

        keyuse = [b'digitalSignature']
        extuse = [b'clientAuth']
        certtype = b'client'

        ext0 = crypto.X509Extension(b'nsCertType',False,certtype)
        ext1 = crypto.X509Extension(b'keyUsage',False,b','.join(keyuse))

        extuse = b','.join(extuse)
        ext2 = crypto.X509Extension(b'extendedKeyUsage',False,extuse)
        ext3 = crypto.X509Extension(b'basicConstraints',False,b'CA:FALSE')

        cert.add_extensions([ext0,ext1,ext2,ext3])

        if signas != None:
            self.signCertAs(cert,signas)
        else:
            self.selfSignCert(cert,pkey)

        if not pkey._only_public:
            keypath = self._savePkeyTo(pkey, 'users','%s.key' % name)
            if outp != None:
                outp.printf('key saved: %s' % (keypath,))

        crtpath = self._saveCertTo(cert, 'users','%s.crt' % name)
        if outp != None:
            outp.printf('cert saved: %s' % (crtpath,))

        return pkey,cert

    def _loadCsrPath(self, path):
        byts = getbytes(path)
        if byts == None:
            return None
        return crypto.load_certificate_request(crypto.FILETYPE_PEM,byts)

    def genUserCsr(self, name, outp=None):
        return self._genPkeyCsr(name,'users',outp=outp)

    def genHostCsr(self, name, outp=None):
        return self._genPkeyCsr(name,'hosts',outp=outp)

    def signUserCsr(self, xcsr, signas, outp=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genUserCert(name, pkey=pkey, signas=signas, outp=outp)

    def signHostCsr(self, xcsr, signas, outp=None):
        pkey = xcsr.get_pubkey()
        name = xcsr.get_subject().CN
        return self.genHostCert(name, pkey=pkey, signas=signas, outp=outp)

    def _genPkeyCsr(self, name, mode, outp=None):
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 2048)

        xcsr = crypto.X509Req()
        xcsr.get_subject().CN = name

        xcsr.set_pubkey(pkey)
        xcsr.sign(pkey,'sha256')

        keypath = self._savePkeyTo(pkey,mode,'%s.key' % name)
        if outp != None:
            outp.printf('key saved: %s' % (keypath,))

        csrpath = self.getPathJoin(mode,'%s.csr' % name)
        if os.path.isfile(csrpath):
            raise DupFileName(path=csrpath)

        with genfile(csrpath) as fd:
            fd.write( crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr) )

        if outp != None:
            outp.printf('csr saved: %s' %( csrpath,))

    def signCertAs(self, cert, signas):
        cakey = self.getCaKey(signas)
        cacert = self.getCaCert(signas)

        cert.set_issuer( cacert.get_subject() )
        cert.sign( cakey, 'sha256' )

    def selfSignCert(self, cert, pkey):
        cert.set_issuer( cert.get_subject() )
        cert.sign( pkey, 'sha256' )

    def getUserForHost(self, user, host):
        for name in iterFqdnUp(host):
            usercert = '%s@%s' % (user,name)
            if self.isUserCert(usercert):
                return usercert

    def getCaCertPath(self, name):
        path = genpath(self.certdir,'cas','%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getCaKeyPath(self, name):
        path = genpath(self.certdir,'cas','%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostCertPath(self, name):
        path = genpath(self.certdir,'hosts','%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getHostKeyPath(self, name):
        path = genpath(self.certdir,'hosts','%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserCertPath(self, name):
        path = genpath(self.certdir,'users','%s.crt' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserKeyPath(self, name):
        path = genpath(self.certdir,'users','%s.key' % name)
        if not os.path.isfile(path):
            return None
        return path

    def getUserCaPath(self, name):
        cert = self.getUserCert(name)
        if cert == None:
            return None

        subj = cert.get_issuer()

        capath = self.getPathJoin('cas','%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def getHostCaPath(self, name):
        cert = self.getHostCert(name)
        if cert == None:
            return None

        subj = cert.get_issuer()

        capath = self.getPathJoin('cas','%s.crt' % subj.CN)
        if not os.path.isfile(capath):
            return None

        return capath

    def isUserCert(self, name):
        crtpath = self.getPathJoin('users','%s.crt' % name)
        return os.path.isfile(crtpath)

    def isCaCert(self, name):
        crtpath = self.getPathJoin('cas','%s.crt' % name)
        return os.path.isfile(crtpath)

    def isHostCert(self, name):
        crtpath = self.getPathJoin('hosts','%s.crt' % name)
        return os.path.isfile(crtpath)
