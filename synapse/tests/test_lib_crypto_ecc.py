import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.kdf.hkdf as c_hkdf

from cryptography.hazmat.backends import default_backend

import synapse.lib.crypto.ecc as s_ecc

from synapse.tests.common import *

class EccTest(SynTest):

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

    def test_lib_crypto_ecc_exchange(self):
        pvk1 = s_ecc.PriKey.generate()
        pbk1 = pvk1.public()

        pvk2 = s_ecc.PriKey.generate()
        pbk2 = pvk2.public()

        k1 = (pvk1.exchange(pbk2))
        k2 = (pvk2.exchange(pbk1))
        self.eq(k1, k2)

        # Do a demonstrative ephemeral exchange
        epvk1 = s_ecc.PriKey.generate()
        epbk1 = epvk1.public()

        epvk2 = s_ecc.PriKey.generate()
        epbk2 = epvk2.public()

        # assume epbk2 is sent to the owner of pvk1
        z1e = epvk1.exchange(epbk2)
        z1s = pvk1.exchange(pbk2)
        z1 = z1e + z1s

        # assume epbk1 is sent to the owner of pvk2
        z2e = epvk2.exchange(epbk1)
        z2s = pvk2.exchange(pbk1)
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
