import hashlib

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.serialization as c_ser

import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

class PriKey:
    '''
    A helper class for using RSA private keys.
    '''
    def __init__(self, priv):
        self.priv = priv

    def sign(self, byts):

        return self.priv.sign(
            byts,
            c_padding.PSS(
                mgf=c_padding.MGF1(c_hashes.SHA256()),
                salt_length=c_padding.PSS.MAX_LENGTH
            ),

            c_hashes.SHA256()
        )

    def public(self):
        return PubKey(self.priv.public_key())

    @staticmethod
    def generate(bits=4096):
        return PriKey(
            c_rsa.generate_private_key(
                public_exponent=65537,
                key_size=bits,
                backend=default_backend()))

    def decrypt(self, byts):
        '''
        Decrypt bytes using the RSA private key.

        Args:
            byts (bytes): The encrypted bytes.
        '''
        return self.priv.decrypt(
            byts,
            c_padding.OAEP(
                mgf=c_padding.MGF1(algorithm=c_hashes.SHA256()),
                algorithm=c_hashes.SHA256(),
                label=None
            )
        )

    def save(self):
        '''
        Save the private key bytes in DER/PKCS8 format.

        Returns:
            (bytes): The DER/PKCS8 encoded private key.
        '''
        return self.priv.private_bytes(
            encoding=c_ser.Encoding.DER,
            format=c_ser.PrivateFormat.PKCS8,
            encryption_algorithm=c_ser.NoEncryption())

    @staticmethod
    def load(byts):
        return PriKey(c_ser.load_der_private_key(
                byts,
                password=None,
                backend=default_backend()))

class PubKey:
    '''
    A helper class for using RSA public keys.
    '''

    def __init__(self, publ):
        self.publ = publ

    def save(self):
        '''
        Save the public key bytes in DER/PKCS8 format.

        Returns:
            (bytes): The DER/PKCS8 encoded public key.
        '''
        return self.publ.public_bytes(
            encoding=c_ser.Encoding.DER,
            format=c_ser.PublicFormat.PKCS1)

    def encrypt(self, byts):
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
            return False

    def iden(self):
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            (str): The SHA256 hash of the public key bytes.
        '''
        return hashlib.sha256(self.save()).hexdigest()

    @staticmethod
    def load(byts):
        return PubKey(c_ser.load_der_public_key(
                byts,
                backend=default_backend()))
