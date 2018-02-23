import os
import hashlib
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

def newkey():
    '''
    Generate a new, random 32 byte key.

    Returns:
        bytes: 32 random bytes
    '''
    return os.urandom(32)

class TinFoilHat:
    '''
    The TinFoilHat class implements a GCM-AES encryption/decryption class.

    Args:
        ekey (bytes): A 32 byte key used for doing encryption & decryption. It
        is assumed the caller has generated the key in a safe manner.
    '''
    def __init__(self, ekey):
        self.ekey = ekey
        self.bend = default_backend()

    def enc(self, byts, asscd=None):
        '''
        Encrypt the given bytes and return an envelope dict in msgpack form.

        Args:
            byts (bytes): The message to be encrypted.
            asscd (bytes): Extra data that needs to be authenticated (but not encrypted).

        Returns:
            bytes: The encrypted message. This is a msgpacked dictionary
            containing the IV, ciphertext, and associated data.
        '''
        iv = os.urandom(16)
        encryptor = AESGCM(self.ekey)
        byts = encryptor.encrypt(iv, byts, asscd)
        envl = {'iv': iv, 'data': byts, 'asscd': asscd}
        return s_msgpack.en(envl)

    def dec(self, byts):
        '''
        Decode an envelope dict and decrypt the given bytes.

        Args:
            byts (bytes): Bytes to decrypt.

        Returns:
            bytes: Decrypted message.
        '''
        envl = s_msgpack.un(byts)
        iv = envl.get('iv', b'')
        asscd = envl.get('asscd', b'')
        data = envl.get('data', b'')

        decryptor = AESGCM(self.ekey)

        try:
            data = decryptor.decrypt(iv, data, asscd)
        except Exception as e:
            logger.exception('Error decrypting data')
            return None
        return data
