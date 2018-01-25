import os
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import synapse.common as s_common
import synapse.lib.msgpack as s_msgpack

def newkey():
    return os.urandom(32)

class TinFoilHat:
    '''
    The TinFoilHat class implements a pure binary cryptography.Fernet clone.
    '''
    def __init__(self, ekey):

        self.ekey = ekey
        self.bend = default_backend()
        self.skey = hashlib.sha256(ekey).digest()

        self.bsize = algorithms.AES.block_size

    def enc(self, byts):
        '''
        Encrypt the given bytes and return an envelope dict.
        '''
        iv = os.urandom(16)

        # pad the bytes using PKCS7
        padr = padding.PKCS7(self.bsize).padder()
        byts = padr.update(byts) + padr.finalize()

        mode = modes.CBC(iv)
        algo = algorithms.AES(self.ekey)
        encr = Cipher(algo, mode, self.bend).encryptor()

        # encrypt the bytes and prepend the IV
        byts = encr.update(byts) + encr.finalize()

        macr = HMAC(self.skey, hashes.SHA256(), backend=self.bend)
        macr.update(iv + byts)

        hmac = macr.finalize()
        envl = {'iv': iv, 'hmac': hmac, 'data': byts}
        return s_msgpack.en(envl)

    def dec(self, byts):

        envl = s_msgpack.un(byts)

        macr = HMAC(self.skey, hashes.SHA256(), backend=self.bend)

        iv = envl.get('iv', b'')
        hmac = envl.get('hmac', b'')
        data = envl.get('data', b'')

        macr.update(iv + data)

        try:
            macr.verify(hmac)
        except InvalidSignature:
            return None

        mode = modes.CBC(iv)
        algo = algorithms.AES(self.ekey)

        decr = Cipher(algo, mode, self.bend).decryptor()

        # decrypt the remaining bytes
        byts = decr.update(data)
        try:
            byts += decr.finalize()
        except ValueError:
            return None

        # unpad the decrypted bytes
        padr = padding.PKCS7(self.bsize).unpadder()

        byts = padr.update(byts)
        try:
            byts += padr.finalize()
        except ValueError:
            return None

        return byts
