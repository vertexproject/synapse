import os
import hashlib
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.cache as s_cache
import synapse.lib.msgpack as s_msgpack

import synapse.lib.crypto.rsa as s_rsa

uservault = '~/.syn/vault.lmdb'

class Cert:

    def __init__(self, cert, rkey=None):

        self.cert = cert
        self.rkey = rkey

        self.tokn = s_msgpack.un(cert[0])
        self.toknhash = hashlib.sha256(cert[0]).hexdigest()

        byts = self.tokn.get('rsa:pub')
        self.rpub = s_rsa.PubKey.load(byts)

    def iden(self):
        return self.toknhash

    def getkey(self):
        return self.rkey

    def signers(self):
        return self.cert[1].get('signers')

    def public(self):
        return self.rpub

    def toknbytes(self):
        return self.cert[0]

    def sign(self, cert, **info):

        if self.rkey is None:
            raise s_exc.NoCertKey()

        info['time'] = s_common.now()

        data = s_msgpack.en(info)
        tosign = data + cert.toknbytes()

        sign = self.rkey.sign(tosign)

        signer = (self.iden(), data, sign)
        cert.addsigner(signer)

    def addsigner(self, sign):
        self.cert[1]['signers'] += (sign,)

    #def (self, sig):
        #self.cert[1]['signers'] += (sig,)

    #def initCertSign(self, cert, name, rkey):
        #'''
        #Construct a cert signature tuple for the given cert.

        #Args:
        #Returns:
            #((iden, bytes, bytes)): A cert signature tuple.
        #'''
        #data = s_msgpack.en({
            #'user': name,
            #'signed': s_common.now(),
        #})

        #iden = rkey.public().iden()
        #return (iden, data, rkey.sign(data + cert[0]))

    def verify(self, byts, sign):
        return self.rpub.verify(byts, sign)

    def signed(self, cert):
        '''
        Check if this cert signed the given Cert and return the info.

        Args:
            cert (Cert): A Cert to confirm that we signed.

        Returns:
            (dict): The signer info dict ( or None if not signed ).

        '''
        byts = cert.toknbytes()

        for iden, data, sign in cert.signers():

            if iden != self.iden():
                continue

            if self.verify(data + byts, sign):
                return s_msgpack.un(data)

    def save(self):
        return s_msgpack.en(self.cert)

    @staticmethod
    def load(byts, rkey=None):
        return Cert(s_msgpack.un(byts), rkey=rkey)

class Vault(s_eventbus.EventBus):

    '''
    tokn:
        {
            'user': <str>,
            'rsa:pub': <bytes>,
        }

    cert:
        ( <toknbyts>, {
            "signers": (
                <sig>,
            ),
        })

    sig:
        # NOTE: <iden> must *only* be used for pub key lookup
        (<iden>, <bytes(signdata)>, <signbytes>),

    '''
    def __init__(self, path):

        s_eventbus.EventBus.__init__(self)

        self.kvstor = s_kv.KvStor(path)

        self.onfini(self.kvstor.fini)

        self.info = self.kvstor.getKvLook('info')

        self.keys = self.kvstor.getKvLook('keys')
        self.certs = self.kvstor.getKvLook('certs')
        self.roots = self.kvstor.getKvLook('roots')

        self.certkeys = self.kvstor.getKvLook('keys:bycert')
        self.usercerts = self.kvstor.getKvLook('certs:byuser')

    def genRsaKey(self):
        '''
        Generate a new RSA key and store it in the vault.
        '''
        rkey = s_rsa.PriKey.generate()

        iden = rkey.iden()
        self.keys.set(iden, rkey.save())

        return rkey

    def setRsaKey(self, name, byts):
        '''
        Set the RSA key (bytes) for the given user.
        '''

        rkey = s_rsa.PriKey.load(byts)

        self.rsacache[name] = rkey
        self.rsakeys.set(name, byts)

        return rkey

    def genCertTokn(self, rpub, **info):
        info['rsa:pub'] = rpub.save()
        info['created'] = s_common.now()
        return s_msgpack.en(info)

    def genToknCert(self, tokn, rkey=None):

        cefo = (tokn, {'signers': ()})
        cert = Cert(cefo, rkey=rkey)

        cert.sign(cert)
        return cert

    def getUserCert(self, name):
        '''
        Retrieve a cert tufo for the given user.
        '''
        iden = self.usercerts.get(name)
        if iden is None:
            return None

        return self.getCert(iden)

    def setUserCert(self, name, cert):
        '''
        Save a cert tufo for the given user.
        '''
        self.certs.set(name, cert)

    def genUserCert(self, name):
        '''
        Generate a key/cert for the given user.

        Args:
            name (str): The user name.

        Returns:
            (Cert): A newly generated user certificate.
        '''
        iden = self.usercerts.get(name)
        if iden is not None:
            return self.getCert(iden)

        rkey = self.genRsaKey()

        rpub = rkey.public()
        tokn = self.genCertTokn(rpub, user=name)
        cert = self.genToknCert(tokn, rkey=rkey)

        root = self.genRootCert()
        root.sign(cert)

        iden = cert.iden()

        self.certs.set(iden, cert.save())
        self.certkeys.set(iden, rkey.save())
        self.usercerts.set(name, iden)

        return cert

    def genUserAuth(self, user):
        '''
        Generate a *sensitve* user auth data structure.

        Args:
            user (str): The user name to export.

        Returns:
            ((str,dict)): A user auth tufo.

        NOTE: This is *highly* sensitive and contains keys.
        '''
        cert = self.genUserCert(user)
        rkey = self.getCertKey(cert.iden())

        return (user, {
            'cert': cert.save(),
            'rsa:key': rkey.save(),
        })

    def addUserAuth(self, auth):
        '''
        Load and store a private user auth tufo.

        NOTE: This is *highly* senstive/trusted.
              Only load auth tufo from trusted sources.
              This API is mostly for provisioning automation.
        '''
        user, info = auth

        certbyts = info.get('cert')
        rkeybyts = info.get('rsa:key')

        rkey = s_rsa.PriKey.load(rkeybyts)
        cert = Cert.load(certbyts, rkey=rkey)

        iden = cert.iden()

        self.certs.set(iden, cert.save())
        self.certkeys.set(iden, rkey.save())
        self.usercerts.set(user, iden)

        return cert

    def getCert(self, iden):
        '''
        Get a certificate by iden.

        Args:
            iden (str): The cert iden.

        Returns:
            (Cert): The Cert or None.
        '''
        byts = self.certs.get(iden)
        if byts is None:
            return None

        rkey = self.getCertKey(iden)
        return Cert.load(byts, rkey=rkey)

    def getCertKey(self, iden):
        byts = self.certkeys.get(iden)
        if byts is not None:
            return s_rsa.PriKey.load(byts)

    def genRootCert(self):
        '''
        Get or generate the primary root cert for this vault.
        '''
        iden = self.info.get('root')
        if iden is not None:
            return self.getCert(iden)

        rkey = self.genRsaKey()
        tokn = self.genCertTokn(rkey.public())
        cert = self.genToknCert(tokn, rkey=rkey)

        iden = cert.iden()

        self.info.set('root', iden)

        self.certkeys.set(iden, rkey.save())

        self.addRootCert(cert)
        return cert

    def addRootCert(self, cert):
        iden = cert.iden()
        self.roots.set(iden, True)
        self.certs.set(iden, cert.save())

    def delRootCert(self, cert):
        iden = cert.iden()
        self.roots.set(iden, False)

    def getRootCerts(self):
        retn = []
        for iden, isok in self.roots.items():

            if not isok:
                continue

            cert = self.getCert(iden)
            if cert is None:
                continue

            retn.append(cert)

        return retn

    def isValidCert(self, cert):
        return any([c.signed(cert) for c in self.getRootCerts()])

@contextlib.contextmanager
def shared(path):
    '''
    A context manager for locking a potentially shared vault.

    Args:
        path (str): Path to the vault.

    Example:

        with s_vault.shared('~/.syn/vault') as vault:
            dostuff()
    '''
    full = s_common.genpath(path)

    lock = os.path.join(full, 'synapse.lock')

    # yo
    with s_common.lockfile(lock):
        # dawg
        with Vault(full) as vault:
            yield vault
