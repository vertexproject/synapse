
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

        newpri = s_rsa.PriKey.load(prib)
        newpub = s_rsa.PubKey.load(pubb)

        encr = newpub.encrypt(b'woot')
        self.eq(b'woot', newpri.decrypt(encr))

        sign = newpri.sign(b'haha')
        self.true(newpub.verify(b'haha', sign))
        self.false(newpub.verify(b'haha', b'newp'))

    #def test_lib_crypto_rsa_saveload(self):
