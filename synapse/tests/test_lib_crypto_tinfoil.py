
import synapse.lib.crypto.tinfoil as s_tinfoil

from synapse.tests.common import *

class TinFoilTest(SynTest):

    def test_lib_crypto_tinfoil(self):

        ekey = s_tinfoil.newkey()
        tinh = s_tinfoil.TinFoilHat(ekey)

        byts = tinh.enc(b'foobar')

        self.eq(tinh.dec(byts), b'foobar')
