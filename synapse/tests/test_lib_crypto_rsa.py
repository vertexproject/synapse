
import os
import hashlib

import synapse.exc as s_exc
import synapse.lib.const as s_const
import synapse.tests.utils as s_t_utils
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.utils as s_crypto

class RsaTest(s_t_utils.SynTest):

    def test_lib_crypto_rsa_keys(self):

        prikey = s_rsa.PriKey.generate()
        pubkey = prikey.public()

        sign = prikey.sign(b'haha')
        self.true(pubkey.verify(b'haha', sign))
        self.false(pubkey.verify(b'haha', b'newp'))

        prib = prikey.dump()
        pubb = pubkey.dump()
        self.isinstance(prib, bytes)
        self.isinstance(pubb, bytes)

        # the public key can also be dumped as PEM/SubjectPublicKeyInfo
        pubpem = pubkey.dump(fmt='pem')
        self.isinstance(pubpem, bytes)
        self.true(pubpem.startswith(b'-----BEGIN PUBLIC KEY-----'))
        self.true(pubpem.rstrip().endswith(b'-----END PUBLIC KEY-----'))

        # Validate iden is as expected
        self.eq(prikey.iden(), hashlib.sha256(pubb).hexdigest())
        self.eq(pubkey.iden(), hashlib.sha256(pubb).hexdigest())

        # Test staticmethods
        newpri = s_rsa.PriKey.load(prib)
        newpub = s_rsa.PubKey.load(pubb)
        self.isinstance(newpri, s_rsa.PriKey)
        self.isinstance(newpub, s_rsa.PubKey)
        self.eq(newpri.dump(), prib)
        self.eq(newpub.dump(), pubb)

        nsign = newpri.sign(b'haha')
        self.true(newpub.verify(b'haha', nsign))
        self.true(newpub.verify(b'haha', sign))
        self.false(newpub.verify(b'haha', b'newp'))

        # Sign a huge chunk of data
        byts = s_const.mebibyte * b'S'
        sign = prikey.sign(byts)
        self.true(pubkey.verify(byts, sign))

        # signitem / verifyitem round-trip a python primitive
        item = ('foo', {'bar': 1})
        isign = prikey.signitem(item)
        self.true(pubkey.verifyitem(item, isign))
        self.false(pubkey.verifyitem(('foo', {'bar': 2}), isign))

        # A larger key size may be requested
        bigpri = s_rsa.PriKey.generate(bits=3072)
        self.isinstance(bigpri, s_rsa.PriKey)

    def test_lib_crypto_rsa_signverify_algs(self):

        # getHashByName resolves the supported hashes and rejects anything else
        for hashalgo in ('sha256', 'sha384', 'sha512'):
            self.eq(s_crypto.getHashByName(hashalgo).name, hashalgo)

        # hash names are case insensitive (matches the ecc backend)
        self.eq(s_crypto.getHashByName('SHA256').name, 'sha256')
        self.eq(s_crypto.getHashByName('Sha512').name, 'sha512')

        with self.raises(s_exc.BadArg):
            s_crypto.getHashByName('newp')

        prikey = s_rsa.PriKey.generate()
        pubkey = prikey.public()

        mesg = 'we all float down here'.encode()

        for hashalgo in ('sha256', 'sha384', 'sha512'):

            other = 'sha512' if hashalgo != 'sha512' else 'sha256'

            # pkcs1v15 round-trips, is deterministic, and rejects tampering / wrong hash
            v15 = prikey.sign(mesg, padding='pkcs1v15', hashalgo=hashalgo)
            self.isinstance(v15, bytes)
            self.true(pubkey.verify(mesg, v15, padding='pkcs1v15', hashalgo=hashalgo))
            self.eq(v15, prikey.sign(mesg, padding='pkcs1v15', hashalgo=hashalgo))
            self.false(pubkey.verify('tampered'.encode(), v15, padding='pkcs1v15', hashalgo=hashalgo))
            self.false(pubkey.verify(mesg, v15, padding='pkcs1v15', hashalgo=other))

            # pss round-trips, is probabilistic, and rejects tampering / wrong hash
            pss = prikey.sign(mesg, padding='pss', hashalgo=hashalgo)
            self.isinstance(pss, bytes)
            self.true(pubkey.verify(mesg, pss, padding='pss', hashalgo=hashalgo))
            self.ne(pss, prikey.sign(mesg, padding='pss', hashalgo=hashalgo))
            self.false(pubkey.verify('tampered'.encode(), pss, padding='pss', hashalgo=hashalgo))
            self.false(pubkey.verify(mesg, pss, padding='pss', hashalgo=other))

        # pss is the default padding for verify
        pss = prikey.sign(mesg, padding='pss')
        self.true(pubkey.verify(mesg, pss))

        # padding schemes do not cross-validate
        v15 = prikey.sign(mesg, padding='pkcs1v15')
        self.false(pubkey.verify(mesg, v15))
        self.false(pubkey.verify(mesg, pss, padding='pkcs1v15'))

        # an unknown padding scheme raises BadArg on both sign and verify
        self.raises(s_exc.BadArg, prikey.sign, mesg, padding='newp')
        self.raises(s_exc.BadArg, pubkey.verify, mesg, pss, padding='newp')

        # padding names are case insensitive
        self.true(pubkey.verify(mesg, prikey.sign(mesg, padding='PSS'), padding='PSS'))
        self.true(pubkey.verify(mesg, prikey.sign(mesg, padding='PKCS1V15'), padding='PKCS1V15'))

        # PriKey PEM dump / load round-trips and the reloaded keys interoperate
        pripem = prikey.dump(fmt='pem')
        pubpem = pubkey.dump(fmt='pem')
        self.isinstance(pripem, bytes)
        self.true(pripem.startswith(b'-----BEGIN PRIVATE KEY-----'))

        newpri = s_rsa.PriKey.load(pripem, fmt='pem')
        newpub = s_rsa.PubKey.load(pubpem, fmt='pem')
        self.isinstance(newpri, s_rsa.PriKey)
        self.isinstance(newpub, s_rsa.PubKey)

        sig = newpri.sign(mesg, padding='pss', hashalgo='sha384')
        self.true(pubkey.verify(mesg, sig, padding='pss', hashalgo='sha384'))
        self.true(newpub.verify(mesg, prikey.sign(mesg, padding='pkcs1v15', hashalgo='sha512'),
                                padding='pkcs1v15', hashalgo='sha512'))

        # an unknown encoding format raises BadArg
        self.raises(s_exc.BadArg, s_crypto.getEncodingByName, 'newp')
        self.raises(s_exc.BadArg, prikey.dump, fmt='newp')
        self.raises(s_exc.BadArg, s_rsa.PriKey.load, pripem, fmt='newp')

        # the fmt argument is case insensitive
        self.eq(prikey.dump(fmt='pem'), prikey.dump(fmt='PEM'))
        self.nn(s_rsa.PriKey.load(prikey.dump(fmt='PEM'), fmt='Pem'))

    def test_lib_crypto_rsa_encrypt(self):

        prikey = s_rsa.PriKey.generate()
        pubkey = prikey.public()

        mesg = 'we all float down here'.encode()

        ciph = pubkey.encrypt(mesg)
        self.isinstance(ciph, bytes)
        self.ne(ciph, mesg)

        # the corresponding private key recovers the plaintext
        self.eq(mesg, prikey.decrypt(ciph))

        # a re-loaded key pair round-trips too
        newpub = s_rsa.PubKey.load(pubkey.dump())
        newpri = s_rsa.PriKey.load(prikey.dump())
        self.eq(mesg, newpri.decrypt(newpub.encrypt(mesg)))

        # a different private key cannot decrypt the ciphertext
        other = s_rsa.PriKey.generate()
        with self.raises(ValueError):
            other.decrypt(ciph)

    def test_lib_crypto_rsa_loadkey(self):

        import synapse.lib.crypto.ecc as s_ecc

        prikey = s_rsa.PriKey.generate(bits=1024)
        pubkey = prikey.public()

        # PEM/DER and public/private are auto-detected
        self.isinstance(s_rsa.loadKey(prikey.dump(fmt='pem')), s_rsa.PriKey)
        self.isinstance(s_rsa.loadKey(pubkey.dump(fmt='pem')), s_rsa.PubKey)
        self.isinstance(s_rsa.loadKey(prikey.dump(fmt='der')), s_rsa.PriKey)
        self.isinstance(s_rsa.loadKey(pubkey.dump(fmt='der')), s_rsa.PubKey)

        # a blob containing more than one key is rejected
        with self.raises(s_exc.BadArg):
            s_rsa.loadKey(prikey.dump(fmt='pem') + pubkey.dump(fmt='pem'))

        # an ECC key (public or private) is not an RSA key
        eck = s_ecc.PriKey.generate(curve='P-256')
        with self.raises(s_exc.BadArg):
            s_rsa.loadKey(eck.dump(fmt='pem'))

        with self.raises(s_exc.BadArg):
            s_rsa.loadKey(eck.public().dump(fmt='pem'))

        # garbage bytes are rejected
        with self.raises(ValueError):
            s_rsa.loadKey(b'not a key')

    def test_lib_crypto_rsa_break(self):
        pvk1 = s_rsa.PriKey.generate()
        pbk1 = pvk1.public()

        pvk2 = s_rsa.PriKey.generate()
        pbk2 = pvk2.public()

        mesg = 'We all float down here'.encode()
        sig1 = pvk1.sign(mesg)

        # Cannot cross validate messages
        self.false(pbk2.verify(mesg, sig1))

        # Tampered messages fail to validate
        self.false(pbk1.verify(mesg, sig1[:-10] + os.urandom(10)))
        self.false(pbk1.verify(mesg, os.urandom(10) + sig1[:10]))
