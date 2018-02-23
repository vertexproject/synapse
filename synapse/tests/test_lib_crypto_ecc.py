import synapse.lib.const as s_const
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
