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

    #def test_lib_crypto_rsa_saveload(self):
