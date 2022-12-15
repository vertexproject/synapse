import hashlib

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.serialization as c_ser
import cryptography.hazmat.primitives.asymmetric.utils as c_utils
import cryptography.hazmat.primitives.asymmetric.padding as c_padding
import cryptography.hazmat.backends.openssl.rsa as c_rsa

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.msgpack as s_msgpack

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

class PriKey:
    '''
    A helper class for using RSA private keys.

    Signing methods use RSA-PSS and MFG1 with sha256 hashing.
    '''
    def __init__(self, priv):
        self.priv = priv  # type: c_rsa.RSAPrivateKey
        self.publ = self.public()

    def iden(self):
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            str: The SHA256 hash of the public key bytes.
        '''
        return self.publ.iden()

    def sign(self, byts):
        '''
        Compute the RSA signature for the given bytestream.

        Args:
            byts (bytes): The bytes to sign.

        Returns:
            bytes: The RSA Signature bytes.
        '''
        sha256 = c_hashes.SHA256()
        pad = c_padding.PSS(c_padding.MGF1(sha256), c_padding.PSS.MAX_LENGTH)
        return self.priv.sign(byts, pad, sha256)

    def signitem(self, item):
        '''
        Compute the RSA signature for the given python primitive.

        Args:
            item: The item to sign. This will be flattened and msgpacked prior to signing.

        Returns:
            bytes: The RSA Signature bytes.
        '''
        byts = s_msgpack.en(s_common.flatten(item))
        return self.sign(byts)

    def public(self):
        '''
        Get the PubKey which corresponds to the RSA PriKey.

        Returns:
            PubKey: A new PubKey object whose key corresponds to the private key.
        '''
        return PubKey(self.priv.public_key())

class PubKey:
    '''
    A helper class for using RSA public keys.
    '''

    def __init__(self, publ):
        self.publ = publ  # type: c_rsa.RSAPublicKey

    def dump(self):
        '''
        Get the public key bytes in DER/SubjectPublicKeyInfo format.

        Returns:
            bytes: The DER/SubjectPublicKeyInfo encoded public key.
        '''
        return self.publ.public_bytes(
            encoding=c_ser.Encoding.DER,
            format=c_ser.PublicFormat.SubjectPublicKeyInfo)

    def verify(self, byts, sign):
        '''
        Verify the signature for the given bytes using the RSA
        public key.

        Args:
            byts (bytes): The data bytes.
            sign (bytes): The signature bytes.

        Returns:
            bool: True if the data was verified, False otherwise.
        '''
        sha256 = c_hashes.SHA256()
        pad = c_padding.PSS(c_padding.MGF1(sha256), c_padding.PSS.MAX_LENGTH)
        try:
            self.publ.verify(sign, byts, pad, sha256)
            return True
        except InvalidSignature:
            return False

    def verifyitem(self, item, sign):
        '''
        Verify the signature for the given item with the RSA public key.

        Args:
            item: The Python primitive to verify.
            sign (bytes): The signature bytes.

        Returns:
            bool: True if the data was verified, False otherwise.
        '''
        byts = s_msgpack.en(s_common.flatten(item))
        return self.verify(byts, sign)

    def iden(self):
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            str: The SHA256 hash of the public key bytes.
        '''
        return hashlib.sha256(self.dump()).hexdigest()

    @staticmethod
    def load(byts):
        '''
        Create a PubKey instance from DER/PKCS8 encoded bytes.

        Args:
            byts (bytes): Bytes to load

        Returns:
            PubKey: A new PubKey instance.
        '''
        return PubKey(c_ser.load_der_public_key(byts, backend=default_backend()))
