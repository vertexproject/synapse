from cryptography.hazmat.backends import default_backend

import synapse.lib.crypto.tinfoil as s_tinfoil

from synapse.tests.common import *

class TinFoilTest(SynTest):

    def test_lib_crypto_tnfl_base(self):

        ekey = s_tinfoil.newkey()
        self.len(32, ekey)
        self.isinstance(ekey, bytes)

        # Keys are random from s_tinfoil.newkey
        self.ne(ekey, s_tinfoil.newkey())
        self.ne(ekey, s_tinfoil.newkey())

        tinh = s_tinfoil.TinFoilHat(ekey)
        self.true(tinh.bend is default_backend())

        byts = tinh.enc(b'foobar')

        # Ensure the envelope is shaped as we expect it too be
        edict = s_msgpack.un(byts)
        self.isinstance(edict, dict)
        self.len(3, edict)

        data = edict.get('data')
        self.isinstance(data, bytes)
        self.gt(len(data), 1)

        iv = edict.get('iv')
        self.isinstance(iv, bytes)
        self.gt(len(iv), 1)

        hmac = edict.get('hmac')
        self.isinstance(hmac, bytes)
        self.gt(len(hmac), 1)

        # We can decrypt and get our original message back
        self.eq(tinh.dec(byts), b'foobar')

        # There isn't anythign special about the tinfoilhat object
        # We can make a new one to decrypt our existing message with
        # the known key
        self.eq(s_tinfoil.TinFoilHat(ekey).dec(byts), b'foobar')

        # Attempting to decrypt with the wrong key fails
        self.none(s_tinfoil.TinFoilHat(s_tinfoil.newkey()).dec(byts))

    def test_lib_crypto_tnfl_break(self):
        ekey = s_tinfoil.newkey()
        tinh = s_tinfoil.TinFoilHat(ekey)

        goodbyts = tinh.enc(b'foobar')
        edict = s_msgpack.un(goodbyts)

        # Empty values will fail
        for key in ('iv', 'hmac', 'data'):
            bdict = {k: v for k, v in edict.items() if k != key}
            byts = s_msgpack.en(bdict)
            self.false(tinh.dec(byts))

        # Tampered values will fail
        bdict = {k: v for k, v in edict.items()}
        bdict['iv'] = os.urandom(16)
        byts = s_msgpack.en(bdict)
        self.false(tinh.dec(byts))

        bdict = {k: v for k, v in edict.items()}
        bdict['hmac'] = os.urandom(32)
        byts = s_msgpack.en(bdict)
        self.false(tinh.dec(byts))

        bdict = {k: v for k, v in edict.items()}
        bdict['data'] = os.urandom(16)
        byts = s_msgpack.en(bdict)
        self.false(tinh.dec(byts))
