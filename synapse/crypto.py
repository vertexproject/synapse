import os
import hashlib

import synapse.common as s_common
import synapse.lib.socket as s_socket

class Rc4Xform(s_socket.SockXform):

    def __init__(self, rc4key):
        self.rc4key = rc4key

    def init(self, sock):
        from Crypto.Cipher import ARC4
        txnonce = os.urandom(16)

        #oldtime = sock.gettimeout()
        #oldblock = sock.blocking()

        try:

            #sock.settimeout(2)
            sock.setblocking(1)

            sock._raw_sendall(txnonce)

            rxnonce = sock._raw_recvall(16)
            if rxnonce == None:
                return

            txkey = hashlib.sha256( txnonce + self.rc4key ).digest()
            rxkey = hashlib.sha256( rxnonce + self.rc4key ).digest()

            self.txcrypt = ARC4.new( txkey )
            self.rxcrypt = ARC4.new( rxkey )

        finally:
            if sock.plex:
                sock.setblocking(0)
            #sock.settimeout(oldtime)
            #sock.setblocking(oldblock)

    def txform(self, byts):
        return self.txcrypt.encrypt(byts)

    def rxform(self, byts):
        return self.rxcrypt.decrypt(byts)
