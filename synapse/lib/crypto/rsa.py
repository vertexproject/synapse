import hashlib
import logging

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.serialization as c_ser

import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class PriKey:
    '''
    A helper class for using RSA private keys.
    '''
    def __init__(self, priv):
        self.priv = priv  # type: c_rsa.RSAPrivateKey
        self.publ = PubKey(self.priv.public_key())

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

        Notes:
            Signatures are computed using PSS padding with SHA256 as the
            one-way transform function.

        Returns:
            bytes: The RSA Signature bytes.
        '''

        return self.priv.sign(
            byts,
            c_padding.PSS(
                mgf=c_padding.MGF1(c_hashes.SHA256()),
                salt_length=c_padding.PSS.MAX_LENGTH
            ),

            c_hashes.SHA256()
        )

    def public(self):
        '''
        Get the PubKey which corresponds to the RSA PriKey.

        Returns:
            PubKey: A new PubKey object whose key corresponds to the private key.
        '''
        return PubKey(self.priv.public_key())

    @staticmethod
    def generate(bits=4096):
        '''
        Generate a new RSA PriKey instance.

        Args:
            bits (int): Key size.

        Returns:
            PriKey: A new PriKey instance.
        '''
        return PriKey(
            c_rsa.generate_private_key(
                public_exponent=65537,
                key_size=bits,
                backend=default_backend()))

    def decrypt(self, byts):
        '''
        Decrypt bytes using the RSA private key.

        Args:
            byts (bytes): The encrypted bytes. If decryption fails, this returns None.
        '''
        try:
            return self.priv.decrypt(
                byts,
                c_padding.OAEP(
                    mgf=c_padding.MGF1(algorithm=c_hashes.SHA256()),
                    algorithm=c_hashes.SHA256(),
                    label=None
                )
            )
        except ValueError as e:
            logger.exception('Error in priv.decrypt')
            return None

    def dump(self):
        '''
        Get the private key bytes in DER/PKCS8 format.

        Returns:
            bytes: The DER/PKCS8 encoded private key.
        '''
        return self.priv.private_bytes(
            encoding=c_ser.Encoding.DER,
            format=c_ser.PrivateFormat.PKCS8,
            encryption_algorithm=c_ser.NoEncryption())

    @staticmethod
    def load(byts):
        '''
        Create a PriKey instance from DER/PKCS8 encoded bytes.

        Args:
            byts (bytes): Bytes to load

        Returns:
            PriKey: A new PubKey instance.
        '''
        return PriKey(c_ser.load_der_private_key(
                byts,
                password=None,
                backend=default_backend()))

class PubKey:
    '''
    A helper class for using RSA public keys.
    '''

    def __init__(self, publ):
        self.publ = publ  # type: c_rsa.RSAPublicKey

    def dump(self):
        '''
        Get the public key bytes in DER/PKCS8 format.

        Returns:
            bytes: The DER/PKCS8 encoded public key.
        '''
        return self.publ.public_bytes(
            encoding=c_ser.Encoding.DER,
            format=c_ser.PublicFormat.PKCS1)

    def encrypt(self, byts):
        '''
        Encrypt bytes using RSA Public Key Encryption.

            Args:
            byts (bytes):

        Notes:
            Bytes are encrypted with OAEP padding with SHA256 as the
            one-way transform function.

        Returns:
            bytes: The bytes encrypted with the RSA Public Key.
        '''
        return self.publ.encrypt(
            byts,
            c_padding.OAEP(
                mgf=c_padding.MGF1(algorithm=c_hashes.SHA256()),
                algorithm=c_hashes.SHA256(),
                label=None
            )
        )

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
        try:

            self.publ.verify(
                sign,
                byts,
                c_padding.PSS(
                    mgf=c_padding.MGF1(c_hashes.SHA256()),
                    salt_length=c_padding.PSS.MAX_LENGTH
                ),
                c_hashes.SHA256()
            )

            return True

        except InvalidSignature as e:
            logger.exception('Error in publ.verify')
            return False

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
        return PubKey(c_ser.load_der_public_key(
                byts,
                backend=default_backend()))
