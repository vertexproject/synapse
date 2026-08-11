import base64

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.ec as c_ec
import cryptography.hazmat.primitives.serialization as c_ser
import cryptography.hazmat.primitives.asymmetric.padding as c_padding
from cryptography.hazmat.backends import default_backend

import synapse.exc as s_exc

hashes = {
    'sha256': c_hashes.SHA256,
    'sha384': c_hashes.SHA384,
    'sha512': c_hashes.SHA512,
}

encodings = {
    'der': c_ser.Encoding.DER,
    'pem': c_ser.Encoding.PEM,
}

curves = {
    'p-256': c_ec.SECP256R1,
    'secp256r1': c_ec.SECP256R1,
    'p-384': c_ec.SECP384R1,
    'secp384r1': c_ec.SECP384R1,
    'p-521': c_ec.SECP521R1,
    'secp521r1': c_ec.SECP521R1,
}

def enbase64url(byts):
    # base64url-encode bytes without padding (the JOSE convention, RFC 7515 2).
    return base64.urlsafe_b64encode(byts).rstrip(b'=').decode('ascii')

def debase64url(text):
    # strict base64url decode: reject any non-urlsafe character (whitespace, '+', '/') rather
    # than silently discarding it, so every JOSE segment is exactly its canonical base64url
    # form. This closes a token-malleability gap where whitespace in the signature segment,
    # which is not part of the signing input, was ignored and the token still verified.
    if isinstance(text, str):
        text = text.encode('ascii')

    return base64.b64decode(text + b'=' * (-len(text) % 4), altchars=b'-_', validate=True)

def getHashByName(hashalgo):
    '''
    Get an instantiated cryptography hash for the given algorithm name.

    Args:
        hashalgo (str): The hash algorithm name (sha256, sha384, or sha512).

    Returns:
        The instantiated hash algorithm.
    '''
    ctor = hashes.get(hashalgo.lower())
    if ctor is None:
        raise s_exc.BadArg(mesg=f'Invalid hash algorithm: {hashalgo}', hashalgo=hashalgo)

    return ctor()

def getEncodingByName(fmt):
    '''
    Get the cryptography serialization Encoding for the given format name.

    Args:
        fmt (str): The encoding format, "der" or "pem".

    Returns:
        The cryptography Encoding.
    '''
    enc = encodings.get(fmt.lower())
    if enc is None:
        raise s_exc.BadArg(mesg=f'Invalid key encoding format: {fmt}', fmt=fmt)

    return enc

def getCurveByName(name):
    '''
    Get an instantiated cryptography elliptic curve for the given curve name.

    Args:
        name (str): The named curve (P-256, P-384, or P-521).

    Returns:
        The instantiated elliptic curve.
    '''
    ctor = curves.get(name.lower())
    if ctor is None:
        raise s_exc.BadArg(mesg=f'Invalid ECC curve: {name}', curve=name)

    return ctor()

def loadKey(byts):
    '''
    Load a single public or private key, auto-detecting the PEM vs DER encoding
    and whether the key is a public or private key.

    Args:
        byts (bytes): The DER or PEM encoded key bytes.

    Returns:
        A ``(isprivate, key)`` tuple where ``key`` is the loaded cryptography key object.
    '''
    if b'-----BEGIN' in byts:
        if byts.count(b'-----BEGIN') != 1:
            raise s_exc.BadArg(mesg='Expected a single PEM encoded key.')

        try:
            return (True, c_ser.load_pem_private_key(byts, password=None, backend=default_backend()))
        except ValueError:
            return (False, c_ser.load_pem_public_key(byts, backend=default_backend()))

    try:
        return (True, c_ser.load_der_private_key(byts, password=None, backend=default_backend()))
    except ValueError:
        return (False, c_ser.load_der_public_key(byts, backend=default_backend()))

def getPaddingByName(padding, hashobj, saltlen=None):
    '''
    Get the cryptography asymmetric padding for the given scheme name.

    Args:
        padding (str): The padding scheme, "pss" or "pkcs1v15".
        hashobj: The instantiated hash used to construct MGF1 for PSS padding.
        saltlen: The PSS salt length in bytes. Defaults to the maximum length; callers
                 that require a specific salt length (e.g. the JWS PS* algorithms, which
                 mandate salt length equal to the digest length) may pass an integer.

    Returns:
        The cryptography padding object.
    '''
    padding = padding.lower()
    if padding == 'pkcs1v15':
        return c_padding.PKCS1v15()

    if padding == 'pss':
        if saltlen is None:
            saltlen = c_padding.PSS.MAX_LENGTH

        return c_padding.PSS(c_padding.MGF1(hashobj), saltlen)

    raise s_exc.BadArg(mesg=f'Invalid padding scheme: {padding}', padding=padding)
