import json
import hashlib

import cryptography.hazmat.primitives.asymmetric.ec as c_ec
import cryptography.hazmat.primitives.asymmetric.rsa as c_rsa

import synapse.exc as s_exc

import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.utils as s_crypto

def _b64uint(text):
    # decode a JWK Base64urlUInt (RFC 7518 2) into a big-endian unsigned integer
    return int.from_bytes(s_crypto.debase64url(text), 'big')

def jwkToKey(jwk):
    '''
    Convert a JWK (RFC 7517) into a Synapse backend key wrapper.

    Args:
        jwk (dict): The JWK members.

    Returns:
        An s_rsa.PriKey/PubKey or s_ecc.PriKey/PubKey for an RSA or EC key. Raises s_exc.BadArg
        for an unsupported key type, a malformed member, or an off-curve EC point.
    '''
    if not isinstance(jwk, dict):
        raise s_exc.BadArg(mesg='JWK must be a mapping.')

    kty = jwk.get('kty')

    try:
        if kty == 'RSA':
            pubnums = c_rsa.RSAPublicNumbers(_b64uint(jwk['e']), _b64uint(jwk['n']))
            if 'd' in jwk:
                privnums = c_rsa.RSAPrivateNumbers(_b64uint(jwk['p']), _b64uint(jwk['q']),
                                                   _b64uint(jwk['d']), _b64uint(jwk['dp']),
                                                   _b64uint(jwk['dq']), _b64uint(jwk['qi']), pubnums)
                return s_rsa.PriKey(privnums.private_key())

            return s_rsa.PubKey(pubnums.public_key())

        if kty == 'EC':
            crv = jwk.get('crv')
            curvector = s_crypto.curves.get(crv.lower()) if isinstance(crv, str) else None
            if curvector is None:
                raise s_exc.BadArg(mesg=f'Unsupported JWK EC curve: {crv}', crv=crv)

            pubnums = c_ec.EllipticCurvePublicNumbers(_b64uint(jwk['x']), _b64uint(jwk['y']), curvector())
            if 'd' in jwk:
                privnums = c_ec.EllipticCurvePrivateNumbers(_b64uint(jwk['d']), pubnums)
                return s_ecc.PriKey(privnums.private_key())

            # public_key() validates that the point lies on the named curve (RFC 8725 3.4).
            return s_ecc.PubKey(pubnums.public_key())

    except (KeyError, TypeError, ValueError) as e:
        raise s_exc.BadArg(mesg=f'Malformed JWK: {e}') from None

    raise s_exc.BadArg(mesg=f'Unsupported JWK kty: {kty}', kty=kty)

def jwkThumbprint(jwk):
    '''
    Compute the RFC 7638 JWK SHA-256 thumbprint and return it as a base64url string.
    '''
    kty = jwk.get('kty')

    try:
        if kty == 'RSA':
            members = {'e': jwk['e'], 'kty': 'RSA', 'n': jwk['n']}
        elif kty == 'EC':
            members = {'crv': jwk['crv'], 'kty': 'EC', 'x': jwk['x'], 'y': jwk['y']}
        elif kty == 'oct':
            members = {'k': jwk['k'], 'kty': 'oct'}
        else:
            raise s_exc.BadArg(mesg=f'Unsupported JWK kty: {kty}', kty=kty)
    except KeyError as e:
        raise s_exc.BadArg(mesg=f'Malformed JWK: missing {e}') from None

    canon = json.dumps(members, separators=(',', ':'), sort_keys=True).encode('utf-8')
    return s_crypto.enbase64url(hashlib.sha256(canon).digest())
