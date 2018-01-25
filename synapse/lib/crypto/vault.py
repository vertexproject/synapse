import os
import contextlib

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.cache as s_cache
import synapse.lib.msgpack as s_msgpack

import synapse.lib.crypto.rsa as s_rsa

class Vault(s_eventbus.EventBus):

    '''
    tokn:
        (<iden>, {
            'user': <str>,
            'rsa:pub': <bytes>,
        })

    cert:
        ( <toknbyts>, {
            "sigs": (
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

        # certs by user
        self.certs = self.kvstor.getKvLook('certs')

        # certs by iden which are authorized signers
        self.signers = self.kvstor.getKvDict('signers')
        self.signpubs = {}

        # rsa key bytes by user
        self.rsakeys = self.kvstor.getKvLook('rsa:keys')
        self.rsacache = s_cache.KeyCache(self._getRsaKey)

        # TODO: revokation

    def _getRsaKey(self, user):

        byts = self.rsakeys.get(user)
        if byts is None:
            return None

        return s_rsa.PriKey.load(byts)

    def addSignerCert(self, cert):
        '''
        Explicitly add the given cert to the signers list.

        Args:
            cert ((bytes,dict)): A cert tuple.

        NOTE: This API assumes validation has already been done.
        '''
        tokn = s_msgpack.un(cert[0])
        self.signers.set(tokn[0], cert)

    def delSignerCert(self, cert):
        '''
        Deny the given cert the ability to sign other certs.

        Args:
            cert ((bytes,dict)): A cert tuple.

        NOTE: This API assumes validation has already been done.
        '''
        tokn = s_msgpack.un(cert[0])
        self.signers.pop(tokn[0])

    def getSignerCert(self, iden):
        return self.signers.get(iden)

    def getRsaKey(self, name):
        return self.rsacache.get(name)

    def genRsaKey(self, name):

        rkey = self.getRsaKey(name)
        if rkey is not None:
            return rkey

        rkey = s_rsa.PriKey.generate()

        self.rsacache[name] = rkey
        self.rsakeys.set(name, rkey.save())

        return rkey

    def setRsaKey(self, name, byts):
        '''
        Set the RSA key (bytes) for the given user.
        '''

        rkey = s_rsa.PriKey.load(byts)

        self.rsacache[name] = rkey
        self.rsakeys.set(name, byts)

        return rkey

    def initUserTokn(self, name, rpub):
        iden = rpub.iden()
        tokn = (iden, {
            'user': name,
            'created': s_common.now(),
            'rsa:pub': rpub.save(),
        })
        return tokn

    def initToknCert(self, tokn):
        return (s_msgpack.en(tokn), {'sigs': ()})

    def getUserCert(self, name):
        '''
        Retrieve a cert tufo for the given user.
        '''
        return self.certs.get(name)

    def setUserCert(self, name, cert):
        '''
        Save a cert tufo for the given user.
        '''
        self.certs.set(name, cert)

    def genUserCert(self, name):
        '''
        Generate a key/cert for the given user and self-sign it.

        Args:
            name (str): The user name.

        Returns:
            (PriKey, (bytes,dict), PriKey): A key, cert tuple.
        '''
        rkey = self.genRsaKey(name)
        cert = self.certs.get(name)
        if cert is not None:
            return rkey, cert

        rpub = rkey.public()

        tokn = self.initUserTokn(name, rpub)

        cert = self.initToknCert(tokn)
        cert = self.addCertSign(cert, name, rkey)

        self.certs.set(name, cert)
        return rkey, cert

    def addCertSign(self, cert, name, rkey=None):

        if rkey is None:
            rkey = self.getRsaKey(name)
            if rkey is None:
                raise NoSuchUser(name=name)

        signer = self.initCertSign(cert, name, rkey)

        cert[1]['sigs'] += (signer,)
        return cert

    def getUserAuth(self, user):
        '''
        Generate a *sensitve* user auth data structure.

        Args:
            user (str): The user name to export.

        Returns:
            ((str,dict)): A user auth tufo.

        NOTE: This is *highly* sensitive and contains keys.
        '''
        rkey = self.getRsaKey(user)
        if rkey is None:
            return None

        cert = self.getUserCert(user)

        return (user, {
            'cert': cert,
            'rsa:key': rkey.save(),
        })

    def addUserAuth(self, auth, signer=False):
        '''
        Load and store a private user auth tufo.

        NOTE: This is *highly* senstive/trusted.
              Only load auth tufo from trusted sources.
              This API is mostly for provisioning automation.
        '''
        user, info = auth

        cert = info.get('cert')
        byts = info.get('rsa:key')

        rkey = self.setRsaKey(user, byts)
        self.setUserCert(user, cert)

        if signer:
            self.addSignerCert(cert)

        return rkey, cert

    def initCertSign(self, cert, name, rkey):
        '''
        Construct a cert signature tuple for the given cert.

        Args:
        Returns:
            ((iden, bytes, bytes)): A cert signature tuple.
        '''
        data = s_msgpack.en({
            'user': name,
            'signed': s_common.now(),
        })

        iden = rkey.public().iden()
        return (iden, data, rkey.sign(data + cert[0]))

    def isValidCert(self, cert):
        '''
        Check if the given cert is valid for this vault.

        Args:
            cert ((bytes,dict)): A certificate tuple.

        '''
        for iden, data, sign in cert[1].get('sigs', ()):

            signer = self.getSignerCert(iden)
            if signer is None:
                continue

            rpub = self.signpubs.get(iden)
            if rpub is None:
                signtokn = s_msgpack.un(signer[0])
                rpub = s_rsa.PubKey.load(signtokn[1].get('rsa:pub'))
                self.signpubs[iden] = rpub

            if not rpub.verify(data + cert[0], sign):
                continue

            # it is now safe to inspect signer data if we want...
            # ...

            return True

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
