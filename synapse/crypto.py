import os
import hashlib

import synapse.socket as s_socket
import synapse.common as s_common

class Rc4Xform(s_socket.SockXform):

    def __init__(self, rc4key):
        self.rc4key = rc4key

    def init(self, sock):
        from Crypto.Cipher import ARC4
        txnonce = s_common.guid()

        sock.sendall(txnonce)

        rxnonce = sock.recvall(16)
        if rxnonce == None:
            return

        txkey = hashlib.sha256( txnonce + self.rc4key ).digest()
        rxkey = hashlib.sha256( rxnonce + self.rc4key ).digest()

        self.txcrypt = ARC4.new( txkey )
        self.rxcrypt = ARC4.new( rxkey )

    def send(self, byts):
        return self.txcrypt.encrypt(byts)

    def recv(self, byts):
        return self.rxcrypt.decrypt(byts)

'''
Synapse PKI Notes:

cert = ( <certbytes>, [ (ident,<sigbytes>), ... ] )

<certbytes> -> {
    'ident':<guid>,
    'pubkey':<rsa-der>,
    'allows':{
    }
}

'''

class CertStore:
    def __init__(self):
        self.keys = {}      # <ident>:<rsakey>
        self.certs = {}     # <ident>:<cert>
        self.certinfo = {}  # <ident>:{ <prop>:<valu>, ... }

    def addCert(self, cert):
        '''
        Add a (<byts>,( (<ident>,<sig>), ..)) tuple.
        '''
        pass

    def isValidCert(self, cert):
        pass

    def getCertInfo(self, ident, prop):
        pass
