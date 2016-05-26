import os
import base64

from cryptography.hazmat.backends import default_backend

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding
import cryptography.hazmat.primitives.serialization as c_serialization

from cryptography.exceptions import InvalidSignature

import synapse.glob as s_glob
import synapse.cortex as s_cortex
import synapse.lib.cache as c_cache

from synapse.common import *
from synapse.eventbus import EventBus

'''
Custom PKI API / objects for use in synapse.

Glossary:

* Token - {
            'iden':<guid>,
            'name':<name>,      # humon readable name (aka "who")
            'root':<int>,       # set to 1 for root cert
            'pubkey':<byts>,    # DER encoded public key bytes
            'can':{ <tag>:True, ... },  # rights granted to the token

            'issued':<time>     # epoch time when embedded in cert and signed

          }

* Certificate - ( <byts>, {                                 # msgpack bytes (most often a token)
                        'signs':( (<iden>,<sign>), ... ),   
                        'certs':( <cert>, ... ),
                    }
                )


'''

backend = default_backend()

c_sha1 = c_hashes.SHA1()
c_sha256 = c_hashes.SHA256()
c_oaep_sha1 = c_padding.OAEP(mgf=c_padding.MGF1(algorithm=c_sha1), algorithm=c_sha1, label=None)
c_pss_sha256 = c_padding.PSS(mgf=c_padding.MGF1(c_sha256),salt_length=c_padding.PSS.MAX_LENGTH)

homedir = os.path.expanduser('~')
pkipath = os.path.join(homedir,'.synpki')
pkicore = 'sqlite:///%s' % (pkipath,)

def getUserPki():
    # TODO env var
    # TODO agent?
    '''
    Return the current/default PkiStor for the current user.
    '''
    with s_glob.lock:

        if s_glob.pki == None:
            core = s_cortex.openurl(pkicore)
            s_glob.pki = PkiStor(core)

        return s_glob.pki

def obj2b64(obj):
    return base64.b64encode( msgenpack(obj) )

def b642obj(txt):
    return msgunpack( base64.b64decode(txt) )

def initTokenTufo(iden, pubkey, root=False, can=(), **props):
    props['root'] = root
    props['pubkey'] = pubkey

    props['can'] = { c:True for c in can }

    return (iden,props)

def initTokenCert(token):
    byts = msgenpack(token)
    return tufo(byts,signs=(),certs=())

def pubToDer(pub):
    '''
    DER encode an RSA public key
    '''
    return pub.public_bytes(
       encoding=c_serialization.Encoding.DER,
       format=c_serialization.PublicFormat.SubjectPublicKeyInfo,
    )

def keyToDer(key):
    '''
    DER encode an RSA key
    '''
    return key.private_bytes(
       encoding=c_serialization.Encoding.DER,
       format=c_serialization.PrivateFormat.TraditionalOpenSSL,
       encryption_algorithm=c_serialization.NoEncryption()
    )

def pubEncBytes(pub, byts):
    return pub.encrypt(byts,c_oaep_sha1)

def keyDecBytes(key, byts):
    return key.decrypt(byts,c_oaep_sha1)

def genRsaKey(bits=4096):
    '''
    Generate a new RSA key pair.
    '''
    return c_rsa.generate_private_key(public_exponent=65537, key_size=bits, backend=backend)

class PkiStor(EventBus):

    '''
    A PkiStor models public key authentication tokens using a cortex
    and provides APIs for creating, verifying, and using tokens for AAA.
    '''

    def __init__(self, core):

        EventBus.__init__(self)
        self.core = core

        self.keys = c_cache.Cache()
        self.keys.setOnMiss( self._getRsaKey )

        self.pubs = c_cache.Cache()
        self.pubs.setOnMiss( self._getPubKey )

        self.certs = c_cache.Cache()
        self.certs.setOnMiss( self._getTokenCert )

        self.tokens = c_cache.Cache()
        self.tokens.setOnMiss( self._getTokenTufo )

        core.onfini( self.keys.fini )
        core.onfini( self.pubs.fini )
        core.onfini( self.certs.fini )
        core.onfini( self.tokens.fini )

        core.addTufoForm('syn:token', ptype='str', doc='synapse identity token (user/host)')

        core.addTufoProp('syn:token', 'user', doc='humon readable user name for this token')
        core.addTufoProp('syn:token', 'host', doc='humon readable host name for this token')

        core.addTufoProp('syn:token', 'blob', doc='Base64 encoded token blob')
        core.addTufoProp('syn:token', 'cert', doc='Base64 encoded certificate blob')
        core.addTufoProp('syn:token', 'rsakey', doc='base64( der( rsa.private ) )')

    def setTokenTufo(self, token, save=False):
        '''
        Add a trusted token tufo and optionally save.

        Example:

            pki.setTokenTufo(token,save=True)

        '''
        iden = token[0]

        host = token[1].get('host')
        user = token[1].get('user')

        self.tokens.put(iden,token)

        if save:
            tokn = self.core.formTufoByProp('syn:token',iden)
            b64blob = base64.b64encode( msgenpack( token ) )

            props = dict(blob=b64blob)

            if host != None:
                props['host'] = host

            if user != None:
                props['user'] = user

            self.core.setTufoProps(tokn, **props)

    def getIdenByUser(self, user):
        '''
        Get user token iden by name.
        '''
        tokn = self.core.getTufoByProp('syn:token:user', user)
        if tokn == None:
            return None

        return tokn[1].get('syn:token')

    def getIdenByHost(self, host):
        '''
        Get host token iden by name.
        '''
        # FIXME cache
        tokn = self.core.getTufoByProp('syn:token:host', host)
        if tokn == None:
            return None

        return tokn[1].get('syn:token')

    def getTokenTufo(self, iden):
        '''
        Return the tufo for the given token iden.

        Example:

            tokn = pki.getTokenTufo(iden)

        '''
        return self.tokens.get(iden)

    def _getTokenTufo(self, iden):
        tokn = self.core.getTufoByProp('syn:token',iden)
        if tokn == None:
            return None

        blob = tokn[1].get('syn:token:blob')
        if blob == None:
            return None

        return msgunpack( base64.b64decode( blob ) )

    def getPubKey(self, iden):
        '''
        Retrieve the RSA public key for the given iden (or None).
        '''
        return self.pubs.get(iden)

    def _getPubKey(self, iden):
        # load all pubkeys from tokens
        token = self.getTokenTufo(iden)
        pubder = token[1].get('pubkey')
        return c_serialization.load_der_public_key(pubder, backend)

    def getRsaKey(self, iden):
        '''
        Retrieve the RSA private key for the given iden (or None).

        Example:

            rsakey = pki.getRsaKey(iden)

        '''
        return self.keys.get(iden)

    def _getRsaKey(self, iden):
        tokn = self.core.getTufoByProp('syn:token',iden)
        if tokn == None:
            return None

        keyb64 = tokn[1].get('syn:token:rsakey')
        if keyb64 == None:
            return None

        rsader = base64.b64decode(keyb64)
        return c_serialization.load_der_private_key(rsader, password=None, backend=backend)

    def setRsaKey(self, iden, key, save=False):
        '''
        Set the RSA private key for an iden and optionally save.

        Example:

            rsakey = genRsaKey(bits=4096)

            pki.setRsaKey(iden,rsakey)

        '''
        self.keys.put(iden,key)

        if not save:
            return

        tokn = self.core.formTufoByProp('syn:token',iden)

        rsab64 = base64.b64encode( keyToDer( key ) )
        props = {'syn:token:rsakey':rsab64}
        self.core.setTufoProps(tokn,**props)

    def genRootToken(self, bits=4096, save=False):
        '''
        Generate a new root token and optionally save.

        Example:
    
            tokn = self.genRootToken()

        '''
        key = genRsaKey(bits=bits)
        pub = key.public_key()

        iden = guid()

        pubder = pubToDer(pub)

        token = initTokenTufo(iden, pubder, root=True)

        self.setRsaKey(iden,key,save=save)
        self.setTokenTufo(token,save=save)

        return token

    def genHostToken(self, host, can=(), bits=4096, save=True):
        '''
        Generate a new host token with the specified capabilities.

        Example:

            tokn = pki.genHostToken('visi.kenshoto.com')

        '''
        iden = guid()
        key = genRsaKey(bits=bits)

        self.setRsaKey(iden, key, save=save)

        pubder = pubToDer( key.public_key() )

        token = initTokenTufo(iden, pubder, host=host, can=can)
        self.setTokenTufo(token, save=save)

        return token

    def genUserToken(self, user, root=False, can=(), bits=4096, save=True):
        '''
        Generate a new user token with the specified capabilities.

        Example:

            tokn = pki.genUserToken('visi@kenshoto.com', can=('sign:cert','mesh:join'))
            skey = pki.getUserKey( tokn[1].get('syntok') )

        '''
        iden = guid()
        key = genRsaKey(bits=bits)

        self.setRsaKey(iden, key, save=save)

        pubder = pubToDer( key.public_key() )

        token = initTokenTufo(iden, pubder, user=user, can=can, root=root)
        self.setTokenTufo(token, save=save)

        return token

    def genTokenCert(self, token, signas=None, save=True):
        '''
        Generate and optionally sign a cert tuple for the given token.

        Example:

            cert = pki.genTokenCert(tokn, signas=iden)

        Notes:

            * See docs for synapse.lib.pki module for cert structure

        '''
        token[1]['cert:issued:at'] = int(time.time())
        if signas != None:
            token[1]['cert:issued:by'] = signas

        cert = initTokenCert(token)
        if signas != None:
            cert = self.signTokenCert(signas,cert)

        self.setTokenCert(token[0], cert, save=save)

        return cert

    def signTokenCert(self, iden, cert, save=True):
        '''
        Add a signature to the given certificate tuple.

        Example:

            cert = pki.signTokenCert(iden,cert)

        '''
        signs = cert[1].get('signs',())
        certs = cert[1].get('certs',())

        sign = self.genByteSign(iden,cert[0])

        mcrt = self.getTokenCert(iden)
        if mcrt != None:
            cert[1]['certs'] = certs + (mcrt,)

        cert[1]['signs'] = signs + ( (iden,sign), )

        self.setTokenCert(iden, cert, save=save)

        return cert

    def genByteSign(self, iden, byts):
        '''
        Generate a signature for the given bytes by the specificed iden.

        Example:

            sign = pki.genByteSign(iden,byts)

        Notes:

            If no RSA key exists for iden, return None.

        '''
        key = self.getRsaKey(iden)
        if key == None:
            return None

        signer = key.signer(c_pss_sha256,c_sha256)
        signer.update(byts)

        return signer.finalize()

    def delTokenTufo(self, iden):
        '''
        Delete an entire token tufo by iden.
        '''
        tokn = self.core.formTufoByProp('syn:token', iden)

        self.keys.pop(iden)
        self.pubs.pop(iden)
        self.certs.pop(iden)
        self.tokens.pop(iden)

    def loadCertToken(self, cert, save=False, force=False):
        '''
        Verify and load a the token within a certificate.
        '''
        for subcert in cert[1].get('certs'):
            self.loadCertToken(subcert, save=save)

        if force:
            token = msgunpack(cert[0])
            self.setTokenTufo(token, save=save)
            return token

        for iden,sign in cert[1].get('signs'):
            token = self.getTokenTufo(iden)
            if token == None:
                continue

            if not token[1].get('root') and not token[1].get('can',{}).get('sign:cert'):
                continue

            if not self.isValidSign(iden,sign,cert[0]):
                continue

            # it's a totally valid cert!
            token = msgunpack(cert[0])
            self.setTokenTufo(token, save=save)

            return token

        return None

    def setTokenCert(self, iden, cert, save=True):
        '''
        Set a token cert in the PkiStor and optionally persist.

        Example:

            pki.setTokenCert(cert)

        '''
        self.certs.put(iden,cert)

        if save:
            b64bytes = base64.b64encode( msgenpack( cert ) )
            tokn = self.core.formTufoByProp('syn:token', iden)
            self.core.setTufoProps(tokn,cert=b64bytes)

    def getTokenCert(self, iden):
        '''
        Retrieve a cert for the given iden.

        Example:

            cert = pki.getTokenCert(iden)

        '''
        return self.certs.get(iden)

    def _getTokenCert(self, iden):
        tokn = self.core.getTufoByProp('syn:token',iden)
        if tokn == None:
            return None

        b64c = tokn[1].get('syn:token:cert')
        if not b64c:
            return None

        byts = base64.b64decode(b64c)
        cert = msgunpack(byts)

        return cert

    def isValidSign(self, iden, sign, byts):
        '''
        Check if the given signature is valid for the given bytes.

        Example:

            if not pki.isValidSign(iden, sign, byts):
                bail()

        '''
        token = self.getTokenTufo(iden)
        if token == None:
            return False

        # FIXME sign / optional can args
        pub = self.getPubKey(iden)

        verifier = pub.verifier(sign,c_pss_sha256,c_sha256)
        verifier.update(byts)

        try:

            verifier.verify()
            return True

        except InvalidSignature as e:
            return False

    def iterTokenTufos(self):
        '''
        Yield each of the known token dictionaries in the PkiStor.

        Example:

            for tokn in stor.iterTokenTufos():
                dostuff(tokn)


        '''
        for tokn in self.core.getTufosByProp('syn:token:blob'):
            blob = tokn[1].get('syn:token:blob')
            if not blob:
                continue

            yield b642obj(blob)

    def encToIden(self, iden, byts):
        '''
        Encrypt the given bytes to the target iden's public key.

        Notes:

            * as usual this should be used to gen/pass symetric key...

        '''
        pub = self.pubs.get(iden)
        if pub == None:
            return None

        return pubEncBytes(pub,byts)

    def decToIden(self, iden, byts):
        '''
        Decrypt the given bytes which were sent to using iden's public key.
        '''
        key = self.keys.get(iden)
        if key == None:
            return None

        return keyDecBytes(key,byts)
