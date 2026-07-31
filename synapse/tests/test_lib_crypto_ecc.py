
import os
import hashlib

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.kdf.hkdf as c_hkdf
from cryptography.hazmat.backends import default_backend
import cryptography.hazmat.primitives.asymmetric.ec as c_ec

import synapse.exc as s_exc
import synapse.lib.const as s_const
import synapse.tests.utils as s_t_utils
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.utils as s_crypto

class EccTest(s_t_utils.SynTest):

    def test_lib_crypto_ecc_keys(self):

        prikey = s_ecc.PriKey.generate()
        pubkey = prikey.public()

        sign = prikey.sign(b'haha')
        self.true(pubkey.verify(b'haha', sign))
        self.false(pubkey.verify(b'haha', b'newp'))

        prib = prikey.dump()
        pubb = pubkey.dump()
        self.isinstance(prib, bytes)
        self.isinstance(pubb, bytes)

        # Validate iden is as expected
        self.eq(prikey.iden(), hashlib.sha256(pubb).hexdigest())
        self.eq(pubkey.iden(), hashlib.sha256(pubb).hexdigest())

        # Test staticmethods
        newpri = s_ecc.PriKey.load(prib)
        newpub = s_ecc.PubKey.load(pubb)
        self.isinstance(newpri, s_ecc.PriKey)
        self.isinstance(newpub, s_ecc.PubKey)

        nsign = newpri.sign(b'haha')
        self.true(newpub.verify(b'haha', nsign))
        self.true(newpub.verify(b'haha', sign))
        self.false(newpub.verify(b'haha', b'newp'))

        # Sign a huge chunk of data
        byts = s_const.mebibyte * b'S'
        sign = prikey.sign(byts)
        self.true(pubkey.verify(byts, sign))

    def test_lib_crypto_ecc_curves_algs_pem(self):

        # default curve is SECP384R1 (backward compatible)
        prikey = s_ecc.PriKey.generate()
        self.eq(prikey.priv.curve.name, 'secp384r1')

        for curve, name, hashalgo in (('P-256', 'secp256r1', 'sha256'),
                                 ('secp256r1', 'secp256r1', 'sha256'),
                                 ('P-384', 'secp384r1', 'sha384'),
                                 ('P-521', 'secp521r1', 'sha512')):

            prikey = s_ecc.PriKey.generate(curve=curve)
            self.eq(prikey.priv.curve.name, name)

            pubkey = prikey.public()

            # sign / verify round trip with a selectable hash
            sign = prikey.sign(b'haha', hashalgo=hashalgo)
            self.true(pubkey.verify(b'haha', sign, hashalgo=hashalgo))
            self.false(pubkey.verify(b'nope', sign, hashalgo=hashalgo))

            # PEM round trip
            pemprv = prikey.dump(fmt='pem')
            pempub = pubkey.dump(fmt='pem')
            self.true(pemprv.startswith(b'-----BEGIN'))
            self.true(pempub.startswith(b'-----BEGIN'))

            newpri = s_ecc.PriKey.load(pemprv, fmt='pem')
            newpub = s_ecc.PubKey.load(pempub, fmt='pem')
            self.eq(newpri.priv.curve.name, name)
            self.true(newpub.verify(b'haha', sign, hashalgo=hashalgo))

        # unknown curve / hash / encoding format raise BadArg
        self.raises(s_exc.BadArg, s_ecc.PriKey.generate, curve='newp')
        self.raises(s_exc.BadArg, s_crypto.getCurveByName, 'newp')
        self.raises(s_exc.BadArg, s_crypto.getHashByName, 'newp')
        self.raises(s_exc.BadArg, s_crypto.getEncodingByName, 'newp')
        self.raises(s_exc.BadArg, prikey.dump, fmt='newp')
        self.raises(s_exc.BadArg, s_ecc.PriKey.load, pemprv, fmt='newp')

        # the fmt argument is case insensitive
        self.eq(prikey.dump(fmt='pem'), prikey.dump(fmt='PEM'))
        self.nn(s_ecc.PriKey.load(prikey.dump(fmt='PEM'), fmt='Pem'))

    def test_lib_crypto_ecc_break(self):
        pvk1 = s_ecc.PriKey.generate()
        pbk1 = pvk1.public()

        pvk2 = s_ecc.PriKey.generate()
        pbk2 = pvk2.public()

        mesg = 'We all float down here'.encode()
        sig1 = pvk1.sign(mesg)

        # Cannot cross validate messages
        self.false(pbk2.verify(mesg, sig1))

        # Tampered messages fail to validate
        self.false(pbk1.verify(mesg, sig1[:-10] + os.urandom(10)))
        self.false(pbk1.verify(mesg, os.urandom(10) + sig1[:10]))

    def test_lib_crypto_ecc_loadkey(self):

        import synapse.lib.crypto.rsa as s_rsa

        prikey = s_ecc.PriKey.generate(curve='P-256')
        pubkey = prikey.public()

        # PEM/DER and public/private are auto-detected
        self.isinstance(s_ecc.loadKey(prikey.dump(fmt='pem')), s_ecc.PriKey)
        self.isinstance(s_ecc.loadKey(pubkey.dump(fmt='pem')), s_ecc.PubKey)
        self.isinstance(s_ecc.loadKey(prikey.dump(fmt='der')), s_ecc.PriKey)
        self.isinstance(s_ecc.loadKey(pubkey.dump(fmt='der')), s_ecc.PubKey)

        # a blob containing more than one key is rejected
        with self.raises(s_exc.BadArg):
            s_ecc.loadKey(prikey.dump(fmt='pem') + pubkey.dump(fmt='pem'))

        # an RSA key (public or private) is not an ECC key
        rsak = s_rsa.PriKey.generate(bits=1024)
        with self.raises(s_exc.BadArg):
            s_ecc.loadKey(rsak.dump(fmt='pem'))

        with self.raises(s_exc.BadArg):
            s_ecc.loadKey(rsak.public().dump(fmt='pem'))

        # garbage bytes are rejected
        with self.raises(ValueError):
            s_ecc.loadKey(b'not a key')

    def test_lib_crypto_ecc_exchange(self):
        spvk1 = s_ecc.PriKey.generate()
        spbk1 = spvk1.public()

        spvk2 = s_ecc.PriKey.generate()
        spbk2 = spvk2.public()

        k1 = (spvk1.exchange(spbk2))
        k2 = (spvk2.exchange(spbk1))
        self.eq(k1, k2)

        # Curves must be the same
        _pkd = c_ec.generate_private_key(
            c_ec.SECP192R1(),  # We don't use this curve
            default_backend()
        )
        prkdiff = s_ecc.PriKey(_pkd)
        pbkdiff = prkdiff.public()
        self.raises(s_exc.BadEccExchange, spvk1.exchange, pbkdiff)
        self.raises(s_exc.BadEccExchange, prkdiff.exchange, spbk1)

        # Do a demonstrative ephemeral exchange
        epvk1 = s_ecc.PriKey.generate()
        epbk1 = epvk1.public()

        epvk2 = s_ecc.PriKey.generate()
        epbk2 = epvk2.public()

        # assume epbk2 is sent to the owner of pvk1
        z1e = epvk1.exchange(epbk2)
        z1s = spvk1.exchange(spbk2)
        z1 = z1e + z1s

        # assume epbk1 is sent to the owner of pvk2
        z2e = epvk2.exchange(epbk1)
        z2s = spvk2.exchange(spbk1)
        z2 = z2e + z2s

        self.eq(z1, z2)

        # run through kdf
        kdf1 = c_hkdf.HKDF(c_hashes.SHA256(),
                           length=64,
                           salt=None,
                           info=b'test',
                           backend=default_backend())
        k1 = kdf1.derive(z1)
        k1tx, k1rx = k1[32:], k1[:32]

        kdf2 = c_hkdf.HKDF(c_hashes.SHA256(),
                           length=64,
                           salt=None,
                           info=b'test',
                           backend=default_backend())
        k2 = kdf2.derive(z2)
        k2rx, k2tx = k2[32:], k2[:32]

        self.eq(k1tx, k2rx)
        self.eq(k1rx, k2tx)
        self.ne(k1tx, k2tx)

    def test_lib_crypto_ecc_doecdhe(self):
        spvk1 = s_ecc.PriKey.generate()
        spbk1 = spvk1.public()

        spvk2 = s_ecc.PriKey.generate()
        spbk2 = spvk2.public()

        epvk1 = s_ecc.PriKey.generate()
        epbk1 = epvk1.public()

        epvk2 = s_ecc.PriKey.generate()
        epbk2 = epvk2.public()

        k1 = s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2)
        self.isinstance(k1, bytes)
        self.len(64, k1)  # Default length
        # It is a deterministic function
        self.eq(k1, s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2))
        # But the results are not eq if we salt it or provide info
        sk1 = s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2, salt=b'test')
        self.ne(k1, sk1)
        tk1 = s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2, info=b'test')
        self.ne(k1, tk1)
        stk1 = s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2, info=b'test', salt=b'test')
        self.ne(k1, stk1)
        self.ne(stk1, tk1)
        self.ne(stk1, sk1)
        # We can change the output length too
        k2 = s_ecc.doECDHE(spvk1, spbk2, epvk1, epbk2, length=128)
        self.len(128, k2)

        # And the other side can do the same derivation in order to
        # generate the same key
        self.eq(k1, s_ecc.doECDHE(spvk2, spbk1, epvk2, epbk1))
