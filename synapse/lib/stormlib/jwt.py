import hmac
import socket
import asyncio
import ipaddress
import urllib.parse

import aiohttp
import aiohttp_socks

import cryptography.hazmat.primitives.asymmetric.utils as c_utils

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.jwk as s_jwk
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.utils as s_crypto
import synapse.lib.schemas as s_schemas
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.stormlib.cryptoutils as s_cryptoutils

# JWKS fetch/cache tuning.
JWKS_TTL = 300              # seconds a fetched JWKS is served from cache
JWKS_TIMEOUT = 10           # seconds for the JWKS HTTPS fetch
JWKS_MAX_BYTES = 256 * 1024  # maximum JWKS response body size
JWKS_CACHE_MAX = 128        # maximum distinct jwks_uri entries cached per Cortex

# Minimum RSA modulus size (bits) accepted for RS*/PS* signing and verification.
RSA_MIN_BITS = 2048

# Supported JWS algorithms and their crypto parameters. The "none" algorithm is
# intentionally absent and unsupported. JWE decryption is not supported. The HMAC
# "minkey" is the RFC 7518 3.2 minimum secret length (equal to the hash output size).
jwtalgs = {
    'HS256': {'kind': 'hmac', 'hash': 'sha256', 'minkey': 32},
    'HS384': {'kind': 'hmac', 'hash': 'sha384', 'minkey': 48},
    'HS512': {'kind': 'hmac', 'hash': 'sha512', 'minkey': 64},
    'RS256': {'kind': 'rsa', 'hash': 'sha256'},
    'RS384': {'kind': 'rsa', 'hash': 'sha384'},
    'RS512': {'kind': 'rsa', 'hash': 'sha512'},
    # RSASSA-PSS: RFC 7518 3.5 mandates a salt length equal to the digest length.
    'PS256': {'kind': 'rsa-pss', 'hash': 'sha256', 'saltlen': 32},
    'PS384': {'kind': 'rsa-pss', 'hash': 'sha384', 'saltlen': 48},
    'PS512': {'kind': 'rsa-pss', 'hash': 'sha512', 'saltlen': 64},
    'ES256': {'kind': 'ecc', 'hash': 'sha256', 'curve': 'secp256r1', 'coordlen': 32},
    'ES384': {'kind': 'ecc', 'hash': 'sha384', 'curve': 'secp384r1', 'coordlen': 48},
    'ES512': {'kind': 'ecc', 'hash': 'sha512', 'curve': 'secp521r1', 'coordlen': 66},
}

# defensive upper bound on a base64url header segment before we decode/parse it
MAX_HEADER_B64 = 65536

def _reqAlg(alg):
    info = jwtalgs.get(alg)
    if info is None:
        raise s_exc.BadArg(mesg=f'Invalid or unsupported JWT algorithm: {alg}', alg=alg)

    return info

def _reqAlgs(algorithms):
    if not isinstance(algorithms, (list, tuple)):
        raise s_exc.BadArg(mesg='algorithms must be a list of strings.')

    algs = set()
    for alg in algorithms:
        if not isinstance(alg, str):
            raise s_exc.BadArg(mesg='algorithms must be a list of strings.')

        _reqAlg(alg)
        algs.add(alg)

    if not algs:
        raise s_exc.BadArg(mesg='At least one algorithm must be provided.')

    return algs

def _reqEccCurve(keyname, info, alg):
    if keyname != info['curve']:
        mesg = f'ECC key curve {keyname} does not match the curve required for JWT algorithm {alg}.'
        raise s_exc.BadArg(mesg=mesg, alg=alg)

def _reqHmacKey(key, info):
    # positive key-type binding: an asymmetric key (a PEM, or a crypto:*:key which toprims
    # to a PEM) must never be accepted as an HMAC secret. This closes the RS256->HS256
    # confusion footgun even when a caller misconfigures the algorithm allowlist.
    if b'-----BEGIN' in key:
        raise s_exc.BadArg(mesg='An asymmetric key may not be used with an HMAC (HS*) algorithm.')

    if len(key) < info['minkey']:
        raise s_exc.BadArg(mesg=f'The HMAC secret must be at least {info["minkey"]} bytes for this algorithm.')

def _reqRsaBits(bits):
    if bits < RSA_MIN_BITS:
        raise s_exc.BadArg(mesg=f'RSA keys must be at least {RSA_MIN_BITS} bits, got {bits}.', bits=bits)

def _reqValidClaims(payload):
    # validate the registered claims of a full payload; custom claims are unconstrained
    # (additionalProperties is True) and non-JSON-safe values are caught at serialization.
    try:
        s_schemas.reqValidJwtClaims(payload)
    except s_exc.SchemaViolation as e:
        raise s_exc.BadArg(mesg=f'Invalid JWT payload: {e}') from None

def _makeSig(alg, info, key, signin):
    kind = info['kind']
    hashalg = info['hash']

    if kind == 'hmac':
        _reqHmacKey(key, info)
        return hmac.new(key, signin, digestmod=hashalg).digest()

    if kind == 'rsa':
        prikey = s_cryptoutils.loadRsaPriv(key)
        _reqRsaBits(prikey.priv.key_size)
        return prikey.sign(signin, padding='pkcs1v15', hashalgo=hashalg)

    if kind == 'rsa-pss':
        prikey = s_cryptoutils.loadRsaPriv(key)
        _reqRsaBits(prikey.priv.key_size)
        return prikey.sign(signin, padding='pss', hashalgo=hashalg, saltlen=info['saltlen'])

    try:
        prikey = s_ecc.PriKey.load(key, fmt='pem')
    except s_cryptoutils._loaderrors as e:
        raise s_exc.BadArg(mesg=f'Invalid ECC private key: {e}') from None

    _reqEccCurve(prikey.priv.curve.name, info, alg)
    der = prikey.sign(signin, hashalgo=hashalg)
    r, s = c_utils.decode_dss_signature(der)
    coordlen = info['coordlen']
    return r.to_bytes(coordlen, 'big') + s.to_bytes(coordlen, 'big')

def _checkSig(alg, info, key, signin, signature):
    kind = info['kind']
    hashalg = info['hash']

    if kind == 'hmac':
        _reqHmacKey(key, info)
        expected = hmac.new(key, signin, digestmod=hashalg).digest()
        return hmac.compare_digest(expected, signature)

    if kind == 'rsa':
        pubkey = s_cryptoutils.loadRsaPub(key)
        _reqRsaBits(pubkey.publ.key_size)
        return pubkey.verify(signin, signature, padding='pkcs1v15', hashalgo=hashalg)

    if kind == 'rsa-pss':
        pubkey = s_cryptoutils.loadRsaPub(key)
        _reqRsaBits(pubkey.publ.key_size)
        return pubkey.verify(signin, signature, padding='pss', hashalgo=hashalg, saltlen=info['saltlen'])

    try:
        pubkey = s_ecc.PubKey.load(key, fmt='pem')
    except s_cryptoutils._loaderrors as e:
        raise s_exc.BadArg(mesg=f'Invalid ECC public key: {e}') from None

    _reqEccCurve(pubkey.publ.curve.name, info, alg)

    coordlen = info['coordlen']
    if len(signature) != coordlen * 2:
        return False

    r = int.from_bytes(signature[:coordlen], 'big')
    s = int.from_bytes(signature[coordlen:], 'big')
    der = c_utils.encode_dss_signature(r, s)
    return pubkey.verify(signin, der, hashalgo=hashalg)

def _splitToken(text):
    '''
    Split a JWS into its (protected, payload, signature) base64url segments, accepting
    either the compact serialization or the flattened JWS JSON serialization. Raises
    BadArg on a JWE (5-segment compact or a JSON object carrying ``ciphertext``) and on
    the general (multi-signature) JSON serialization.
    '''
    stripped = text.lstrip()
    if stripped[:1] in ('{', '['):
        try:
            obj = s_json.loads(stripped.encode())
        except (ValueError, TypeError, s_exc.BadJsonText) as e:
            raise s_exc.BadArg(mesg=f'Unable to decode JWS JSON: {e}') from None

        if not isinstance(obj, dict):
            raise s_exc.BadArg(mesg='JWS JSON serialization must be an object.')

        if 'ciphertext' in obj:
            raise s_exc.BadArg(mesg='input is a JWE; JWE decryption is not supported.')

        if 'signatures' in obj:
            raise s_exc.BadArg(mesg='General JWS JSON serialization is not supported; use the flattened form.')

        prot = obj.get('protected')
        p64 = obj.get('payload')
        s64 = obj.get('signature')
        if not (isinstance(prot, str) and isinstance(p64, str) and isinstance(s64, str)):
            raise s_exc.BadArg(mesg='Flattened JWS JSON must contain string protected, payload, and signature members.')

        return (prot, p64, s64)

    parts = text.split('.')
    if len(parts) == 5:
        raise s_exc.BadArg(mesg='input is a JWE; JWE decryption is not supported.')

    if len(parts) != 3 or not all(parts):
        raise s_exc.BadArg(mesg='JWT must contain three non-empty segments.')

    return (parts[0], parts[1], parts[2])

def _decodeJws(text, algs):
    '''
    Decode and validate the structure of a JWS without checking its signature, returning
    (h64, p64, header, payload, signature, alg, info). Raises BadArg on any failure. The
    signature is checked separately after the verification key has been resolved.
    '''
    h64, p64, s64 = _splitToken(text)

    try:
        header = s_json.loads(s_crypto.debase64url(h64))
        payload = s_json.loads(s_crypto.debase64url(p64))
        signature = s_crypto.debase64url(s64)
    except (ValueError, TypeError, s_exc.BadJsonText) as e:
        raise s_exc.BadArg(mesg=f'Unable to decode JWT: {e}') from None

    if not isinstance(header, dict):
        raise s_exc.BadArg(mesg='JWT header must be a JSON object.')

    if not isinstance(payload, dict):
        raise s_exc.BadArg(mesg='JWT payload must be a JSON object.')

    # RFC 7515 4.1.11: a crit header lists parameters that MUST be understood. We implement
    # no extensions, so any non-empty crit is unsupported and the token must be rejected.
    if header.get('crit'):
        raise s_exc.BadArg(mesg='JWT contains an unsupported crit header parameter.', crit=header.get('crit'))

    alg = header.get('alg')
    if not isinstance(alg, str):
        raise s_exc.BadArg(mesg='JWT header is missing a string alg.')

    if alg not in algs:
        raise s_exc.BadArg(mesg=f'JWT alg {alg} is not in the list of allowed algorithms.', alg=alg)

    info = _reqAlg(alg)

    return (h64, p64, header, payload, signature, alg, info)

def _reqNumericDate(valu, name):
    # NumericDate (RFC 7519 2) is a JSON number of epoch seconds. A bool is a JSON number
    # in Python's eyes but is never a valid date, so exclude it explicitly.
    if isinstance(valu, bool) or not isinstance(valu, (int, float)):
        raise s_exc.BadArg(mesg=f'JWT {name} claim must be a number.', claim=name)

def _checkAudience(aud, audience):
    # RFC 7519 4.1.3: the principal must identify itself with a value in aud. A falsy aud
    # (absent, empty string, or empty list) carries no value to match, so the token is rejected
    # when audience validation is requested.
    if not aud:
        raise s_exc.BadArg(mesg='JWT has no aud claim value to match the expected audience.')

    tokauds = set(aud) if isinstance(aud, (list, tuple)) else {aud}
    wants = set(audience) if isinstance(audience, (list, tuple)) else {audience}
    if not (tokauds & wants):
        raise s_exc.BadArg(mesg='JWT aud does not match the expected audience.')

def _checkMatch(valu, expected, name):
    # a str expected value is an exact match; a list/tuple is a membership test. Never a
    # substring test (RFC 8725 / CVE-2024-53861).
    if isinstance(expected, (list, tuple)):
        if valu not in expected:
            raise s_exc.BadArg(mesg=f'JWT {name} does not match any expected value.', claim=name)
    elif valu != expected:
        raise s_exc.BadArg(mesg=f'JWT {name} does not match the expected value.', claim=name)

def _checkClaims(payload, header, nowsecs, audience, issuer, subject, leeway, typ, requiredclaims, options):
    '''
    Apply the RFC 7519 claim checks. Raises BadArg on any failure. exp/nbf/iat are validated
    automatically whenever present (secure-by-default); aud/iss/sub are validated only when
    the caller supplies an expected value. Each check may be disabled via the options dict.
    '''
    for name in requiredclaims:
        if name not in payload:
            raise s_exc.BadArg(mesg=f'JWT is missing required claim: {name}', claim=name)

    if typ is not None and header.get('typ') != typ:
        raise s_exc.BadArg(mesg=f'JWT typ {header.get("typ")} does not match the expected typ {typ}.')

    if options.get('verify_exp', True) and 'exp' in payload:
        exp = payload['exp']
        _reqNumericDate(exp, 'exp')
        if nowsecs - leeway >= exp:
            raise s_exc.BadArg(mesg='JWT has expired.')

    if options.get('verify_nbf', True) and 'nbf' in payload:
        nbf = payload['nbf']
        _reqNumericDate(nbf, 'nbf')
        if nowsecs + leeway < nbf:
            raise s_exc.BadArg(mesg='JWT is not yet valid (nbf).')

    if options.get('verify_iat', True) and 'iat' in payload:
        _reqNumericDate(payload['iat'], 'iat')

    if options.get('verify_aud', True) and audience is not None:
        _checkAudience(payload.get('aud'), audience)

    if options.get('verify_iss', True) and issuer is not None:
        _checkMatch(payload.get('iss'), issuer, 'iss')

    if options.get('verify_sub', True) and subject is not None:
        _checkMatch(payload.get('sub'), subject, 'sub')

def _reqSafeUrl(url):
    '''
    Require the https scheme for a jwks_uri and return its (host, port). Raises BadArg on a
    non-https URL or a URL with no host. This is a cheap, synchronous check with no DNS.
    '''
    info = urllib.parse.urlparse(url)
    if info.scheme != 'https':
        raise s_exc.BadArg(mesg='jwks_uri must be an https URL.', url=url)

    if not info.hostname:
        raise s_exc.BadArg(mesg='jwks_uri is missing a host.', url=url)

    return info.hostname, info.port or 443

async def _resolveJwksHost(host, port):
    '''
    Resolve a jwks_uri host asynchronously (so the ioloop is never blocked on DNS) and return the
    getaddrinfo records so the caller can dial exactly the resolved addresses and avoid a
    DNS-rebinding TOCTOU. A resolution failure is transient, so the caller may serve a stale cache
    entry rather than hard-fail.
    '''
    loop = asyncio.get_running_loop()
    try:
        return await loop.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as e:
        raise s_exc.BadArg(mesg=f'Unable to resolve jwks_uri host: {e}', url=host) from None

def _reqGlobalAddrs(host, sockaddrs, allowinternal):
    '''
    Unless allowinternal is set, reject any non-global address (loopback, link-local, private, or a
    cloud metadata endpoint). This is a policy rejection rather than a transient failure, so it
    always hard-fails and never falls back to a stale cache entry.
    '''
    if allowinternal:
        return

    # sockaddrs are getaddrinfo (family, socktype, proto, canonname, sockaddr) tuples; element 0
    # of each trailing sockaddr is the resolved IP string (IPv4 and IPv6 alike).
    for *_, sockaddr in sockaddrs:
        ipaddr = ipaddress.ip_address(sockaddr[0])
        if not ipaddr.is_global:
            mesg = f'jwks_uri resolves to the non-global address {ipaddr}; set allowinternal to override.'
            raise s_exc.BadArg(mesg=mesg, host=host)

class _PinnedResolver(aiohttp.abc.AbstractResolver):
    '''
    An aiohttp resolver that returns only the addresses already resolved and vetted, so the
    connection dials exactly the checked IPs rather than re-resolving (which a DNS-rebinding
    host could answer differently).
    '''
    def __init__(self, addrs):
        self.addrs = addrs

    async def resolve(self, host, port=0, family=socket.AF_UNSPEC):
        results = []
        for fam, _, _, _, sockaddr in self.addrs:
            if family in (socket.AF_UNSPEC, fam):
                results.append({'hostname': host, 'host': sockaddr[0], 'port': port,
                                'family': fam, 'proto': socket.IPPROTO_TCP, 'flags': socket.AI_NUMERICHOST})

        return results

    async def close(self):
        pass

def _kidInSet(jwkset, kid):
    # whether a JWKS (already validated to carry a keys list) contains a key with this kid
    return any(isinstance(k, dict) and k.get('kid') == kid for k in jwkset.get('keys', ()))

def _pickJwk(jwkobj, header):
    # select a single JWK from a JWK or a JWKS (by the token kid) for verification
    if 'keys' not in jwkobj:
        return jwkobj

    keys = jwkobj.get('keys')
    if not isinstance(keys, (list, tuple)):
        raise s_exc.BadArg(mesg='JWKS keys must be a list.')

    cands = [k for k in keys if isinstance(k, dict)]

    kid = header.get('kid')
    if kid is not None:
        matched = [k for k in cands if k.get('kid') == kid]
        if len(matched) != 1:
            raise s_exc.BadArg(mesg=f'JWKS does not contain exactly one key with kid {kid}.', kid=kid)

        return matched[0]

    if len(cands) != 1:
        raise s_exc.BadArg(mesg='JWKS contains multiple keys but the token has no kid to select one.')

    return cands[0]

def _selectJwk(jwkobj, header, alg):
    '''
    Resolve the verification key bytes from a JWK or JWKS for the given algorithm. Returns
    PEM bytes for RS*/PS*/ES* and the raw secret bytes for HS*. Raises BadArg on a key that
    does not match the algorithm family.
    '''
    kind = jwtalgs[alg]['kind']
    jwk = _pickJwk(jwkobj, header)
    kty = jwk.get('kty')

    if kind == 'hmac':
        if kty != 'oct' or not isinstance(jwk.get('k'), str):
            raise s_exc.BadArg(mesg=f'JWK kty {kty} does not match the HMAC algorithm {alg}.')

        try:
            return s_crypto.debase64url(jwk['k'])
        except (ValueError, TypeError) as e:
            raise s_exc.BadArg(mesg=f'Invalid HMAC JWK k value: {e}') from None

    keyobj = s_jwk.jwkToKey(jwk)

    if kind in ('rsa', 'rsa-pss'):
        if not isinstance(keyobj, (s_rsa.PriKey, s_rsa.PubKey)):
            raise s_exc.BadArg(mesg=f'JWK is not an RSA key for algorithm {alg}.')

        pubkey = keyobj.public() if isinstance(keyobj, s_rsa.PriKey) else keyobj
        return pubkey.dump(fmt='pem')

    if not isinstance(keyobj, (s_ecc.PriKey, s_ecc.PubKey)):
        raise s_exc.BadArg(mesg=f'JWK is not an EC key for algorithm {alg}.')

    pubkey = keyobj.public() if isinstance(keyobj, s_ecc.PriKey) else keyobj
    return pubkey.dump(fmt='pem')

def _decodeHeader(h64):
    if len(h64) > MAX_HEADER_B64:
        raise s_exc.BadArg(mesg='JWT header segment is too large.')

    try:
        header = s_json.loads(s_crypto.debase64url(h64))
    except (ValueError, TypeError, s_exc.BadJsonText) as e:
        raise s_exc.BadArg(mesg=f'Unable to decode JWT header: {e}') from None

    if not isinstance(header, dict):
        raise s_exc.BadArg(mesg='JWT header must be a JSON object.')

    return header

def _parseToken(text):
    '''
    Key-free structural parse: report whether a token is a JWS or a JWE and decode only
    its protected header. Does no signature check and no decryption.
    '''
    stripped = text.lstrip()
    if stripped[:1] in ('{', '['):
        try:
            obj = s_json.loads(stripped.encode())
        except (ValueError, TypeError, s_exc.BadJsonText) as e:
            raise s_exc.BadArg(mesg=f'Unable to decode JOSE JSON: {e}') from None

        if not isinstance(obj, dict):
            raise s_exc.BadArg(mesg='JOSE JSON serialization must be an object.')

        if 'ciphertext' in obj:
            typ = 'JWE'
            prot = obj.get('protected')
        elif 'signatures' in obj:
            typ = 'JWS'
            sigs = obj.get('signatures')
            prot = sigs[0].get('protected') if isinstance(sigs, list) and sigs and isinstance(sigs[0], dict) else None
        elif 'signature' in obj:
            typ = 'JWS'
            prot = obj.get('protected')
        else:
            raise s_exc.BadArg(mesg='Unrecognized JOSE JSON serialization.')

        header = _decodeHeader(prot) if isinstance(prot, str) and prot else {}
        return {'typ': typ, 'header': header}

    parts = text.split('.')
    if len(parts) == 3:
        typ = 'JWS'
    elif len(parts) == 5:
        typ = 'JWE'
    else:
        raise s_exc.BadArg(mesg='Unrecognized compact JOSE serialization.')

    return {'typ': typ, 'header': _decodeHeader(parts[0])}

@s_stormtypes.registry.registerLib
class LibJwt(s_stormtypes.Lib):
    '''
    A Storm library for constructing, signing, and verifying JSON Web Tokens (JWTs).
    '''
    _storm_locals = (
        {'name': 'generate', 'desc': '''
        Construct a new unsigned ``crypto:jwt`` object.

        Examples:
            Construct a token, set a claim, and sign it::

                $key = $lib.crypto.rsa.generate()
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "1234567890"
                $jwtstr = $token.sign($key, "RS256")
        ''',
         'type': {'type': 'function', '_funcname': '_generate',
                  'args': (
                      {'name': 'payload', 'type': 'dict', 'default': None,
                       'desc': 'An optional dictionary to use as the initial claims payload.'},
                  ),
                  'returns': {'type': 'crypto:jwt', 'desc': 'The newly constructed crypto:jwt object.'}}},

        {'name': 'verify', 'desc': '''
        Verify a JWT and return a ``crypto:jwt`` object.

        The ``algorithms`` list is a required allowlist. The algorithm named in the token header must be
        present in the allowlist or verification fails. This is the primary mitigation against JWT algorithm
        confusion attacks. The ``none`` algorithm is never supported. Both the compact and the flattened
        JWS JSON serializations are accepted.

        The ``exp``, ``nbf``, and ``iat`` claims are validated automatically whenever they are present. The
        ``audience``, ``issuer``, and ``subject`` claims are validated when a corresponding expected value
        is provided. Each of these checks may be disabled via the ``options`` dictionary.

        The ``key`` may be a PEM key, an HMAC secret, a crypto:rsa:key / crypto:ecc:key object, or a JWK /
        JWKS dictionary (a JWKS is selected by the token ``kid``). If ``key`` is null and a ``jwks_uri`` is
        provided, the key set is fetched over HTTPS (respecting ``ssl_verify``, ``ssl_opts``, and ``proxy``) and cached. The
        token header ``jku`` / ``x5u`` / ``jwk`` are never followed.

        Examples:
            Verify a token and use the returned object::

                ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $key.pubkey(), ("RS256",), audience="myapp")
                if $ok { $lib.print($valu.payload.sub) }
        ''',
         'type': {'type': 'function', '_funcname': '_verify',
                  'args': (
                      {'name': 'token', 'type': 'str', 'desc': 'The JWT string to verify.'},
                      {'name': 'key', 'type': ['str', 'bytes', 'dict', 'crypto:rsa:key', 'crypto:ecc:key'],
                       'desc': 'The verification key: a PEM public key (or crypto:rsa:key / crypto:ecc:key) '
                               'for RS* / PS* / ES*, an HMAC secret for HS*, a JWK / JWKS dictionary, or '
                               'null to resolve the key via jwks_uri.'},
                      {'name': 'algorithms', 'type': 'list',
                       'desc': 'The required allowlist of acceptable JWS algorithms.'},
                      {'name': 'audience', 'type': ['str', 'list'], 'default': None,
                       'desc': 'The expected audience. The token aud claim must contain at least one match.'},
                      {'name': 'issuer', 'type': ['str', 'list'], 'default': None,
                       'desc': 'The expected issuer. A str is an exact match; a list is a membership test.'},
                      {'name': 'subject', 'type': 'str', 'default': None,
                       'desc': 'The expected subject, compared for exact equality with the sub claim.'},
                      {'name': 'leeway', 'type': 'int', 'default': 0,
                       'desc': 'Seconds of clock-skew leeway applied to the exp and nbf checks.'},
                      {'name': 'typ', 'type': 'str', 'default': None,
                       'desc': 'An expected header typ value to require (e.g. "JWT" or "at+jwt").'},
                      {'name': 'requiredclaims', 'type': 'list', 'default': None,
                       'desc': 'Claim names that must be present in the payload (presence only, not value).'},
                      {'name': 'options', 'type': 'dict', 'default': None,
                       'desc': 'Toggles for verify_exp, verify_nbf, verify_iat, verify_aud, verify_iss, '
                               'and verify_sub. Each defaults to true.'},
                      {'name': 'jwks_uri', 'type': 'str', 'default': None,
                       'desc': 'An https URL to fetch the JWKS from when key is null. The result is cached.'},
                      {'name': 'ssl_verify', 'type': 'boolean', 'default': True,
                       'desc': 'Perform SSL/TLS verification.'},
                      {'name': 'ssl_opts', 'type': 'dict', 'default': None,
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.'},
                      {'name': 'proxy', 'type': ['boolean', 'str'], 'default': True,
                       'desc': 'Proxy configuration for the jwks_uri fetch (same as $lib.inet.http).'},
                      {'name': 'allowinternal', 'type': 'boolean', 'default': False,
                       'desc': 'Allow a jwks_uri that resolves to a loopback / private / link-local address.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'An ($ok, $valu) tuple. On success $valu is a verified crypto:jwt '
                                      'object; on failure $valu is a dictionary of error information.'}}},

        {'name': 'parse', 'desc': '''
        Structurally parse a token without a key, reporting whether it is a JWS or a JWE and decoding only
        its protected header. This performs no signature verification and no decryption.
        ''',
         'type': {'type': 'function', '_funcname': '_parse',
                  'args': (
                      {'name': 'token', 'type': 'str', 'desc': 'The compact or JSON serialized token.'},
                  ),
                  'returns': {'type': 'dict',
                              'desc': 'A dictionary with ``typ`` ("JWS" or "JWE") and the decoded ``header``.'}}},

        {'name': 'algorithms', 'desc': 'The list of JWS algorithms supported by the JWT functionality.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorAlgorithms',
                  'returns': {'type': 'list', 'desc': 'A list of the supported JWS algorithm names.'}}},
    )
    _storm_lib_path = ('crypto', 'jwt')

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name=name)
        self.gtors['algorithms'] = self._gtorAlgorithms

    def getObjLocals(self):
        return {
            'parse': self._parse,
            'verify': self._verify,
            'generate': self._generate,
        }

    async def _gtorAlgorithms(self):
        return list(jwtalgs)

    @s_stormtypes.stormfunc(readonly=True)
    async def _generate(self, payload=None):
        payload = await s_stormtypes.toprim(payload)
        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise s_exc.BadArg(mesg='The JWT payload must be a dictionary.')

        if not all(isinstance(k, str) for k in payload):
            raise s_exc.BadArg(mesg='JWT claim names must be strings.')

        _reqValidClaims(payload)

        return Jwt(self.runt, payload=payload)

    async def _fetchJwks(self, url, host, addrs, ssl_verify, ssl_opts, proxy):
        # HTTPS GET of a JWKS document from the pre-vetted addresses; returns the parsed set.
        sslctx = self.runt.snap.core.getCachedSslCtx(opts=ssl_opts, verify=ssl_verify)

        proxyurl = await s_stormtypes.resolveCoreProxyUrl(proxy)
        if proxyurl is not None:
            # the proxy performs the connect; the local address vetting still ran.
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)
        else:
            # dial only the resolved and vetted addresses (defeats DNS-rebinding).
            connector = aiohttp.TCPConnector(resolver=_PinnedResolver(addrs))

        timeout = aiohttp.ClientTimeout(total=JWKS_TIMEOUT)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
            async with sess.get(url, ssl=sslctx, allow_redirects=False) as resp:

                if resp.status != 200:
                    raise s_exc.BadArg(mesg=f'JWKS endpoint returned HTTP {resp.status}.', status=resp.status)

                total = 0
                chunks = []
                async for chunk in resp.content.iter_chunked(65536):
                    total += len(chunk)
                    if total > JWKS_MAX_BYTES:
                        raise s_exc.BadArg(mesg='JWKS response exceeds the maximum allowed size.')

                    chunks.append(chunk)

                byts = b''.join(chunks)

        try:
            data = s_json.loads(byts)
        except (ValueError, TypeError, s_exc.BadJsonText) as e:
            raise s_exc.BadArg(mesg=f'Unable to decode JWKS JSON: {e}') from None

        if not isinstance(data, dict) or not isinstance(data.get('keys'), list):
            raise s_exc.BadArg(mesg='A JWKS must be an object with a keys array.')

        return data

    async def _getJwks(self, url, ssl_verify, ssl_opts, proxy, allowinternal, refresh):
        # fetch a JWKS with a per-Cortex TTL cache, per-uri single-flight, and serve-stale on
        # a failed refresh so a transient JWKS outage does not break verification outright.
        core = self.runt.snap.core
        cache = core.jwkscache
        locks = core.jwkslocks

        if not refresh:
            entry = cache.get(url)
            if entry is not None and s_common.now() / 1000 < entry[0]:
                return entry[1]

        # Validate and resolve the URL BEFORE taking a lock, so a rejected or unresolvable URL
        # leaves no permanent lock residue. Resolution is async so the ioloop is never blocked.
        host, port = _reqSafeUrl(url)
        try:
            addrs = await _resolveJwksHost(host, port)
        except s_exc.BadArg:
            # a transient resolution failure serves a present (stale) cache entry, matching the
            # failed-refresh path below, so a DNS blip does not break verification outright.
            entry = cache.get(url)
            if entry is not None:
                return entry[1]

            raise

        # a non-global address is a policy rejection, not a transient failure: it always hard-fails
        # and never serves stale.
        _reqGlobalAddrs(host, addrs, allowinternal)

        # Bound the per-Cortex maps: drop unlocked locks whose URL is no longer cached before
        # adding a new one, so failed/rotating URLs cannot accrete unbounded lock objects.
        if len(locks) >= JWKS_CACHE_MAX:
            for stale in [u for u in locks if u not in cache and not locks[u].locked()]:
                locks.pop(stale, None)

        lock = locks.setdefault(url, asyncio.Lock())
        async with lock:

            if not refresh:
                entry = cache.get(url)
                if entry is not None and s_common.now() / 1000 < entry[0]:
                    return entry[1]

            try:
                jwkset = await self._fetchJwks(url, host, addrs, ssl_verify, ssl_opts, proxy)
            except Exception:
                entry = cache.get(url)
                if entry is not None:
                    return entry[1]

                raise

            cache[url] = (s_common.now() / 1000 + JWKS_TTL, jwkset)

            # cap the cache by evicting the soonest-to-expire other entries (and their locks).
            while len(cache) > JWKS_CACHE_MAX:
                victim = min((u for u in cache if u != url), key=lambda u: cache[u][0], default=None)
                if victim is None:
                    break

                cache.pop(victim, None)
                if victim in locks and not locks[victim].locked():
                    locks.pop(victim, None)

            return jwkset

    async def _resolveKey(self, key, header, alg, jwks_uri, ssl_verify, ssl_opts, proxy, allowinternal):
        keyprim = await s_stormtypes.toprim(key)

        if keyprim is not None and keyprim != '' and keyprim != b'':
            if isinstance(keyprim, dict):
                return _selectJwk(keyprim, header, alg)

            return await s_cryptoutils.reqKey(key, 'key')

        if jwks_uri is None:
            raise s_exc.BadArg(mesg='verify requires a key or a jwks_uri.')

        jwks_uri = await s_stormtypes.tostr(jwks_uri)
        jwkset = await self._getJwks(jwks_uri, ssl_verify, ssl_opts, proxy, allowinternal, refresh=False)
        try:
            return _selectJwk(jwkset, header, alg)
        except s_exc.BadArg:
            # Only a genuine unknown-kid miss (a plausible key rotation) triggers a refresh; a
            # structural / type-mismatch failure must not let a bad token defeat the cache TTL.
            kid = header.get('kid')
            if kid is None or _kidInSet(jwkset, kid):
                raise

            jwkset = await self._getJwks(jwks_uri, ssl_verify, ssl_opts, proxy, allowinternal, refresh=True)
            return _selectJwk(jwkset, header, alg)

    @s_stormtypes.stormfunc(readonly=True)
    async def _verify(self, token, key, algorithms, audience=None, issuer=None, subject=None,
                      leeway=0, typ=None, requiredclaims=None, options=None,
                      jwks_uri=None, ssl_verify=True, ssl_opts=None, proxy=True, allowinternal=False):
        # verify() never raises: any failure (including invalid input) is returned as the
        # ($ok, $info) tuple so callers can branch on $ok without a try/except in Storm.
        try:
            token = await s_stormtypes.tostr(token)
            algorithms = await s_stormtypes.toprim(algorithms)
            algs = _reqAlgs(algorithms)

            audience = await s_stormtypes.toprim(audience)
            issuer = await s_stormtypes.toprim(issuer)
            subject = await s_stormtypes.toprim(subject)
            typ = await s_stormtypes.toprim(typ)
            requiredclaims = await s_stormtypes.toprim(requiredclaims)
            if requiredclaims is None:
                requiredclaims = ()

            if isinstance(requiredclaims, str):
                requiredclaims = (requiredclaims,)

            options = await s_stormtypes.toprim(options)
            if options is None:
                options = {}

            if not isinstance(options, dict):
                raise s_exc.BadArg(mesg='options must be a dictionary.')

            leeway = await s_stormtypes.toint(leeway)
            if leeway < 0:
                raise s_exc.BadArg(mesg='leeway must not be negative.', leeway=leeway)

            ssl_verify = await s_stormtypes.tobool(ssl_verify, noneok=True)
            ssl_opts = await s_stormtypes.toprim(ssl_opts)
            proxy = await s_stormtypes.toprim(proxy)
            jwks_uri = await s_stormtypes.toprim(jwks_uri)
            allowinternal = await s_stormtypes.tobool(allowinternal)

            # Offload the structural decode to the executor pool to avoid blocking the ioloop
            # on large payloads.
            h64, p64, header, payload, signature, alg, info = \
                await s_coro.executor(lambda: _decodeJws(token, algs))

            keybyts = await self._resolveKey(key, header, alg, jwks_uri, ssl_verify, ssl_opts, proxy, allowinternal)

            def checksig():
                # reconstruct the signing input from the received base64url segments verbatim.
                signin = f'{h64}.{p64}'.encode('ascii')
                if not _checkSig(alg, info, keybyts, signin, signature):
                    raise s_exc.BadArg(mesg='JWT signature verification failed.')

            await s_coro.executor(checksig)

            # s_common.now() is milliseconds; convert to epoch seconds for NumericDate math.
            nowsecs = s_common.now() / 1000
            _checkClaims(payload, header, nowsecs, audience, issuer, subject, leeway,
                         typ, requiredclaims, options)

        except Exception as e:
            return s_common.retnexc(e)

        jwt = Jwt(self.runt, payload=payload)
        jwt.header = header
        jwt.locls['signature'] = signature
        jwt.locked = True

        return (True, jwt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _parse(self, token):
        token = await s_stormtypes.tostr(token)

        def parse():
            return _parseToken(token)

        return await s_coro.executor(parse)

@s_stormtypes.registry.registerType
class Jwt(s_stormtypes.StormType):
    '''
    A JSON Web Token (JWT) to construct, sign, and verify.
    '''
    _storm_typename = 'crypto:jwt'

    _storm_locals = (

        {'name': 'payload',
         'desc': '''
         The claims payload of the JWT.

         While the token is being constructed, individual claims may be set (e.g. ``$token.payload.sub = "foo"``).
         Once the token has been signed or loaded via ``$lib.crypto.jwt.verify()``, the payload becomes immutable.
         ''',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorPayload',
                  'returns': {'type': 'crypto:jwt:dict', 'desc': 'The JWT claims payload.'}}},

        {'name': 'header',
         'desc': '''
         The JOSE header of the JWT.

         Header parameters (e.g. ``kid``, ``cty``) may be set while the token is being constructed. The
         ``alg`` and ``typ`` parameters are set by ``sign()``; a caller-set ``alg`` is always overridden by
         the ``sign()`` algorithm argument. Once the token has been signed or loaded the header becomes
         immutable.
         ''',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorHeader',
                  'returns': {'type': 'crypto:jwt:dict', 'desc': 'The JWT JOSE header.'}}},

        {'name': 'signature', 'type': 'bytes',
         'desc': 'The raw signature bytes of the token, or ``$lib.null`` if it has not been signed or verified.'},

        {'name': 'sign',
         'desc': '''
         Sign the current payload and return a JWT string.

         The JOSE header is populated with the algorithm and type and the signature bytes are set. The
         payload becomes immutable once the token is signed.
         ''',
         'type': {'type': 'function', '_funcname': 'sign',
                  'args': (
                      {'name': 'key', 'type': ['str', 'bytes', 'crypto:rsa:key', 'crypto:ecc:key'],
                       'desc': 'The signing key. A PEM encoded private key (or a crypto:rsa:key / '
                               'crypto:ecc:key object) for RS* / PS* / ES* algorithms, or the secret for '
                               'HS* algorithms. May be a str or bytes.'},
                      {'name': 'alg', 'type': 'str',
                       'desc': 'The JWS algorithm (HS256/384/512, RS256/384/512, PS256/384/512, or ES256/384/512).'},
                      {'name': 'fmt', 'type': 'str', 'default': 'compact',
                       'desc': 'The serialization: "compact" (default) or "json" (flattened JWS JSON serialization).'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The signed JWT string.'}}},
    )

    def __init__(self, runt, payload=None):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt

        self.payload = payload if payload is not None else {}
        self.header = {}
        self.locked = False

        self.locls.update({
            'sign': self.sign,
            'signature': None,
        })

        self.gtors.update({
            'payload': self._gtorPayload,
            'header': self._gtorHeader,
        })

    async def _gtorPayload(self):
        return JwtDict(self.payload, self, validate=True)

    async def _gtorHeader(self):
        return JwtDict(self.header, self)

    @s_stormtypes.stormfunc(readonly=True)
    async def sign(self, key, alg, fmt='compact'):
        if self.locked:
            raise s_exc.BadArg(mesg='This JWT has already been signed or loaded.')

        key = await s_cryptoutils.reqKey(key, 'key')
        alg = await s_stormtypes.tostr(alg)
        fmt = (await s_stormtypes.tostr(fmt)).lower()
        if fmt not in ('compact', 'json'):
            raise s_exc.BadArg(mesg=f'Invalid JWT serialization format: {fmt}', fmt=fmt)

        info = _reqAlg(alg)

        payload = await s_stormtypes.toprim(self.payload)
        userhdr = await s_stormtypes.toprim(self.header)

        # re-validate the full payload at sign time: a nested claim (e.g. an aud list) can be
        # mutated in place after generate()/setitem, so this remains the last gate.
        _reqValidClaims(payload)

        def sign():
            header = dict(userhdr)
            # the sign() algorithm is authoritative; a caller-set alg never overrides it.
            header['alg'] = alg
            header.setdefault('typ', 'JWT')

            try:
                h64 = s_crypto.enbase64url(s_json.dumps(header))
                p64 = s_crypto.enbase64url(s_json.dumps(payload))
            except s_exc.MustBeJsonSafe as e:
                raise s_exc.BadArg(mesg=f'Unable to encode JWT payload: {e}') from None

            signin = f'{h64}.{p64}'.encode('ascii')
            signature = _makeSig(alg, info, key, signin)
            s64 = s_crypto.enbase64url(signature)

            if fmt == 'compact':
                token = f'{h64}.{p64}.{s64}'
            else:
                token = s_json.dumps({'payload': p64, 'protected': h64, 'signature': s64}).decode()

            return (token, header, signature)

        # Offload the serialization and signing to the executor pool to avoid blocking
        # the ioloop, which matters for large payloads and expensive keys.
        token, header, signature = await s_coro.executor(sign)

        self.header = header
        self.locls['signature'] = signature
        self.locked = True

        return token

@s_stormtypes.registry.registerType
class JwtDict(s_stormtypes.Dict):
    '''
    A dictionary view of JWT payload or header data which becomes immutable once the token is signed or loaded.
    '''
    _storm_typename = 'crypto:jwt:dict'

    def __init__(self, valu, jwt, validate=False):
        s_stormtypes.Dict.__init__(self, valu)
        self.jwt = jwt
        self.validate = validate

    async def setitem(self, name, valu):
        if self.jwt.locked:
            raise s_exc.IsReadOnly(mesg='The JWT is read only and may not be modified.')

        pname = await s_stormtypes.toprim(name)
        if not isinstance(pname, str):
            raise s_exc.BadArg(mesg='JWT claim and header names must be strings.', name=pname)

        # validate a set registered claim against the schema (payload dict only); custom
        # claims and JOSE header params are unconstrained beyond the string-key requirement.
        if self.validate and valu is not s_stormtypes.undef and pname in s_schemas.jwtRegisteredClaims:
            pvalu = await s_stormtypes.toprim(valu)
            try:
                s_schemas.reqValidJwtClaims({pname: pvalu})
            except s_exc.SchemaViolation as e:
                raise s_exc.BadArg(mesg=f'Invalid JWT claim {pname}: {e}') from None

        return await s_stormtypes.Dict.setitem(self, name, valu)
