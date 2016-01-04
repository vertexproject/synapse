import os
import hashlib

import synapse.common as s_common
import synapse.lib.socket as s_socket

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import ARC4

class Rc4Xform(s_socket.SockXform):

    def __init__(self, rc4key):
        self.rc4key = rc4key

    def init(self, sock):

        txnonce = os.urandom(16)

        try:

            sock.setblocking(1)

            sock._raw_sendall(txnonce)

            rxnonce = sock._raw_recvall(16)
            if rxnonce == None:
                return

            txkey = hashlib.sha256( txnonce + self.rc4key ).digest()
            rxkey = hashlib.sha256( rxnonce + self.rc4key ).digest()

            self.txcrypt = Cipher( ARC4(txkey), mode=None, backend=default_backend() ).encryptor()
            self.rxcrypt = Cipher( ARC4(rxkey), mode=None, backend=default_backend() ).decryptor()

        finally:

            if sock.plex:
                sock.setblocking(0)

    def txform(self, byts):
        return self.txcrypt.update(byts)

    def rxform(self, byts):
        return self.rxcrypt.update(byts)

class Rc4Skey(s_socket.SockXform):

    def __init__(self, rc4key):
        self.rc4key = rc4key
        self.txcrypt = Cipher( ARC4(rc4key), mode=None, backend=default_backend() ).encryptor()
        self.rxcrypt = Cipher( ARC4(rc4key), mode=None, backend=default_backend() ).decryptor()

    def init(self, sock):
        pass

    def txform(self, byts):
        return self.txcrypt.update(byts)

    def rxform(self, byts):
        return self.rxcrypt.update(byts)
