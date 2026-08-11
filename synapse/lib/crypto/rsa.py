import hashlib

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.serialization as c_ser
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa
import cryptography.hazmat.primitives.asymmetric.padding as c_padding

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.utils as s_crypto

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

    def iden(self) -> str:
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            str: The SHA256 hash of the public key bytes.
        '''
        return self.publ.iden()

    def sign(self, byts, padding='pss', hashalgo='sha256', saltlen=None):
        '''
        Compute the RSA signature for the given bytestream.

        Args:
            byts (bytes): The bytes to sign.
            padding (str): The padding scheme, "pss" (default) or "pkcs1v15".
            hashalgo (str): The hash algorithm name (sha256, sha384, or sha512).
            saltlen: The PSS salt length in bytes, or None for the maximum length.

        Returns:
            bytes: The RSA signature bytes.
        '''
        hashobj = s_crypto.getHashByName(hashalgo)
        pad = s_crypto.getPaddingByName(padding, hashobj, saltlen=saltlen)
        return self.priv.sign(byts, pad, hashobj)

    def signitem(self, item) -> bytes:
        '''
        Compute the RSA signature for the given python primitive.

        Args:
            item: The item to sign. This will be flattened and msgpacked prior to signing.

        Returns:
            bytes: The RSA Signature bytes.
        '''
        byts = s_msgpack.en(s_common.flatten(item))
        return self.sign(byts)

    def decrypt(self, byts):
        '''
        Decrypt bytes which were encrypted with the corresponding public key.

        Args:
            byts (bytes): The ciphertext bytes to decrypt.

        Returns:
            bytes: The decrypted plaintext bytes.
        '''
        sha256 = c_hashes.SHA256()
        pad = c_padding.OAEP(mgf=c_padding.MGF1(sha256), algorithm=sha256, label=None)
        return self.priv.decrypt(byts, pad)

    def public(self):
        '''
        Get the PubKey which corresponds to the RSA PriKey.

        Returns:
            PubKey: A new PubKey object whose key corresponds to the private key.
        '''
        return PubKey(self.priv.public_key())

    @staticmethod
    def generate(bits=2048):
        '''
        Generate a new RSA PriKey instance.

        Args:
            bits (int): The size of the RSA key in bits.

        Returns:
            PriKey: A new PriKey instance.
        '''
        return PriKey(c_rsa.generate_private_key(
            public_exponent=65537,
            key_size=bits,
            backend=default_backend()))

    def dump(self, fmt='der'):
        '''
        Get the private key bytes in PKCS8 format.

        Args:
            fmt (str): The encoding format, "der" (default) or "pem".

        Returns:
            bytes: The encoded PKCS8 private key.
        '''
        return self.priv.private_bytes(
            encoding=s_crypto.getEncodingByName(fmt),
            format=c_ser.PrivateFormat.PKCS8,
            encryption_algorithm=c_ser.NoEncryption())

    @staticmethod
    def load(byts, fmt='der'):
        '''
        Create a PriKey instance from PKCS8 encoded bytes.

        Args:
            byts (bytes): Bytes to load.
            fmt (str): The encoding format, "der" (default) or "pem".

        Returns:
            PriKey: A new PriKey instance.
        '''
        s_crypto.getEncodingByName(fmt)
        if fmt.lower() == 'pem':
            priv = c_ser.load_pem_private_key(byts, password=None, backend=default_backend())
        else:
            priv = c_ser.load_der_private_key(byts, password=None, backend=default_backend())

        return PriKey(priv)

def loadKey(byts):
    '''
    Load a single RSA public or private key, auto-detecting the PEM vs DER
    encoding and whether the key is public or private.

    Args:
        byts (bytes): The DER or PEM encoded RSA key bytes.

    Returns:
        PriKey or PubKey: The loaded key wrapper.
    '''
    isprivate, key = s_crypto.loadKey(byts)
    if isprivate:
        if not isinstance(key, c_rsa.RSAPrivateKey):
            raise s_exc.BadArg(mesg='Key is not an RSA private key.')

        return PriKey(key)

    if not isinstance(key, c_rsa.RSAPublicKey):
        raise s_exc.BadArg(mesg='Key is not an RSA public key.')

    return PubKey(key)

class PubKey:
    '''
    A helper class for using RSA public keys.
    '''

    def __init__(self, publ):
        self.publ = publ  # type: c_rsa.RSAPublicKey

    def dump(self, fmt='der'):
        '''
        Get the public key bytes in SubjectPublicKeyInfo format.

        Args:
            fmt (str): The encoding format, "der" (default) or "pem".

        Returns:
            bytes: The encoded SubjectPublicKeyInfo public key.
        '''
        return self.publ.public_bytes(
            encoding=s_crypto.getEncodingByName(fmt),
            format=c_ser.PublicFormat.SubjectPublicKeyInfo)

    def verify(self, byts, sign, padding='pss', hashalgo='sha256', saltlen=None):
        '''
        Verify the signature for the given bytes using the RSA public key.

        Args:
            byts (bytes): The data bytes.
            sign (bytes): The signature bytes.
            padding (str): The padding scheme, "pss" (default) or "pkcs1v15".
            hashalgo (str): The hash algorithm name (sha256, sha384, or sha512).
            saltlen: The PSS salt length in bytes, or None for the maximum length.

        Returns:
            bool: True if the data was verified, False otherwise.
        '''
        hashobj = s_crypto.getHashByName(hashalgo)
        pad = s_crypto.getPaddingByName(padding, hashobj, saltlen=saltlen)
        try:
            self.publ.verify(sign, byts, pad, hashobj)
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

    def encrypt(self, byts):
        '''
        Encrypt bytes using the RSA public key.

        Args:
            byts (bytes): The plaintext bytes to encrypt.

        Returns:
            bytes: The encrypted ciphertext bytes.
        '''
        sha256 = c_hashes.SHA256()
        pad = c_padding.OAEP(mgf=c_padding.MGF1(sha256), algorithm=sha256, label=None)
        return self.publ.encrypt(byts, pad)

    def iden(self):
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            str: The SHA256 hash of the public key bytes.
        '''
        return hashlib.sha256(self.dump()).hexdigest()

    @staticmethod
    def load(byts, fmt='der'):
        '''
        Create a PubKey instance from SubjectPublicKeyInfo encoded bytes.

        Args:
            byts (bytes): Bytes to load.
            fmt (str): The encoding format, "der" (default) or "pem".

        Returns:
            PubKey: A new PubKey instance.
        '''
        s_crypto.getEncodingByName(fmt)
        if fmt.lower() == 'pem':
            publ = c_ser.load_pem_public_key(byts, backend=default_backend())
        else:
            publ = c_ser.load_der_public_key(byts, backend=default_backend())

        return PubKey(publ)
