import synapse.lib.crypto as s_crypto
from synapse.tests.common import *

class CryptoTest(SynTest):

    def test_lib_crypto_tinfoilhat(self):
        ekey = s_crypto.newkey()
        tinh = s_crypto.TinFoilHat(ekey)

        byts = tinh.enc(b'foobar')

        self.eq(tinh.dec(byts), b'foobar')
