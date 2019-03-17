import os
import logging
import itertools

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import synapse.exc as s_exc

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
        except Exception:
            logger.exception('Error decrypting data')
            return None
        return data

class CryptSeq:
    '''
    Applies and verifies sequence numbers of encrypted messages coming and going

    Args:
        rx_key (bytes): TX key (used with TinFoilHat).
        tx_key (bytes): RX key (used with TinFoilHat).
        initial_rx_seq (int): Starting rx sequence number.
        initial_tx_seq (int): Starting tx sequence number.
    '''
    def __init__(self, rx_key, tx_key, initial_rx_seq=0, initial_tx_seq=0):
        self._rx_tinh = TinFoilHat(rx_key)
        self._tx_tinh = TinFoilHat(tx_key)
        self._rx_sn = itertools.count(initial_rx_seq)
        self._tx_sn = itertools.count(initial_tx_seq)

    def encrypt(self, mesg):
        '''
        Wrap a message with a sequence number and encrypt it.

        Args:
            mesg: The mesg to encrypt.

        Returns:
            bytes: The encrypted message.
        '''
        seqn = next(self._tx_sn)
        rv = self._tx_tinh.enc(s_msgpack.en((seqn, mesg)))
        return rv

    def decrypt(self, ciphertext):
        '''
        Decrypt a message, validating its sequence number is as we expect.

        Args:
            ciphertext (bytes): The message to decrypt and verify.

        Returns:
            mesg: A mesg.

        Raises:
            s_exc.CryptoErr: If the message decryption fails or the sequence number was unexpected.
        '''

        plaintext = self._rx_tinh.dec(ciphertext)
        if plaintext is None:
            logger.error('Message decryption failure')
            raise s_exc.CryptoErr(mesg='Message decryption failure')

        seqn = next(self._rx_sn)

        sn, mesg = s_msgpack.un(plaintext)
        if sn != seqn:
            logger.error('Message out of sequence: got %d expected %d', sn, seqn)
            raise s_exc.CryptoErr(mesg='Message out of sequence', expected=seqn, got=sn)

        return mesg
