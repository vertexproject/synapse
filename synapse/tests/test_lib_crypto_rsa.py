import hashlib

import synapse.lib.crypto.rsa as s_rsa

from synapse.tests.common import *

class RsaTest(SynTest):

    def test_lib_crypto_rsa_keys(self):

        prikey = s_rsa.PriKey.generate()
        pubkey = prikey.public()

        encr = pubkey.encrypt(b'woot')
        self.eq(b'woot', prikey.decrypt(encr))

        sign = prikey.sign(b'haha')
        self.true(pubkey.verify(b'haha', sign))
        self.false(pubkey.verify(b'haha', b'newp'))

        prib = prikey.save()
        pubb = pubkey.save()
        self.isinstance(prib, bytes)
        self.isinstance(pubb, bytes)

        # Validate iden is as expected
        self.eq(prikey.iden(), hashlib.sha256(pubb).hexdigest())
        self.eq(pubkey.iden(), hashlib.sha256(pubb).hexdigest())

        # Test staticmethods
        newpri = s_rsa.PriKey.load(prib)
        newpub = s_rsa.PubKey.load(pubb)
        self.isinstance(newpri, s_rsa.PriKey)
        self.isinstance(newpub, s_rsa.PubKey)

        nencr = newpub.encrypt(b'woot')
        self.eq(b'woot', newpri.decrypt(encr))
        self.eq(b'woot', newpri.decrypt(nencr))

        nsign = newpri.sign(b'haha')
        self.true(newpub.verify(b'haha', nsign))
        self.true(newpub.verify(b'haha', sign))
        self.false(newpub.verify(b'haha', b'newp'))

    def test_lib_crypto_rsa_break(self):
        pvk1 = s_rsa.PriKey.generate()
        pbk1 = pvk1.public()

        pvk2 = s_rsa.PriKey.generate()
        pbk2 = pvk2.public()

        mesg = 'We all float down here'.encode()
        sig1 = pvk1.sign(mesg)
        enc1 = pbk1.encrypt(mesg)

        # Cannot cross validate / decrypt messages
        self.false(pbk2.verify(mesg, sig1))
        self.none(pvk2.decrypt(enc1))

        # Tampered messages fail to validate
        self.false(pbk1.verify(mesg, sig1[:-10] + os.urandom(10)))
        self.false(pbk1.verify(mesg, os.urandom(10) + sig1[:10]))

        self.none(pvk1.decrypt(sig1[:-10] + os.urandom(10)))
        self.none(pvk1.decrypt(os.urandom(10) + sig1[:10]))
