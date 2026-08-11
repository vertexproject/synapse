import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.jwk as s_jwk
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.utils as s_crypto

def i2b64(i):
    return s_crypto.enbase64url(i.to_bytes((i.bit_length() + 7) // 8 or 1, 'big'))

class JwkTest(s_t_utils.SynTest):

    def test_lib_crypto_jwk_rsa(self):

        prikey = s_rsa.PriKey.generate(bits=2048)
        pubkey = prikey.public()
        pn = pubkey.publ.public_numbers()

        pubjwk = {'kty': 'RSA', 'n': i2b64(pn.n), 'e': i2b64(pn.e)}
        loaded = s_jwk.jwkToKey(pubjwk)
        self.isinstance(loaded, s_rsa.PubKey)
        self.true(loaded.verify(b'data', prikey.sign(b'data', padding='pkcs1v15'), padding='pkcs1v15'))

        # a private RSA JWK reconstructs a usable private key
        prn = prikey.priv.private_numbers()
        privjwk = {'kty': 'RSA', 'n': i2b64(pn.n), 'e': i2b64(pn.e), 'd': i2b64(prn.d),
                   'p': i2b64(prn.p), 'q': i2b64(prn.q), 'dp': i2b64(prn.dmp1),
                   'dq': i2b64(prn.dmq1), 'qi': i2b64(prn.iqmp)}
        priv = s_jwk.jwkToKey(privjwk)
        self.isinstance(priv, s_rsa.PriKey)
        self.true(pubkey.verify(b'data', priv.sign(b'data', padding='pss'), padding='pss'))

        # malformed / non-dict / bad base64 JWKs raise ValueError
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, {'kty': 'RSA', 'n': i2b64(pn.n)})
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, 'notadict')
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, {'kty': 'RSA', 'n': '!!!', 'e': 'AQAB'})
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, {'kty': 'newp'})
        # a JWK member is strict base64url: embedded whitespace is rejected, not ignored
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, {'kty': 'RSA', 'n': i2b64(pn.n) + ' ', 'e': 'AQAB'})

    def test_lib_crypto_jwk_ec(self):

        for curve, clen in (('P-256', 32), ('P-384', 48), ('P-521', 66)):

            prikey = s_ecc.PriKey.generate(curve=curve)
            pubkey = prikey.public()
            pn = pubkey.publ.public_numbers()

            def coord(i):
                return s_crypto.enbase64url(i.to_bytes(clen, 'big'))

            pubjwk = {'kty': 'EC', 'crv': curve, 'x': coord(pn.x), 'y': coord(pn.y)}
            loaded = s_jwk.jwkToKey(pubjwk)
            self.isinstance(loaded, s_ecc.PubKey)
            self.true(loaded.verify(b'data', prikey.sign(b'data')))

            dn = prikey.priv.private_numbers()
            privjwk = dict(pubjwk, d=coord(dn.private_value))
            priv = s_jwk.jwkToKey(privjwk)
            self.isinstance(priv, s_ecc.PriKey)
            self.true(pubkey.verify(b'data', priv.sign(b'data')))

        # an off-curve point is rejected
        prikey = s_ecc.PriKey.generate(curve='P-256')
        pn = prikey.public().publ.public_numbers()
        offcurve = {'kty': 'EC', 'crv': 'P-256',
                    'x': s_crypto.enbase64url(pn.x.to_bytes(32, 'big')), 'y': s_crypto.enbase64url((pn.y ^ 1).to_bytes(32, 'big'))}
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, offcurve)

        # an unknown curve is rejected
        self.raises(s_exc.BadArg, s_jwk.jwkToKey, {'kty': 'EC', 'crv': 'P-999', 'x': 'AA', 'y': 'AA'})

    def test_lib_crypto_jwk_thumbprint(self):

        # RFC 7638 3.1 canonical example vector
        rfc = {
            'kty': 'RSA',
            'n': '0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4'
                 'cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n'
                 '3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ'
                 '5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHz'
                 'u6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0f'
                 'M4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw',
            'e': 'AQAB',
        }
        self.eq(s_jwk.jwkThumbprint(rfc), 'NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs')

        # EC and oct produce thumbprints; missing members and unknown kty raise
        eck = s_ecc.PriKey.generate(curve='P-256')
        en = eck.public().publ.public_numbers()
        ecjwk = {'kty': 'EC', 'crv': 'P-256',
                 'x': s_crypto.enbase64url(en.x.to_bytes(32, 'big')), 'y': s_crypto.enbase64url(en.y.to_bytes(32, 'big'))}
        self.isinstance(s_jwk.jwkThumbprint(ecjwk), str)
        self.isinstance(s_jwk.jwkThumbprint({'kty': 'oct', 'k': 'AAAA'}), str)

        self.raises(s_exc.BadArg, s_jwk.jwkThumbprint, {'kty': 'RSA', 'e': 'AQAB'})
        self.raises(s_exc.BadArg, s_jwk.jwkThumbprint, {'kty': 'newp'})
