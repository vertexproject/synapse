import time
import hmac
import json
import socket
import asyncio
from unittest import mock

import cryptography.hazmat.primitives.asymmetric.utils as c_utils

import synapse.exc as s_exc
import synapse.lib.json as s_json
import synapse.lib.httpapi as s_httpapi
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.utils as s_crypto
import synapse.lib.stormlib.jwt as s_jwt

import synapse.tests.utils as s_test

def rsaJwk(pubpem, kid):
    pn = s_rsa.PubKey.load(pubpem.encode(), fmt='pem').publ.public_numbers()
    def i2b(i):
        return s_crypto.enbase64url(i.to_bytes((i.bit_length() + 7) // 8, 'big'))
    return {'kty': 'RSA', 'kid': kid, 'n': i2b(pn.n), 'e': i2b(pn.e)}

def eccJwk(pubpem, kid):
    pn = s_ecc.PubKey.load(pubpem.encode(), fmt='pem').publ.public_numbers()
    return {'kty': 'EC', 'kid': kid, 'crv': 'P-256',
            'x': s_crypto.enbase64url(pn.x.to_bytes(32, 'big')), 'y': s_crypto.enbase64url(pn.y.to_bytes(32, 'big'))}

class JwksHandler(s_httpapi.Handler):
    def initialize(self, cell, state):
        s_httpapi.Handler.initialize(self, cell)
        self.state = state
    async def get(self):
        self.state['hits'] += 1
        code = self.state.get('code', 200)
        if code != 200:
            self.set_status(code)
            self.write(b'error')
            return
        self.write(self.state['body'])

# HMAC secrets must be at least the hash output length (RFC 7518 3.2), so tests use a
# 64-byte secret that satisfies HS256/384/512.
SECRET = b'k' * 64
SECRET_STR = 'k' * 64
WRONGSECRET = b'w' * 64

def forgeHmac(header, payload, secret, hashname='sha256'):
    h = s_crypto.enbase64url(json.dumps(header, separators=(',', ':')).encode())
    p = s_crypto.enbase64url(json.dumps(payload, separators=(',', ':')).encode())
    signin = f'{h}.{p}'.encode('ascii')
    sig = hmac.new(secret, signin, hashname).digest()
    return f'{h}.{p}.{s_crypto.enbase64url(sig)}'

class StormLibJwtTest(s_test.SynTest):

    async def _rsaPems(self, core):
        return await core.callStorm('$k = $lib.crypto.rsa.generate() return(($k.encode(), $k.pubkey().encode()))')

    async def _eccPems(self, core, curve):
        return await core.callStorm(
            '$k = $lib.crypto.ecc.generate(curve=$c) return(($k.encode(), $k.pubkey().encode()))',
            opts={'vars': {'c': curve}})

    async def _signHs(self, core, claims):
        # returns a compact HS256 token whose payload is the given claims dict
        return await core.callStorm(
            '$t = $lib.crypto.jwt.generate($claims) return($t.sign($secret, "HS256"))',
            opts={'vars': {'claims': claims, 'secret': SECRET}})

    async def _verifyHs(self, core, tok, **kwargs):
        vs = {'tok': tok, 'secret': SECRET}
        vs.update(kwargs)
        args = ''.join(f', {k}=${k}' for k in kwargs)
        return await core.callStorm(
            f'return($lib.crypto.jwt.verify($tok, $secret, ("HS256",){args}))', opts={'vars': vs})

    async def test_stormlib_jwt_roundtrip(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)
            eckeys = {}
            for curve in ('P-256', 'P-384', 'P-521'):
                eckeys[curve] = await self._eccPems(core, curve)

            cases = (
                ('HS256', SECRET, SECRET),
                ('HS384', SECRET, SECRET),
                ('HS512', SECRET, SECRET),
                ('RS256', rsaprv, rsapub),
                ('RS384', rsaprv, rsapub),
                ('RS512', rsaprv, rsapub),
                ('PS256', rsaprv, rsapub),
                ('PS384', rsaprv, rsapub),
                ('PS512', rsaprv, rsapub),
                ('ES256', eckeys['P-256'][0], eckeys['P-256'][1]),
                ('ES384', eckeys['P-384'][0], eckeys['P-384'][1]),
                ('ES512', eckeys['P-521'][0], eckeys['P-521'][1]),
            )

            for alg, signkey, verifykey in cases:

                opts = {'vars': {'signkey': signkey, 'verifykey': verifykey, 'alg': alg}}
                retn = await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $before = $token.signature
                    $token.payload.sub = "1234567890"
                    $token.payload.name = "vtx"
                    $jwtstr = $token.sign($signkey, $alg)
                    ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $verifykey, ($alg,))
                    return(($before, $jwtstr, $ok, $valu.payload.sub, $valu.payload.name,
                            $valu.header.alg, $valu.header.typ, $valu.signature, $token.signature))
                ''', opts=opts)

                before, jwtstr, ok, sub, name, halg, htyp, vsig, tsig = retn

                self.none(before)
                self.len(3, jwtstr.split('.'))
                self.true(ok)
                self.eq(sub, '1234567890')
                self.eq(name, 'vtx')
                self.eq(halg, alg)
                self.eq(htyp, 'JWT')
                self.isinstance(vsig, bytes)
                self.isinstance(tsig, bytes)

                parts = jwtstr.split('.')
                self.eq(json.loads(s_crypto.debase64url(parts[0])).get('alg'), alg)
                self.eq(json.loads(s_crypto.debase64url(parts[1])).get('sub'), '1234567890')

    async def test_stormlib_jwt_json_serialization(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)
            opts = {'vars': {'prvpem': rsaprv, 'pubpem': rsapub}}

            jsonstr, compactstr = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.sub = "js"
                $j = $t.sign($prvpem, "PS256", fmt="json")
                $t2 = $lib.crypto.jwt.generate()
                $t2.payload.sub = "js"
                $c = $t2.sign($prvpem, "PS256")
                return(($j, $c))
            ''', opts=opts)

            obj = json.loads(jsonstr)
            self.sorteq(('payload', 'protected', 'signature'), tuple(obj.keys()))
            self.len(3, compactstr.split('.'))

            opts2 = {'vars': {'tok': jsonstr, 'pubpem': rsapub}}
            ok, sub = await core.callStorm('''
                ($ok, $valu) = $lib.crypto.jwt.verify($tok, $pubpem, ("PS256",))
                return(($ok, $valu.payload.sub))
            ''', opts=opts2)
            self.true(ok)
            self.eq(sub, 'js')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($prvpem, "PS256", fmt="newp")', opts=opts)

    async def test_stormlib_jwt_whitespace(self):

        async with self.getTestCore() as core:

            tok = await self._signHs(core, {'sub': 'u'})
            self.true((await self._verifyHs(core, tok))[0])

            # base64url segments are strict: whitespace anywhere in a compact token fails to
            # verify (previously a whitespace-only mutation of the signature segment, which is
            # not part of the signing input, still verified)
            h, p, s = tok.split('.')
            for mut in (tok + ' ', tok + '\n', ' ' + tok,
                        f'{h}.{p}.{s[:4]} {s[4:]}',
                        f'{h}.{p[:4]} {p[4:]}.{s}',
                        f'{h[:4]} {h[4:]}.{p}.{s}'):
                self.false((await self._verifyHs(core, mut))[0])

            # the flattened-JSON form tolerates whitespace around the JSON container, but a
            # whitespace-corrupted base64url value inside it is still rejected
            jsontok = await core.callStorm(
                '$t = $lib.crypto.jwt.generate(({"sub": "u"})) return($t.sign($secret, "HS256", fmt="json"))',
                opts={'vars': {'secret': SECRET}})
            self.true((await self._verifyHs(core, f'  {jsontok}  \n'))[0])

            obj = json.loads(jsontok)
            obj['signature'] = obj['signature'] + ' '
            self.false((await self._verifyHs(core, json.dumps(obj)))[0])

    async def test_stormlib_jwt_stringoruri(self):

        async with self.getTestCore() as core:

            # iss/sub/aud are RFC 7519 StringOrURI: a value containing a ':' must be a valid URI.
            # These are enforced on the tokens we construct (generate / setitem / sign).
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate(({"iss": "not a uri: x"}))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$t = $lib.crypto.jwt.generate() $t.payload.sub = "foo:bar baz"')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.jwt.generate($p))',
                                     opts={'vars': {'p': {'aud': ['ok', 'bad: x']}}})

            # valid StringOrURI values (a URI, and no-colon plain strings) round-trip
            ok, iss, sub = await core.callStorm('''
                $t = $lib.crypto.jwt.generate(({"iss": "https://issuer.example", "sub": "urn:uuid:1234"}))
                $t.payload.aud = ("https://a.example", "b")
                $j = $t.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($j, $secret, ("HS256",))
                return(($ok, $valu.payload.iss, $valu.payload.sub))
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)
            self.eq(iss, 'https://issuer.example')
            self.eq(sub, 'urn:uuid:1234')

            # empty strings are valid StringOrURI (no ':') and must stay accepted, including an
            # empty element inside an aud array
            ok, iss = await core.callStorm('''
                $t = $lib.crypto.jwt.generate(({"iss": "", "sub": ""}))
                $t.payload.aud = ("", "x")
                $j = $t.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($j, $secret, ("HS256",), issuer="")
                return(($ok, $valu.payload.iss))
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)
            self.eq(iss, '')

            # verify stays lenient: a third-party token whose iss is not a valid StringOrURI
            # (built outside our construction path) still verifies, matching PyJWT's leniency
            badtok = forgeHmac({'alg': 'HS256', 'typ': 'JWT'}, {'iss': 'not a uri: x', 'sub': 'u'}, SECRET)
            ok, iss = await core.callStorm('''
                ($ok, $valu) = $lib.crypto.jwt.verify($t, $secret, ("HS256",), issuer="not a uri: x")
                return(($ok, $valu.payload.iss))
            ''', opts={'vars': {'t': badtok, 'secret': SECRET}})
            self.true(ok)
            self.eq(iss, 'not a uri: x')

    async def test_stormlib_jwt_header(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)
            opts = {'vars': {'prvpem': rsaprv, 'pubpem': rsapub}}

            jwtstr = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.header.kid = "key-1"
                $t.header.cty = "example"
                $t.header.alg = "none"
                $t.payload.sub = "hdr"
                return($t.sign($prvpem, "RS256"))
            ''', opts=opts)

            header = json.loads(s_crypto.debase64url(jwtstr.split('.')[0]))
            self.eq(header.get('kid'), 'key-1')
            self.eq(header.get('cty'), 'example')
            self.eq(header.get('alg'), 'RS256')
            self.eq(header.get('typ'), 'JWT')

            opts2 = {'vars': {'tok': jwtstr, 'pubpem': rsapub}}
            kid = await core.callStorm('''
                ($ok, $valu) = $lib.crypto.jwt.verify($tok, $pubpem, ("RS256",))
                return($valu.header.kid)
            ''', opts=opts2)
            self.eq(kid, 'key-1')

    async def test_stormlib_jwt_parse(self):

        async with self.getTestCore() as core:

            rsaprv, _ = await self._rsaPems(core)
            opts = {'vars': {'prvpem': rsaprv}}

            info = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.sub = "p"
                $j = $t.sign($prvpem, "RS256")
                return($lib.crypto.jwt.parse($j))
            ''', opts=opts)
            self.eq(info.get('typ'), 'JWS')
            self.eq(info.get('header').get('alg'), 'RS256')

            info = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.sub = "p"
                $j = $t.sign($prvpem, "RS256", fmt="json")
                return($lib.crypto.jwt.parse($j))
            ''', opts=opts)
            self.eq(info.get('typ'), 'JWS')
            self.eq(info.get('header').get('alg'), 'RS256')

            jweh = s_crypto.enbase64url(b'{"alg":"RSA-OAEP","enc":"A256GCM"}')
            jwe = f'{jweh}.a.b.c.d'
            info = await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': jwe}})
            self.eq(info.get('typ'), 'JWE')
            self.eq(info.get('header').get('enc'), 'A256GCM')

            jwejson = json.dumps({'protected': s_crypto.enbase64url(b'{"enc":"A256GCM"}'), 'ciphertext': 'x',
                                  'iv': 'y', 'tag': 'z', 'encrypted_key': 'k'})
            info = await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': jwejson}})
            self.eq(info.get('typ'), 'JWE')

            gjson = json.dumps({'payload': 'e30', 'signatures': [{'protected': s_crypto.enbase64url(b'{"alg":"RS256"}'), 'signature': 'x'}]})
            info = await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': gjson}})
            self.eq(info.get('typ'), 'JWS')
            self.eq(info.get('header').get('alg'), 'RS256')

            gjson2 = json.dumps({'payload': 'e30', 'signatures': []})
            info = await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': gjson2}})
            self.eq(info.get('typ'), 'JWS')
            self.eq(info.get('header'), {})

            badheaderjson = f'{s_crypto.enbase64url(b"123")}.b.c'
            for bad in ('a.b', 'not json and not dotted here', '{"unknown":1}', '[]', '{',
                        'aaa.b.c', badheaderjson):
                with self.raises(s_exc.BadArg):
                    await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': bad}})

            big = ('A' * 70000) + '.b.c'
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.jwt.parse($t))', opts={'vars': {'t': big}})

    async def test_stormlib_jwt_algorithms(self):

        async with self.getTestCore() as core:

            algs = await core.callStorm('return($lib.crypto.jwt.algorithms)')
            self.eq(sorted(algs), sorted(s_jwt.jwtalgs))
            self.isin('HS256', algs)
            self.isin('RS512', algs)
            self.isin('ES512', algs)

            # a new list is returned on each access, so mutating it does not affect the next
            await core.callStorm('$a = $lib.crypto.jwt.algorithms $a.append("bogus")')
            algs2 = await core.callStorm('return($lib.crypto.jwt.algorithms)')
            self.notin('bogus', algs2)

    async def test_stormlib_jwt_jwe_rejected(self):

        async with self.getTestCore() as core:

            jwe = 'aaaa.bbbb.cccc.dddd.eeee'
            retn = await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))',
                opts={'vars': {'t': jwe, 'k': SECRET}})
            self.false(retn[0])
            self.isin('JWE', retn[1][1].get('mesg'))

            jwejson = json.dumps({'protected': 'e30', 'ciphertext': 'x', 'iv': 'y', 'tag': 'z', 'encrypted_key': 'k'})
            retn = await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))',
                opts={'vars': {'t': jwejson, 'k': SECRET}})
            self.false(retn[0])
            self.isin('JWE', retn[1][1].get('mesg'))

            gjson = json.dumps({'payload': 'e30', 'signatures': [{'protected': 'e30', 'signature': 'x'}]})
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))',
                opts={'vars': {'t': gjson, 'k': SECRET}}))[0])

            for bad in (json.dumps({'foo': 1}), '{bad', '[1,2]'):
                self.false((await core.callStorm(
                    'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))',
                    opts={'vars': {'t': bad, 'k': SECRET}}))[0])

    async def test_stormlib_jwt_key_objects(self):

        async with self.getTestCore() as core:

            for gen, alg in (('$lib.crypto.rsa.generate()', 'RS256'),
                             ('$lib.crypto.rsa.generate()', 'PS256'),
                             ('$lib.crypto.ecc.generate(curve="P-256")', 'ES256')):
                ok, sub = await core.callStorm(f'''
                    $key = {gen}
                    $token = $lib.crypto.jwt.generate()
                    $token.payload.sub = "obj"
                    $jwtstr = $token.sign($key, "{alg}")
                    ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $key.pubkey(), ("{alg}",))
                    return(($ok, $valu.payload.sub))
                ''')
                self.true(ok)
                self.eq(sub, 'obj')

    async def test_stormlib_jwt_rsa_interop(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)

            jwtstr = await core.callStorm('''
                $key = $lib.crypto.rsa.load($prvpem)
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "interop"
                return($token.sign($key, "RS256"))
            ''', opts={'vars': {'prvpem': rsaprv}})

            h, p, s = jwtstr.split('.')
            sig = s_crypto.debase64url(s)
            signin = f'{h}.{p}'
            opts = {'vars': {'pubpem': rsapub, 'signin': signin, 'sig': sig}}
            self.true(await core.callStorm(
                'return($lib.crypto.rsa.load($pubpem).verify($signin.encode(), $sig, padding="pkcs1v15"))', opts=opts))

    async def test_stormlib_jwt_initial_payload(self):

        async with self.getTestCore() as core:

            ok, iss, sub = await core.callStorm('''
                $token = $lib.crypto.jwt.generate(({"iss": "vertex", "sub": "abc"}))
                $jwtstr = $token.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $secret, ("HS256",))
                return(($ok, $valu.payload.iss, $valu.payload.sub))
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)
            self.eq(iss, 'vertex')
            self.eq(sub, 'abc')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.jwt.generate("notadict"))')

    async def test_stormlib_jwt_str_keys(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)
            self.isinstance(rsaprv, str)
            self.isinstance(rsapub, str)

            opts = {'vars': {'prvpem': rsaprv, 'pubpem': rsapub}}
            ok, sub = await core.callStorm('''
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "strkey"
                $jwtstr = $token.sign($prvpem, "RS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $pubpem, ("RS256",))
                return(($ok, $valu.payload.sub))
            ''', opts=opts)
            self.true(ok)
            self.eq(sub, 'strkey')

            for secret in (SECRET_STR, SECRET):
                opts = {'vars': {'secret': secret}}
                ok = await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.payload.sub = "hs"
                    $jwtstr = $token.sign($secret, "HS256")
                    ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $secret, ("HS256",))
                    return($ok)
                ''', opts=opts)
                self.true(ok)

            # a str secret and the equivalent bytes secret interoperate
            signed = await core.callStorm(
                '$token = $lib.crypto.jwt.generate() $token.payload.sub = "hs" return($token.sign($secret, "HS256"))',
                opts={'vars': {'secret': SECRET_STR}})
            ok = await core.callStorm(
                '($ok, $valu) = $lib.crypto.jwt.verify($tok, $secret, ("HS256",)) return($ok)',
                opts={'vars': {'tok': signed, 'secret': SECRET}})
            self.true(ok)

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign((1234), "HS256")')

    async def test_stormlib_jwt_claims(self):

        async with self.getTestCore() as core:

            now = int(time.time())

            # exp: a future exp verifies, a past one is expired
            self.true((await self._verifyHs(core, await self._signHs(core, {'exp': now + 3600})))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'exp': now - 3600})))[0])

            # leeway lets a just-expired token through
            tok = await self._signHs(core, {'exp': now - 10})
            self.false((await self._verifyHs(core, tok))[0])
            self.true((await self._verifyHs(core, tok, leeway=3600))[0])

            # nbf: a past nbf verifies, a future one is not yet valid
            self.true((await self._verifyHs(core, await self._signHs(core, {'nbf': now - 3600})))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'nbf': now + 3600})))[0])

            # iat present and numeric verifies
            self.true((await self._verifyHs(core, await self._signHs(core, {'iat': now})))[0])

            # non-numeric exp/nbf/iat in an incoming token are rejected
            for claim in ('exp', 'nbf', 'iat'):
                forged = forgeHmac({'alg': 'HS256', 'typ': 'JWT'}, {claim: 'notanumber'}, SECRET)
                self.false((await self._verifyHs(core, forged))[0])

            # audience: token aud may be a string or an array; caller audience may be a string or a list
            self.true((await self._verifyHs(core, await self._signHs(core, {'aud': 'myapp'}), audience='myapp'))[0])
            self.true((await self._verifyHs(core, await self._signHs(core, {'aud': ['a', 'myapp']}), audience='myapp'))[0])
            self.true((await self._verifyHs(core, await self._signHs(core, {'aud': 'myapp'}), audience=['x', 'myapp']))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'aud': 'other'}), audience='myapp'))[0])
            # audience requested but the token has no aud claim
            self.false((await self._verifyHs(core, await self._signHs(core, {'sub': 'x'}), audience='myapp'))[0])
            # RFC 7519 4.1.3: an empty aud carries no value to match, so it is rejected (as PyJWT
            # does), even against an empty expected audience; an empty element inside a non-empty
            # aud array still matches.
            self.false((await self._verifyHs(core, await self._signHs(core, {'aud': ''}), audience=''))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'aud': ''}), audience='x'))[0])
            self.true((await self._verifyHs(core, await self._signHs(core, {'aud': ['', 'x']}), audience=''))[0])

            # issuer: exact string match, list membership, and NO substring matching
            self.true((await self._verifyHs(core, await self._signHs(core, {'iss': 'vertex'}), issuer='vertex'))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'iss': 'vertex'}), issuer='ver'))[0])
            self.true((await self._verifyHs(core, await self._signHs(core, {'iss': 'vertex'}), issuer=['a', 'vertex']))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'iss': 'vertex'}), issuer=['a', 'b']))[0])

            # subject exact match
            self.true((await self._verifyHs(core, await self._signHs(core, {'sub': 'u1'}), subject='u1'))[0])
            self.false((await self._verifyHs(core, await self._signHs(core, {'sub': 'u1'}), subject='u2'))[0])

            # required claims (presence only); a str is treated as a single name
            tok = await self._signHs(core, {'sub': 'x'})
            self.true((await self._verifyHs(core, tok, requiredclaims=('sub',)))[0])
            self.true((await self._verifyHs(core, tok, requiredclaims='sub'))[0])
            self.false((await self._verifyHs(core, tok, requiredclaims=('missing',)))[0])

            # typ check against the header
            tok = await self._signHs(core, {'sub': 'x'})
            self.true((await self._verifyHs(core, tok, typ='JWT'))[0])
            self.false((await self._verifyHs(core, tok, typ='at+jwt'))[0])

    async def test_stormlib_jwt_claim_options(self):

        async with self.getTestCore() as core:

            now = int(time.time())
            expired = await self._signHs(core, {'exp': now - 3600, 'sub': 'x'})

            # disabling verify_exp lets an expired token through
            self.true((await self._verifyHs(core, expired, options={'verify_exp': False}))[0])
            # by default it is rejected
            self.false((await self._verifyHs(core, expired))[0])

            # options must be a dict; leeway must be non-negative
            self.false((await self._verifyHs(core, expired, options='notadict'))[0])
            self.false((await self._verifyHs(core, expired, leeway=-1))[0])

            # an explicit null requiredclaims is treated as empty
            good = await self._signHs(core, {'sub': 'x'})
            self.true((await self._verifyHs(core, good, requiredclaims=None))[0])

    async def test_stormlib_jwt_schema(self):

        async with self.getTestCore() as core:

            # setting a registered claim to the wrong type is rejected at set time
            with self.raises(s_exc.BadArg):
                await core.callStorm('$t = $lib.crypto.jwt.generate() $t.payload.exp = "notanumber"')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$t = $lib.crypto.jwt.generate() $t.payload.aud = (5)')

            # aud may be set to an array of strings
            ok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.aud = ("a", "b")
                $t.payload.exp = (99999999999)
                $j = $t.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($j, $secret, ("HS256",), audience="b")
                return($ok)
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)

            # a custom (non-registered) claim of any JSON type is allowed
            ok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.custom = (42)
                $j = $t.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($j, $secret, ("HS256",))
                return($ok)
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)

            # claim / header names must be strings
            with self.raises(s_exc.BadArg):
                await core.callStorm('$t = $lib.crypto.jwt.generate() $k = (1234) $t.payload.$k = "x"')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$t = $lib.crypto.jwt.generate() $k = (1234) $t.header.$k = "x"')

            # generate() validates an initial payload up front: bad registered-claim types and
            # non-string keys are rejected before a Jwt is created
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate(({"exp": "notanumber"}))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate(({"aud": (5)}))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.jwt.generate($p))',
                                     opts={'vars': {'p': {1234: 'x'}}})

            # a custom (non-registered) claim in an initial payload is allowed
            ok, custom = await core.callStorm('''
                $t = $lib.crypto.jwt.generate(({"sub": "x", "custom": "y"}))
                $j = $t.sign($secret, "HS256")
                ($ok, $valu) = $lib.crypto.jwt.verify($j, $secret, ("HS256",))
                return(($ok, $valu.payload.custom))
            ''', opts={'vars': {'secret': SECRET}})
            self.true(ok)
            self.eq(custom, 'y')

            # a registered claim mutated in place after generate() bypasses generate/setitem
            # validation, so the sign-time gate still catches it
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $t = $lib.crypto.jwt.generate()
                    $t.payload.aud = ("a",)
                    $t.payload.aud.append((5))
                    $t.sign($secret, "HS256")
                ''', opts={'vars': {'secret': SECRET}})

    async def test_stormlib_jwt_hardening(self):

        async with self.getTestCore() as core:

            rsaprv, _ = await self._rsaPems(core)

            # an asymmetric key (PEM) may not be used as an HMAC secret
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($k, "HS256")', opts={'vars': {'k': rsaprv}})

            # an HMAC secret shorter than the hash output is rejected
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($k, "HS256")', opts={'vars': {'k': b'short'}})

            # an RSA key smaller than 2048 bits is rejected on sign
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $k = $lib.crypto.rsa.generate(bits=(1024))
                    $lib.crypto.jwt.generate().sign($k, "RS256")
                ''')

            # ... and on verify: a token signed by a 1024-bit key is rejected
            prikey = s_rsa.PriKey.generate(bits=1024)
            pubpem = prikey.public().dump(fmt='pem').decode()
            h = s_crypto.enbase64url(json.dumps({'alg': 'RS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
            p = s_crypto.enbase64url(json.dumps({'sub': 'x'}, separators=(',', ':')).encode())
            sig = prikey.sign(f'{h}.{p}'.encode('ascii'), padding='pkcs1v15', hashalgo='sha256')
            smalltok = f'{h}.{p}.{s_crypto.enbase64url(sig)}'
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))',
                opts={'vars': {'t': smalltok, 'k': pubpem}}))[0])

            # a token carrying a crit header is rejected on verify
            crittok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.header.crit = ("exp",)
                $t.payload.sub = "x"
                return($t.sign($secret, "HS256"))
            ''', opts={'vars': {'secret': SECRET}})
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $secret, ("HS256",)))',
                opts={'vars': {'t': crittok, 'secret': SECRET}}))[0])

    async def test_stormlib_jwt_immutable(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.payload.a = "1"
                    $token.sign($secret, "HS256")
                    $token.payload.b = "2"
                ''', opts={'vars': {'secret': SECRET}})

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.sign($secret, "HS256")
                    $token.header.kid = "late"
                ''', opts={'vars': {'secret': SECRET}})

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.payload.a = "1"
                    $jwtstr = $token.sign($secret, "HS256")
                    ($ok, $loaded) = $lib.crypto.jwt.verify($jwtstr, $secret, ("HS256",))
                    $loaded.payload.b = "2"
                ''', opts={'vars': {'secret': SECRET}})

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $jwtstr = $token.sign($secret, "HS256")
                    ($ok, $loaded) = $lib.crypto.jwt.verify($jwtstr, $secret, ("HS256",))
                    $loaded.header.kid = "x"
                ''', opts={'vars': {'secret': SECRET}})

    async def test_stormlib_jwt_errors(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($secret, "HS999")',
                                     opts={'vars': {'secret': SECRET}})

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign((1234), "HS256")')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($lib.base64.decode(""), "HS256")')

            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.sign($secret, "HS256")
                    $token.sign($secret, "HS256")
                ''', opts={'vars': {'secret': SECRET}})

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($k, "RS256")', opts={'vars': {'k': b'not a pem'}})

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($k, "PS256")', opts={'vars': {'k': b'not a pem'}})

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.crypto.jwt.generate().sign($k, "ES256")', opts={'vars': {'k': b'not a pem'}})

            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $token = $lib.crypto.jwt.generate()
                    $token.payload.custom = $lib.base64.decode("aGk=")
                    $token.sign($secret, "HS256")
                ''', opts={'vars': {'secret': SECRET}})

    async def test_stormlib_jwt_malformed(self):

        async with self.getTestCore() as core:

            jwtstr = await core.callStorm('''
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "x"
                return($token.sign($secret, "HS256"))
            ''', opts={'vars': {'secret': SECRET}})
            opts = {'vars': {'tok': jwtstr, 'secret': SECRET}}

            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $secret, "HS256"))', opts=opts))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $secret, ((1234),)))', opts=opts))[0])

            def verify(tok, key=SECRET, algs=('HS256',)):
                o = {'vars': {'tok': tok, 'key': key, 'algs': list(algs)}}
                return core.callStorm('return($lib.crypto.jwt.verify($tok, $key, $algs))', opts=o)

            emptyobj = s_crypto.enbase64url(b'{}')
            badnum = s_crypto.enbase64url(b'123')
            hdr_hs = s_crypto.enbase64url(b'{"alg":"HS256","typ":"JWT"}')
            hdr_notyp = s_crypto.enbase64url(b'{"typ":"JWT"}')
            openbrace = s_crypto.enbase64url(b'{')

            self.false((await verify(jwtstr, algs=()))[0])
            self.false((await verify('a.b'))[0])
            self.false((await verify('a.a.a'))[0])
            self.false((await verify(f'{openbrace}.{emptyobj}.AA'))[0])
            self.false((await verify(f'{badnum}.{emptyobj}.AA'))[0])
            self.false((await verify(f'{hdr_hs}.{badnum}.AA'))[0])
            self.false((await verify(f'{hdr_notyp}.{emptyobj}.AA'))[0])
            self.false((await verify(jwtstr, algs=('RS256',)))[0])
            self.false((await verify(jwtstr, key=b''))[0])
            self.false((await verify(jwtstr, key=1234))[0])

            rsaprv, _ = await self._rsaPems(core)
            rstok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.sub = "x"
                return($t.sign($prvpem, "RS256"))
            ''', opts={'vars': {'prvpem': rsaprv}})
            self.false((await verify(rstok, key=b'not pem', algs=('RS256',)))[0])

            ecprv, _ = await self._eccPems(core, 'P-256')
            estok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.payload.sub = "x"
                return($t.sign($prvpem, "ES256"))
            ''', opts={'vars': {'prvpem': ecprv}})
            self.false((await verify(estok, key=b'not pem', algs=('ES256',)))[0])

class StormLibJwtAttackTest(s_test.SynTest):

    async def _rsaPems(self, core):
        return await core.callStorm('$k = $lib.crypto.rsa.generate() return(($k.encode(), $k.pubkey().encode()))')

    async def _eccPems(self, core, curve):
        return await core.callStorm(
            '$k = $lib.crypto.ecc.generate(curve=$c) return(($k.encode(), $k.pubkey().encode()))',
            opts={'vars': {'c': curve}})

    async def test_stormlib_jwt_attack_alg_none(self):

        async with self.getTestCore() as core:

            h = s_crypto.enbase64url(json.dumps({'alg': 'none', 'typ': 'JWT'}, separators=(',', ':')).encode())
            p = s_crypto.enbase64url(json.dumps({'sub': 'admin'}, separators=(',', ':')).encode())
            nonetok = f'{h}.{p}.'

            opts = {'vars': {'tok': nonetok, 'key': SECRET}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $key, ("HS256",)))', opts=opts))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $key, ("none",)))', opts=opts))[0])

    async def test_stormlib_jwt_attack_confusion(self):

        async with self.getTestCore() as core:

            _, pubpem = await self._rsaPems(core)

            # forge an HS256 token using the RSA public key PEM as the HMAC secret
            forged = forgeHmac({'alg': 'HS256', 'typ': 'JWT'}, {'sub': 'admin'}, pubpem.encode())

            # the allowlist rejects the forged HS256 token when RS256 is required, AND the
            # key-type binding rejects using an asymmetric key PEM as an HMAC secret even when
            # HS256 is (mistakenly) allowed. Both mitigations hold.
            opts = {'vars': {'tok': forged, 'pubkey': pubpem}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("RS256",)))', opts=opts))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("HS256",)))', opts=opts))[0])

    async def test_stormlib_jwt_attack_allowlist(self):

        async with self.getTestCore() as core:

            rsaprv, rsapub = await self._rsaPems(core)

            jwtstr = await core.callStorm('''
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "x"
                return($token.sign($prvpem, "RS256"))
            ''', opts={'vars': {'prvpem': rsaprv}})

            opts = {'vars': {'tok': jwtstr, 'pubkey': rsapub}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("HS256",)))', opts=opts))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ()))', opts=opts))[0])

    async def test_stormlib_jwt_attack_tamper(self):

        async with self.getTestCore() as core:

            jwtstr = await core.callStorm('''
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "user"
                return($token.sign($secret, "HS256"))
            ''', opts={'vars': {'secret': SECRET}})

            h, p, s = jwtstr.split('.')
            badp = s_crypto.enbase64url(json.dumps({'sub': 'admin'}, separators=(',', ':')).encode())
            badtok = f'{h}.{badp}.{s}'

            opts = {'vars': {'tok': badtok, 'secret': SECRET}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $secret, ("HS256",)))', opts=opts))[0])

    async def test_stormlib_jwt_attack_kid_ignored(self):

        async with self.getTestCore() as core:

            header = {'alg': 'HS256', 'typ': 'JWT', 'kid': '../../../etc/passwd'}
            forged = forgeHmac(header, {'sub': 'x'}, SECRET)

            opts = {'vars': {'tok': forged, 'secret': SECRET}}
            ok, sub = await core.callStorm('''
                ($ok, $valu) = $lib.crypto.jwt.verify($tok, $secret, ("HS256",))
                return(($ok, $valu.payload.sub))
            ''', opts=opts)
            self.true(ok)
            self.eq(sub, 'x')

            opts = {'vars': {'tok': forged, 'secret': WRONGSECRET}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $secret, ("HS256",)))', opts=opts))[0])

    async def test_stormlib_jwt_attack_ecc(self):

        async with self.getTestCore() as core:

            ec256prv, ec256pub = await self._eccPems(core, 'P-256')
            _, ec384pub = await self._eccPems(core, 'P-384')

            jwtstr = await core.callStorm('''
                $token = $lib.crypto.jwt.generate()
                $token.payload.sub = "ecc"
                return($token.sign($prvpem, "ES256"))
            ''', opts={'vars': {'prvpem': ec256prv}})

            opts = {'vars': {'tok': jwtstr, 'pubkey': ec384pub}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("ES384",)))', opts=opts))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("ES256",)))', opts=opts))[0])

            h, p, s = jwtstr.split('.')
            raw = s_crypto.debase64url(s)
            r = int.from_bytes(raw[:32], 'big')
            sval = int.from_bytes(raw[32:], 'big')
            der = c_utils.encode_dss_signature(r, sval)
            badtok = f'{h}.{p}.{s_crypto.enbase64url(der)}'

            opts = {'vars': {'tok': badtok, 'pubkey': ec256pub}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("ES256",)))', opts=opts))[0])

            zerotok = f'{h}.{p}.{s_crypto.enbase64url(bytes(64))}'
            opts = {'vars': {'tok': zerotok, 'pubkey': ec256pub}}
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($tok, $pubkey, ("ES256",)))', opts=opts))[0])

class StormLibJwtJwksTest(s_test.SynTest):

    async def _mkkey(self, core, kid):
        prvpem, pubpem = await core.callStorm(
            '$k = $lib.crypto.rsa.generate() return(($k.encode(), $k.pubkey().encode()))')
        return prvpem, rsaJwk(pubpem, kid)

    async def _sign(self, core, prvpem, kid, sub='u'):
        return await core.callStorm('''
            $t = $lib.crypto.jwt.generate()
            $t.header.kid = $kid
            $t.payload.sub = $sub
            return($t.sign($prvpem, "RS256"))
        ''', opts={'vars': {'prvpem': prvpem, 'kid': kid, 'sub': sub}})

    async def test_stormlib_jwt_jwks_dict(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            _, jwk2 = await self._mkkey(core, 'k2')
            tok = await self._sign(core, prv1, 'k1')
            jwks = {'keys': [jwk1, jwk2]}

            # select from a JWKS by kid
            ok, sub = await core.callStorm(
                '($ok, $v) = $lib.crypto.jwt.verify($t, $jwks, ("RS256",)) return(($ok, $v.payload.sub))',
                opts={'vars': {'t': tok, 'jwks': jwks}})
            self.true(ok)
            self.eq(sub, 'u')

            # a single JWK (not a set) also works
            self.true((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("RS256",)))',
                opts={'vars': {'t': tok, 'jwk': jwk1}}))[0])

            # a kid with no match in the set fails
            toknope = await self._sign(core, prv1, 'nope')
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwks, ("RS256",)))',
                opts={'vars': {'t': toknope, 'jwks': jwks}}))[0])

            # a JWKS with no kid selector and multiple keys fails
            toknokid = await core.callStorm(
                '$t = $lib.crypto.jwt.generate() $t.payload.sub = "u" return($t.sign($prvpem, "RS256"))',
                opts={'vars': {'prvpem': prv1}})
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwks, ("RS256",)))',
                opts={'vars': {'t': toknokid, 'jwks': jwks}}))[0])

            # a single-key JWKS with no kid selector is used directly
            self.true((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwks, ("RS256",)))',
                opts={'vars': {'t': toknokid, 'jwks': {'keys': [jwk1]}}}))[0])

            # a malformed keys member and a malformed JWK are rejected
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwks, ("RS256",)))',
                opts={'vars': {'t': tok, 'jwks': {'keys': 'notalist'}}}))[0])
            badjwk = dict(jwk1, n='!!!')
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("RS256",)))',
                opts={'vars': {'t': tok, 'jwk': badjwk}}))[0])

            # an EC JWK verifies an ES256 token; an EC JWK for an RS256 token is rejected
            esprv, espub = await core.callStorm(
                '$k = $lib.crypto.ecc.generate(curve="P-256") return(($k.encode(), $k.pubkey().encode()))')
            ecjwk = eccJwk(espub, 'k1')
            estok = await core.callStorm('''
                $k = $lib.crypto.ecc.load($prvpem)
                $t = $lib.crypto.jwt.generate()
                $t.header.kid = "k1"
                $t.payload.sub = "u"
                return($t.sign($k, "ES256"))
            ''', opts={'vars': {'prvpem': esprv}})
            self.true((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("ES256",)))',
                opts={'vars': {'t': estok, 'jwk': ecjwk}}))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("RS256",)))',
                opts={'vars': {'t': tok, 'jwk': ecjwk}}))[0])

            # an RSA JWK for an ES256 token (kty/alg mismatch) is rejected
            es = await core.callStorm('''
                $k = $lib.crypto.ecc.generate(curve="P-256")
                $t = $lib.crypto.jwt.generate()
                $t.header.kid = "k1"
                $t.payload.sub = "u"
                return($t.sign($k, "ES256"))
            ''')
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("ES256",)))',
                opts={'vars': {'t': es, 'jwk': jwk1}}))[0])

            # an oct JWK verifies an HS256 token, and a non-oct JWK for HS256 is rejected
            octjwk = {'kty': 'oct', 'kid': 'h1', 'k': s_crypto.enbase64url(SECRET)}
            hstok = await core.callStorm('''
                $t = $lib.crypto.jwt.generate()
                $t.header.kid = "h1"
                $t.payload.sub = "u"
                return($t.sign($secret, "HS256"))
            ''', opts={'vars': {'secret': SECRET}})
            self.true((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("HS256",)))',
                opts={'vars': {'t': hstok, 'jwk': octjwk}}))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("HS256",)))',
                opts={'vars': {'t': hstok, 'jwk': jwk1}}))[0])

            # an oct JWK whose k is not valid base64url fails closed rather than leaking a raw
            # binascii error into the runtime
            badoct = {'kty': 'oct', 'kid': 'h1', 'k': 'AAAAA'}
            ok, info = await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $jwk, ("HS256",)))',
                opts={'vars': {'t': hstok, 'jwk': badoct}})
            self.false(ok)
            self.isin('Invalid HMAC JWK k value', info[1].get('mesg'))

    async def test_stormlib_jwt_jwks_uri(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')

            state = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1]})}
            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/jwks', JwksHandler, {'cell': core, 'state': state})
            # use localhost (not the 127.0.0.1 literal) so the fetch exercises the pinned resolver
            url = f'https://localhost:{port}/jwks'

            base = {'t': tok, 'k': None, 'url': url}

            # https is required
            httpurl = f'http://localhost:{port}/jwks'
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri=$url, ssl_verify=(false)))',
                opts={'vars': dict(base, url=httpurl)}))[0])

            # a jwks_uri missing a host, or with an unresolvable host, is rejected
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri="https:///jwks"))',
                opts={'vars': base}))[0])
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri="https://nx.invalid./jwks"))',
                opts={'vars': base}))[0])

            # a loopback jwks_uri is blocked unless allowinternal is set
            retn = await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri=$url, ssl_verify=(false)))',
                opts={'vars': base})
            self.false(retn[0])
            self.isin('non-global', retn[1][1].get('mesg'))
            self.eq(state['hits'], 0)

            # neither a key nor a jwks_uri is an error
            self.false((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",)))', opts={'vars': base}))[0])

            # happy path with allowinternal fetches and verifies
            ok, sub = await core.callStorm('''
                ($ok, $v) = $lib.crypto.jwt.verify($t, $k, ("RS256",),
                    jwks_uri=$url, ssl_verify=(false), allowinternal=(true))
                return(($ok, $v.payload.sub))
            ''', opts={'vars': base})
            self.true(ok)
            self.eq(sub, 'u')
            self.eq(state['hits'], 1)

            # a second verify is served from cache without another fetch
            self.true((await core.callStorm(
                'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))',
                opts={'vars': base}))[0])
            self.eq(state['hits'], 1)

    async def test_stormlib_jwt_jwks_uri_rotate(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            prv2, jwk2 = await self._mkkey(core, 'k2')
            tok1 = await self._sign(core, prv1, 'k1')
            tok2 = await self._sign(core, prv2, 'k2')

            state = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1]})}
            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/jwks', JwksHandler, {'cell': core, 'state': state})
            url = f'https://127.0.0.1:{port}/jwks'

            q = '''
                return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                    jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
            '''
            self.true((await core.callStorm(q, opts={'vars': {'t': tok1, 'k': None, 'url': url}}))[0])
            self.eq(state['hits'], 1)

            # rotate: the endpoint now serves both keys. An unknown kid forces one refresh.
            state['body'] = s_json.dumps({'keys': [jwk1, jwk2]})
            self.true((await core.callStorm(q, opts={'vars': {'t': tok2, 'k': None, 'url': url}}))[0])
            self.eq(state['hits'], 2)

    async def test_stormlib_jwt_jwks_uri_stale(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')

            state = {'hits': 0, 'code': 500, 'body': b''}
            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/jwks', JwksHandler, {'cell': core, 'state': state})
            url = f'https://127.0.0.1:{port}/jwks'

            # pre-seed an expired cache entry; the refresh fails (HTTP 500) and the stale set is served
            core.jwkscache[url] = (0.0, {'keys': [jwk1]})

            ok = (await core.callStorm('''
                return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                    jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
            ''', opts={'vars': {'t': tok, 'k': None, 'url': url}}))[0]
            self.true(ok)
            self.eq(state['hits'], 1)

    async def test_stormlib_jwt_jwks_uri_resolve_stale(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')

            url = 'https://rotated.example.com/jwks'
            opts = {'vars': {'t': tok, 'k': None, 'url': url}}
            q = 'return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri=$url, allowinternal=(true)))'

            async def boom(host, port):
                raise s_exc.BadArg(mesg='the resolver is down', url=host)

            with mock.patch.object(s_jwt, '_resolveJwksHost', boom):

                # a transient resolution failure with no cached entry hard-fails
                retn = await core.callStorm(q, opts=opts)
                self.false(retn[0])
                self.isin('the resolver is down', retn[1][1].get('mesg'))

                # the same failure with a present (stale) cache entry serves it rather than breaking
                core.jwkscache[url] = (0.0, {'keys': [jwk1]})
                self.true((await core.callStorm(q, opts=opts))[0])

    async def test_stormlib_jwt_jwks_uri_limits(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')

            addr, port = await core.addHttpsPort(0)

            def check(path, body, code=200):
                state = {'hits': 0, 'code': code, 'body': body}
                core.addHttpApi(path, JwksHandler, {'cell': core, 'state': state})
                url = f'https://127.0.0.1:{port}{path}'
                return core.callStorm('''
                    return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                        jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
                ''', opts={'vars': {'t': tok, 'k': None, 'url': url}})

            # a response larger than the cap, a non-JSON body, and a JSON body that is not a
            # JWKS object are all rejected
            self.false((await check('/big', s_json.dumps({'keys': [jwk1], 'pad': 'x' * (300 * 1024)})))[0])
            self.false((await check('/notjson', b'not json{'))[0])
            self.false((await check('/nokeys', s_json.dumps({'foo': 1})))[0])
            self.false((await check('/http500', b'', code=500))[0])

            # a configured proxy is used for the fetch (the bogus proxy makes the fetch fail)
            core.conf['http:proxy'] = 'socks5://127.0.0.1:1'
            state2 = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1]})}
            core.addHttpApi('/jwks2', JwksHandler, {'cell': core, 'state': state2})
            url2 = f'https://127.0.0.1:{port}/jwks2'
            self.false((await core.callStorm('''
                return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                    jwks_uri=$url, ssl_verify=(false), proxy=(true), allowinternal=(true)))
            ''', opts={'vars': {'t': tok, 'k': None, 'url': url2}}))[0])
            self.eq(state2['hits'], 0)

    async def test_stormlib_jwt_jwks_uri_singleflight(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')

            state = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1]})}
            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/jwks', JwksHandler, {'cell': core, 'state': state})
            url = f'https://127.0.0.1:{port}/jwks'

            q = '''
                return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                    jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
            '''
            opts = {'vars': {'t': tok, 'k': None, 'url': url}}

            # two concurrent verifies race the cache; single-flight collapses them to one fetch
            r1, r2 = await asyncio.gather(core.callStorm(q, opts=opts), core.callStorm(q, opts=opts))
            self.true(r1[0])
            self.true(r2[0])
            self.eq(state['hits'], 1)

    async def test_stormlib_jwt_jwks_uri_norefetch(self):

        async with self.getTestCore() as core:

            _, jwk1 = await self._mkkey(core, 'k1')
            _, jwk2 = await self._mkkey(core, 'k2')
            prv, _ = await self._mkkey(core, 'kx')
            addr, port = await core.addHttpsPort(0)

            # a no-kid token against a multi-key set: selection fails with no kid, so no refetch
            toknokid = await core.callStorm(
                '$t = $lib.crypto.jwt.generate() $t.payload.sub = "u" return($t.sign($prvpem, "RS256"))',
                opts={'vars': {'prvpem': prv}})
            stateA = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1, jwk2]})}
            core.addHttpApi('/a', JwksHandler, {'cell': core, 'state': stateA})
            urlA = f'https://localhost:{port}/a'
            self.false((await core.callStorm('''
                return($lib.crypto.jwt.verify($t, $k, ("RS256",), jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
            ''', opts={'vars': {'t': toknokid, 'k': None, 'url': urlA}}))[0])
            self.eq(stateA['hits'], 1)

            # a kid that IS present but is the wrong key type for the alg: no refetch either
            esprv, _ = await core.callStorm(
                '$k = $lib.crypto.ecc.generate(curve="P-256") return(($k.encode(), $k.pubkey().encode()))')
            estok = await core.callStorm('''
                $k = $lib.crypto.ecc.load($prvpem)
                $t = $lib.crypto.jwt.generate()
                $t.header.kid = "k1"
                $t.payload.sub = "u"
                return($t.sign($k, "ES256"))
            ''', opts={'vars': {'prvpem': esprv}})
            stateB = {'hits': 0, 'code': 200, 'body': s_json.dumps({'keys': [jwk1]})}
            core.addHttpApi('/b', JwksHandler, {'cell': core, 'state': stateB})
            urlB = f'https://localhost:{port}/b'
            self.false((await core.callStorm('''
                return($lib.crypto.jwt.verify($t, $k, ("ES256",), jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
            ''', opts={'vars': {'t': estok, 'k': None, 'url': urlB}}))[0])
            self.eq(stateB['hits'], 1)

    async def test_stormlib_jwt_jwks_uri_cache_bound(self):

        async with self.getTestCore() as core:

            prv1, jwk1 = await self._mkkey(core, 'k1')
            tok = await self._sign(core, prv1, 'k1')
            addr, port = await core.addHttpsPort(0)

            def add(path, code=200):
                state = {'hits': 0, 'code': code, 'body': s_json.dumps({'keys': [jwk1]})}
                core.addHttpApi(path, JwksHandler, {'cell': core, 'state': state})
                return f'https://localhost:{port}{path}'

            failurl = add('/fail', code=500)
            okurl1 = add('/ok1')
            okurl2 = add('/ok2')

            def verify(url):
                return core.callStorm('''
                    return($lib.crypto.jwt.verify($t, $k, ("RS256",),
                        jwks_uri=$url, ssl_verify=(false), allowinternal=(true)))
                ''', opts={'vars': {'t': tok, 'k': None, 'url': url}})

            with mock.patch.object(s_jwt, 'JWKS_CACHE_MAX', 1):
                # a failed fetch leaves an unlocked, uncached lock...
                self.false((await verify(failurl))[0])
                # ...which the next call prunes; and exceeding the cap evicts the oldest entry.
                self.true((await verify(okurl1))[0])
                self.true((await verify(okurl2))[0])

            self.le(len(core.jwkscache), 1)

            # a zero cap exercises the "nothing else to evict" break
            with mock.patch.object(s_jwt, 'JWKS_CACHE_MAX', 0):
                self.true((await verify(add('/ok3')))[0])

    async def test_stormlib_jwt_pinned_resolver(self):

        addrs = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('1.2.3.4', 443))]
        resolver = s_jwt._PinnedResolver(addrs)

        res = await resolver.resolve('example.com', 443, socket.AF_INET)
        self.eq(res[0]['host'], '1.2.3.4')
        self.eq(res[0]['hostname'], 'example.com')

        # a mismatched address family is filtered out
        self.eq(await resolver.resolve('example.com', 443, socket.AF_INET6), [])

        await resolver.close()
