
import hashlib

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.kdf.hkdf as c_hkdf
import cryptography.hazmat.primitives.asymmetric.ec as c_ec
import cryptography.hazmat.primitives.serialization as c_ser
import cryptography.hazmat.primitives.asymmetric.utils as c_utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

import synapse.exc as s_exc
import synapse.lib.crypto.utils as s_crypto


class PriKey:
    '''
    A helper class for using ECC private keys.
    '''
    def __init__(self, priv):
        self.priv = priv  # type: c_ec.EllipticCurvePrivateKey
        self.publ = PubKey(self.priv.public_key())

    def iden(self):
        '''
        Return a SHA256 hash for the public key (to be used as a GUID).

        Returns:
            str: The SHA256 hash of the public key bytes.
        '''
        return self.publ.iden()

    def sign(self, byts, hashalgo='sha256'):
        '''
        Compute the ECC signature for the given bytestream.

        Args:
            byts (bytes): The bytes to sign.
            hashalgo (str): The hash algorithm to use (sha256, sha384, or sha512).

        Returns:
            bytes: The DER encoded ECDSA signature bytes.
        '''
        chosen_hash = s_crypto.getHashByName(hashalgo)
        hasher = c_hashes.Hash(chosen_hash, default_backend())
        hasher.update(byts)
        digest = hasher.finalize()
        return self.priv.sign(digest,
                              c_ec.ECDSA(c_utils.Prehashed(chosen_hash))
                              )

    def exchange(self, pubkey):
        '''
        Perform a ECDH key exchange with a public key.

        Args:
            pubkey (PubKey): A PubKey to perform the ECDH with.

        Returns:
            bytes: The ECDH bytes. This is deterministic for a given pubkey
            and private key.
        '''
        try:
            return self.priv.exchange(c_ec.ECDH(), pubkey.publ)
        except ValueError as e:
            raise s_exc.BadEccExchange(mesg=str(e))

    def public(self):
        '''
        Get the PubKey which corresponds to the ECC PriKey.

        Returns:
            PubKey: A new PubKey object whose key corresponds to the private key.
        '''
        return PubKey(self.priv.public_key())

    @staticmethod
    def generate(curve='SECP384R1'):
        '''
        Generate a new ECC PriKey instance.

        Args:
            curve (str): The named curve to use. Defaults to SECP384R1.

        Returns:
            PriKey: A new PriKey instance.
        '''
        curveobj = s_crypto.getCurveByName(curve)

        return PriKey(c_ec.generate_private_key(
            curveobj,
            default_backend()
        ))

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

class PubKey:
    '''
    A helper class for using ECC public keys.
    '''

    def __init__(self, publ):
        self.publ = publ  # type: c_ec.EllipticCurvePublicKey

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

    def verify(self, byts, sign, hashalgo='sha256'):
        '''
        Verify the signature for the given bytes using the ECC
        public key.

        Args:
            byts (bytes): The data bytes.
            sign (bytes): The DER encoded signature bytes.
            hashalgo (str): The hash algorithm to use (sha256, sha384, or sha512).

        Returns:
            bool: True if the data was verified, False otherwise.
        '''
        try:
            chosen_hash = s_crypto.getHashByName(hashalgo)
            hasher = c_hashes.Hash(chosen_hash, default_backend())
            hasher.update(byts)
            digest = hasher.finalize()
            self.publ.verify(sign,
                             digest,
                             c_ec.ECDSA(c_utils.Prehashed(chosen_hash))
                             )
            return True
        except InvalidSignature:
            return False

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

def loadKey(byts):
    '''
    Load a single ECC public or private key, auto-detecting the PEM vs DER
    encoding and whether the key is public or private.

    Args:
        byts (bytes): The DER or PEM encoded ECC key bytes.

    Returns:
        PriKey or PubKey: The loaded key wrapper.
    '''
    isprivate, key = s_crypto.loadKey(byts)
    if isprivate:
        if not isinstance(key, c_ec.EllipticCurvePrivateKey):
            raise s_exc.BadArg(mesg='Key is not an ECC private key.')

        return PriKey(key)

    if not isinstance(key, c_ec.EllipticCurvePublicKey):
        raise s_exc.BadArg(mesg='Key is not an ECC public key.')

    return PubKey(key)

def doECDHE(statprv_u, statpub_v, ephmprv_u, ephmpub_v,
            length=64,
            salt=None,
            info=None):
    '''
    Perform one side of an Ecliptic Curve Diffie Hellman Ephemeral key exchange.

    Args:
        statprv_u (PriKey): Static Private Key for U
        statpub_v (PubKey: Static Public Key for V
        ephmprv_u (PriKey): Ephemeral Private Key for U
        ephmpub_v (PubKey): Ephemeral Public Key for V
        length (int): Number of bytes to return
        salt (bytes): Salt to use when computing the key.
        info (bytes): Additional information to use when computing the key.

    Notes:
        This makes no assumption about the reuse of the Ephemeral keys passed
        to the function. It is the caller's responsibility to destroy the keys
        after they are used for doing key generation. This implementation is
        the dhHybrid1 scheme described in NIST 800-56A Revision 2.

    Returns:
        bytes: The derived key.
    '''
    zs = statprv_u.exchange(statpub_v)
    ze = ephmprv_u.exchange(ephmpub_v)
    z = ze + zs
    kdf = c_hkdf.HKDF(c_hashes.SHA256(),
                      length=length,
                      salt=salt,
                      info=info,
                      backend=default_backend())
    k = kdf.derive(z)
    return k
