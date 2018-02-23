import os
import hashlib
import logging

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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
        ekey (bytes): A 32 byte key used for doing encryption & decryption.
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
            containing the IV, ciphertext, associated data and tag values.
        '''
        iv = os.urandom(16)

        try:
            encryptor = Cipher(
                algorithms.AES(self.ekey),
                modes.GCM(iv),
                backend=self.bend
            ).encryptor()
        except Exception as e:
            logger.exception('Failed to initialize encryptor')
            return None

        if asscd is None:
            asscd = b''

        encryptor.authenticate_additional_data(asscd)
        byts = encryptor.update(byts) + encryptor.finalize()
        envl = {'iv': iv, 'data': byts, 'asscd': asscd, 'tag': encryptor.tag}
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
        assc = envl.get('asscd', b'')
        data = envl.get('data', b'')
        tag = envl.get('tag', b'')

        try:
            decryptor = Cipher(
                algorithms.AES(self.ekey),
                modes.GCM(iv, tag),
                backend=self.bend
            ).decryptor()
        except Exception as e:
            logger.exception('Failed to initialize decryptor')
            return None

        decryptor.authenticate_additional_data(assc)
        try:
            data = decryptor.update(data) + decryptor.finalize()
        except InvalidTag as e:
            logger.exception('Error decrypting data')
            return None
        return data
