import hashlib
import binascii

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
        self.len(16, data)  # The output is padded

        iv = edict.get('iv')
        self.isinstance(iv, bytes)
        self.len(16, iv)

        hmac = edict.get('hmac')
        self.isinstance(hmac, bytes)
        self.len(32, hmac)

        # We can decrypt and get our original message back
        self.eq(tinh.dec(byts), b'foobar')

        # There isn't anythign special about the tinfoilhat object
        # We can make a new one to decrypt our existing message with
        # the known key
        self.eq(s_tinfoil.TinFoilHat(ekey).dec(byts), b'foobar')

        # We can encrypt/decrypt null messages
        byts = tinh.enc(b'')
        self.eq(tinh.dec(byts), b'')

        # Attempting to decrypt with the wrong key fails
        self.none(s_tinfoil.TinFoilHat(s_tinfoil.newkey()).dec(byts))

        # Messages are padded to expected lengths
        for msize in [0, 1, 2, 15, 16, 17, 31, 32, 33, 63, 65]:
            mesg = msize * b'!'
            byts = tinh.enc(mesg)
            edict = s_msgpack.un(byts)

            self.len(16, edict.get('iv'))
            self.len(32, edict.get('hmac'))

            mul = msize // 16
            elen = (mul + 1) * 16

            data = edict.get('data')
            print(msize, elen, mesg)
            self.len(elen, data)  # The output is padded
            self.eq(tinh.dec(byts), mesg)

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

    def test_lib_crypto_tnfl_vector(self):
        key = binascii.unhexlify(b'fc066c018159a674c13ae1fb7c5c6548a4e05a11d742a0ebed35d28724b767b0')
        edict = {'data': b'339f3a4efd4b158d61f87b303655fe1e971e83eaba41d9ea7076991f85a995953cc7598c'
                         b'745f3e159edbb36a4c03d2b138dc599434fa59e3ee3a2f39335c2addef531244644db350'
                         b'4b13a6e5f93d4019063550ddee5cd66b277000683144f5b066c30eab08309990cafee7f2'
                         b'9d23fedc7240bbe41d152a0b769e64c5aac6ac4c',
                 'hmac': b'fb4b53fb2b94d4ef91b5a094ab786b879ba6274384e23da15f7990609df5ab88',
                 'iv': b'575a0ee4c0293b444e67a8ac27ee34fb',
                 }
        msg = s_msgpack.en({k: binascii.unhexlify(v) for k, v in edict.items()})
        tinh = s_tinfoil.TinFoilHat(key)
        self.eq(hashlib.md5(tinh.dec(msg)).digest(),
                binascii.unhexlify(b'3303e226461e38f0f36988e441825e19'))
