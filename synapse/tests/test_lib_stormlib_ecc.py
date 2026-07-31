import cryptography.hazmat.primitives.asymmetric.ec as c_ec
from cryptography.exceptions import InvalidSignature

import synapse.exc as s_exc
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.crypto.utils as s_crypto

import synapse.tests.utils as s_test

# A crypto:ecc:key primitivizes to a PEM string across a callStorm boundary, so
# tests carry the PEM forms and reload the object inside each query.
LOAD = '$key = $lib.crypto.ecc.load($prvpem)\n$pub = $lib.crypto.ecc.load($pubpem)\n'

class StormLibEccTest(s_test.SynTest):

    async def test_stormlib_ecc_object(self):

        async with self.getTestCore() as core:

            # generate() returns a private crypto:ecc:key; toprim yields a PEM key
            self.true(await core.callStorm('return($lib.crypto.ecc.generate().isPrivate)'))
            toprimpem = await core.callStorm('return($lib.crypto.ecc.generate())')
            self.true(toprimpem.startswith('-----BEGIN PRIVATE KEY-----'))

            prvpem, pubpem, prvder, pubder = await core.callStorm('''
                $key = $lib.crypto.ecc.generate()
                $pub = $key.pubkey()
                return(($key.encode(), $pub.encode(), $key.encode(fmt="der"), $pub.encode(fmt="der")))
            ''')

            opts = {'vars': {'prvpem': prvpem, 'pubpem': pubpem}}

            # encode() defaults to a PEM string, "der" returns bytes, bad fmt raises
            enc, encder = await core.callStorm(
                'return(($lib.crypto.ecc.load($prvpem).encode(), $lib.crypto.ecc.load($prvpem).encode(fmt="der")))',
                opts=opts)
            self.true(enc.startswith('-----BEGIN'))
            self.eq(encder, prvder)
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($prvpem).encode(fmt="newp"))', opts=opts)

            # pubkey() yields a public-only key; pubkey()/sign() on public raise
            self.false(await core.callStorm('return($lib.crypto.ecc.load($prvpem).pubkey().isPrivate)', opts=opts))
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($pubpem).pubkey())', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($pubpem).sign($lib.hex.decode("ab")))', opts=opts)

    async def test_stormlib_ecc_signverify(self):

        async with self.getTestCore() as core:

            for curve, hashname in (('P-256', 'sha256'), ('P-384', 'sha384'), ('P-521', 'sha512')):

                prvpem, pubpem = await core.callStorm('''
                    $key = $lib.crypto.ecc.generate(curve=$curve)
                    return(($key.encode(), $key.pubkey().encode()))
                ''', opts={'vars': {'curve': curve}})

                mesg = 'hello world'
                base = {'prvpem': prvpem, 'pubpem': pubpem, 'mesg': mesg, 'hashalgo': hashname}

                # sign / verify round-trips, and verifies on the pubkey too
                opts = {'vars': base}
                sig = await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), hashalgo=$hashalgo))', opts=opts)
                self.isinstance(sig, bytes)

                opts = {'vars': dict(base, sig=sig)}
                self.true(await core.callStorm(
                    LOAD + 'return($key.verify($mesg.encode(), $sig, hashalgo=$hashalgo))', opts=opts))
                self.true(await core.callStorm(
                    LOAD + 'return($pub.verify($mesg.encode(), $sig, hashalgo=$hashalgo))', opts=opts))

                # tampered message does not verify
                opts = {'vars': dict(base, sig=sig, mesg='hello there')}
                self.false(await core.callStorm(
                    LOAD + 'return($key.verify($mesg.encode(), $sig, hashalgo=$hashalgo))', opts=opts))

                # interop: verify our signature against cryptography directly
                pubobj = s_ecc.PubKey.load(pubpem.encode(), fmt='pem')
                chash = s_crypto.hashes[hashname]()
                pubobj.publ.verify(sig, mesg.encode(), c_ec.ECDSA(chash))
                with self.raises(InvalidSignature):
                    pubobj.publ.verify(sig, b'nope', c_ec.ECDSA(chash))

    async def test_stormlib_ecc_load(self):

        async with self.getTestCore() as core:

            prvpem, pubpem, prvder, pubder = await core.callStorm('''
                $key = $lib.crypto.ecc.generate()
                $pub = $key.pubkey()
                return(($key.encode(), $pub.encode(), $key.encode(fmt="der"), $pub.encode(fmt="der")))
            ''')

            # each encoding/kind auto-detects on load
            for key, isprivate in ((prvpem, True), (pubpem, False), (prvder, True), (pubder, False)):
                opts = {'vars': {'key': key}}
                self.eq(isprivate, await core.callStorm('return($lib.crypto.ecc.load($key).isPrivate)', opts=opts))

            # a PEM key may also be provided as bytes
            opts = {'vars': {'key': prvpem.encode()}}
            self.true(await core.callStorm('return($lib.crypto.ecc.load($key).isPrivate)', opts=opts))

            # multiple keys in one blob is rejected
            opts = {'vars': {'key': prvpem + pubpem}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($key))', opts=opts)

            # an RSA key is rejected by the ECC loader
            rsapem = await core.callStorm('return($lib.crypto.rsa.generate(bits=(1024)).encode())')
            opts = {'vars': {'key': rsapem}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($key))', opts=opts)

            # garbage input is rejected
            opts = {'vars': {'key': b'not a pem'}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($key))', opts=opts)

    async def test_stormlib_ecc_errors(self):

        async with self.getTestCore() as core:

            # unknown curve
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.generate(curve="newp"))')

            prvpem = await core.callStorm('return($lib.crypto.ecc.generate().encode())')
            opts = {'vars': {'prvpem': prvpem}}

            # non-bytes byts / signature
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($prvpem).sign((1234)))', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($prvpem).verify($m.encode(), (1234)))',
                                     opts={'vars': {'prvpem': prvpem, 'm': 'foo'}})

            # invalid hash algorithm
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.ecc.load($prvpem).sign($m.encode(), hashalgo="newp"))',
                                     opts={'vars': {'prvpem': prvpem, 'm': 'foo'}})
