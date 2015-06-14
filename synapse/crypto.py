import os
import hashlib

import synapse.common as s_common

class CryptoProvider:
    '''
    Encryption provider API for sockets.
    '''
    def __init__(self, link):
        self.link = link

        self.txcrypt = None
        self.rxcrypt = None

    def initSockCrypto(self, sock):
        pass

    def encrypt(self, byts):
        return self.txcrypt.encrypt(byts)

    def decrypt(self, byts):
        return self.rxcrypt.decrypt(byts)

    def __getattr__(self, name):
        return getattr(self.sock, name)

class RC4Crypto(CryptoProvider):

    def initSockCrypto(self, sock):

        # avoid deps until we require them
        from Crypto.Cipher import ARC4

        key = self.link[1].get('rc4key')
        txnonce = s_common.guid()

        sock.sendall(txnonce)

        rxnonce = sock.recvall(16)
        if rxnonce == None:
            return

        txkey = hashlib.sha256( txnonce + key ).digest()
        rxkey = hashlib.sha256( rxnonce + key ).digest()

        self.txcrypt = ARC4.new( txkey )
        self.rxcrypt = ARC4.new( rxkey )
