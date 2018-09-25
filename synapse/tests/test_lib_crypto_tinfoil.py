
import os
import hashlib
import binascii

from cryptography.hazmat.backends import default_backend

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.tinfoil as s_tinfoil

class TinFoilTest(s_t_utils.SynTest):

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
        self.len(6 + 16, data)

        iv = edict.get('iv')
        self.isinstance(iv, bytes)
        self.len(16, iv)

        asscd = edict.get('asscd')
        self.eq(asscd, None)

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

        # Messages are stream encoded so the length is 1 to 1
        for msize in [0, 1, 2, 15, 16, 17, 31, 32, 33, 63, 65]:
            mesg = msize * b'!'
            byts = tinh.enc(mesg)
            edict = s_msgpack.un(byts)

            self.len(16, edict.get('iv'))
            data = edict.get('data')
            self.len(len(mesg) + 16, data)
            self.eq(tinh.dec(byts), mesg)

        # We can pass in additional data that we want authed too
        byts = tinh.enc(b'robert grey', b'pennywise')
        edict = s_msgpack.un(byts)
        self.eq(edict.get('asscd'), b'pennywise')
        self.eq(tinh.dec(byts), b'robert grey')
        # A malformed edict with a bad asscd won't decrypt
        edict['asscd'] = b'georgey'
        self.none(tinh.dec(s_msgpack.en(edict)))

    def test_lib_crypto_tnfl_break(self):
        ekey = s_tinfoil.newkey()
        tinh = s_tinfoil.TinFoilHat(ekey)

        goodbyts = tinh.enc(b'foobar', b'hehe')
        edict = s_msgpack.un(goodbyts)

        # Empty values will fail to decrypt
        for key in ('iv', 'data', 'asscd'):
            bdict = {k: v for k, v in edict.items() if k != key}
            byts = s_msgpack.en(bdict)
            self.none(tinh.dec(byts))

        # Tampered values will fail
        bdict = {k: v for k, v in edict.items()}
        bdict['iv'] = os.urandom(16)
        byts = s_msgpack.en(bdict)
        self.none(tinh.dec(byts))

        bdict = {k: v for k, v in edict.items()}
        bdict['data'] = os.urandom(16)
        byts = s_msgpack.en(bdict)
        self.none(tinh.dec(byts))

        bdict = {k: v for k, v in edict.items()}
        bdict['asscd'] = os.urandom(16)
        byts = s_msgpack.en(bdict)
        self.none(tinh.dec(byts))

    def test_lib_crypto_tnfl_vector(self):
        key = binascii.unhexlify(b'fc066c018159a674c13ae1fb7c5c6548a4e05a11d742a0ebed35d28724b767b0')

        edict = {'data': b'02f9f72c9164e231f0e6795fd1d1fb21db6e8b0c049ef611ea6'
                         b'432ed8ec6d54b245d66864b06cc6cbdc52ebf5f0dbe1382b42e'
                         b'94a67411f7042d0562f3fd9b1a6961aacff69292aa596382c9f'
                         b'869e2957269191c5f916f56889188db03eb60d2caf7f7dd7388'
                         b'a5a9ef13494aaeb905f08e658fbb907afd7169b879b0313d065'
                         b'c1045e844c039b43296f44d6bc5',
                 'hmac': b'fb4b53fb2b94d4ef91b5a094ab786b879ba6274384e23da15f7990609df5ab88',
                 'iv': b'ecf8ed3d7932834fc76b7323d6ab73ce',
                 'asscd': b''
                 }
        msg = s_msgpack.en({k: binascii.unhexlify(v) for k, v in edict.items()})
        tinh = s_tinfoil.TinFoilHat(key)
        self.eq(hashlib.md5(tinh.dec(msg)).digest(),
                binascii.unhexlify(b'3303e226461e38f0f36988e441825e19'))

    def test_lib_crypto_tnfl_cryptseq(self):
        txk = s_common.buid()
        rxk = s_common.buid()

        crypter1 = s_tinfoil.CryptSeq(rxk, txk)
        crypter2 = s_tinfoil.CryptSeq(txk, rxk)
        mesg = ('hehe', {'key': 'valu'})

        self.eq(str(crypter1._tx_sn), 'count(0)')
        self.eq(str(crypter2._rx_sn), 'count(0)')
        ct = crypter1.encrypt(mesg)
        self.isinstance(ct, bytes)
        self.eq(str(crypter1._tx_sn), 'count(1)')

        pt = crypter2.decrypt(ct)
        self.eq(str(crypter2._rx_sn), 'count(1)')
        self.eq(mesg, pt)

        self.raises(s_exc.CryptoErr, crypter1.decrypt, ct)
        self.eq(str(crypter1._rx_sn), 'count(0)')

        self.raises(s_exc.CryptoErr, crypter2.decrypt, ct)
        self.eq(str(crypter2._rx_sn), 'count(2)')  # even though we fail, we've incremented the seqn valu
