import os
import hashlib
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import synapse.common as s_common
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# Don't let people use tinfoil if they don't meet the requirements
_bend = default_backend()
if not _bend.cipher_supported(algorithms.AES(b'\x00' * 32), modes.CBC(b'\x00' * 16)):  # pragma: no cover
    raise s_common.SynErr(mesg='default_backend() does not support AES-CBC')
if not _bend.hash_supported(hashes.SHA256()):  # pragma: no cover
    raise s_common.SynErr(mesg='default_backend() does not support SHA256 hash')
if not _bend.hmac_supported(hashes.SHA256()):  # pragma: no cover
    raise s_common.SynErr(mesg='default_backend() does not support SHA256 hmac')

def newkey():
    '''
    Generate a new, random 32 byte key.

    Returns:
        bytes: 32 random bytes
    '''
    return os.urandom(32)

class TinFoilHat:
    '''
    The TinFoilHat class implements a pure binary cryptography.Fernet clone.

    This provides symmetric AES-CBC Encryption with SHA256 HMAC (in encrypt
    then mac mode).

    Args:
        ekey (bytes): A 32 byte key used for doing encryption & decryption.
    '''
    def __init__(self, ekey):
        self.ekey = ekey
        self.bend = default_backend()
        self.skey = hashlib.sha256(ekey).digest()

        self.bsize = algorithms.AES.block_size

    def enc(self, byts):
        '''
        Encrypt the given bytes and return an envelope dict in msgpack form.

        Args:
            byts (bytes): The message to be encrypted.

        Returns:
            bytes: The encrypted message. This is a msgpacked dictionary
            containing the IV, ciphertext and HMAC values.
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
        '''
        Decode an envelope dict and decrypt the given bytes.

        Args:
            byts (bytes): Bytes to decrypt.

        Returns:
            bytes: Decrypted message.
        '''

        envl = s_msgpack.un(byts)

        macr = HMAC(self.skey, hashes.SHA256(), backend=self.bend)

        iv = envl.get('iv', b'')
        hmac = envl.get('hmac', b'')
        data = envl.get('data', b'')

        macr.update(iv + data)

        try:
            macr.verify(hmac)
        except InvalidSignature as e:
            logger.warning('Error in macr.verify: [%s]', str(e))
            return None

        mode = modes.CBC(iv)
        algo = algorithms.AES(self.ekey)

        decr = Cipher(algo, mode, self.bend).decryptor()

        # decrypt the remaining bytes
        byts = decr.update(data)
        byts += decr.finalize()

        # unpad the decrypted bytes
        padr = padding.PKCS7(self.bsize).unpadder()

        byts = padr.update(byts)
        byts += padr.finalize()

        return byts
