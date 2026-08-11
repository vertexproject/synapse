import base64

import cryptography.hazmat.primitives.hashes as c_hashes
import cryptography.hazmat.primitives.asymmetric.padding as c_padding

import synapse.exc as s_exc
import synapse.lib.crypto.rsa as s_rsa

import synapse.tests.utils as s_test

# A crypto:rsa:key primitivizes to a PEM string when it crosses a callStorm
# boundary, so tests carry the PEM forms and reload the object with
# $lib.crypto.rsa.load(...) inside each query.
LOAD = '$key = $lib.crypto.rsa.load($prvpem)\n$pub = $lib.crypto.rsa.load($pubpem)\n'

class StormLibRsaTest(s_test.SynTest):

    async def _genKeyForms(self, core):
        return await core.callStorm('''
            $key = $lib.crypto.rsa.generate()
            $pub = $key.pubkey()
            return((
                $key.encode(), $pub.encode(),
                $key.encode(fmt="der"), $pub.encode(fmt="der"),
            ))
        ''')

    async def test_stormlib_rsa_object(self):

        async with self.getTestCore() as core:

            prvpem, pubpem, prvder, pubder = await self._genKeyForms(core)

            # generate() returns a private crypto:rsa:key; toprim yields a PEM private key
            self.isinstance(prvpem, str)
            self.true(prvpem.startswith('-----BEGIN PRIVATE KEY-----'))
            self.true(await core.callStorm('return($lib.crypto.rsa.generate().isPrivate)'))

            # toprim (applied at the callStorm return boundary) yields the PEM private key
            toprimpem = await core.callStorm('return($lib.crypto.rsa.generate())')
            self.true(toprimpem.startswith('-----BEGIN PRIVATE KEY-----'))

            opts = {'vars': {'prvpem': prvpem, 'pubpem': pubpem}}

            # encode() defaults to a PEM string, "pem" matches, and "der" returns bytes
            enc, encpem, encder = await core.callStorm(
                'return(($lib.crypto.rsa.load($prvpem).encode(), '
                '$lib.crypto.rsa.load($prvpem).encode(fmt="pem"), '
                '$lib.crypto.rsa.load($prvpem).encode(fmt="der")))', opts=opts)
            self.isinstance(enc, str)
            self.true(enc.startswith('-----BEGIN'))
            self.eq(enc, encpem)
            self.eq(encder, prvder)

            # encode() with a bad format raises BadArg
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($prvpem).encode(fmt="newp"))', opts=opts)

            # isPrivate reflects public vs private
            self.true(await core.callStorm('return($lib.crypto.rsa.load($prvpem).isPrivate)', opts=opts))
            self.false(await core.callStorm('return($lib.crypto.rsa.load($pubpem).isPrivate)', opts=opts))

            # pubkey() returns a public-only key
            self.false(await core.callStorm('return($lib.crypto.rsa.load($prvpem).pubkey().isPrivate)', opts=opts))
            self.true(await core.callStorm(
                'return($lib.crypto.rsa.load($prvpem).pubkey().encode().startswith("-----BEGIN PUBLIC KEY-----"))',
                opts=opts))

            # pubkey() on a public-only key raises BadArg
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($pubpem).pubkey())', opts=opts)

            # sign() with a public-only key raises BadArg
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($pubpem).sign($lib.hex.decode("ab")))', opts=opts)

    async def test_stormlib_rsa_signverify(self):

        async with self.getTestCore() as core:

            prvpem, pubpem, _, _ = await self._genKeyForms(core)
            mesg = 'hello world'
            base = {'prvpem': prvpem, 'pubpem': pubpem, 'mesg': mesg}

            # pkcs1v15 sign/verify round-trips, is deterministic, and verifies on the pubkey too
            opts = {'vars': dict(base, pad='pkcs1v15')}
            sig = await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), padding=$pad))', opts=opts)
            self.isinstance(sig, bytes)
            self.eq(sig, await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), padding=$pad))', opts=opts))

            opts = {'vars': dict(base, sig=sig, pad='pkcs1v15')}
            self.true(await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig, padding=$pad))', opts=opts))
            self.true(await core.callStorm(LOAD + 'return($pub.verify($mesg.encode(), $sig, padding=$pad))', opts=opts))

            # a tampered message does not verify
            opts = {'vars': dict(base, sig=sig, mesg='hello there', pad='pkcs1v15')}
            self.false(await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig, padding=$pad))', opts=opts))

            # pss is the default padding and is probabilistic, but both verify
            opts = {'vars': base}
            psig1 = await core.callStorm(LOAD + 'return($key.sign($mesg.encode()))', opts=opts)
            psig2 = await core.callStorm(LOAD + 'return($key.sign($mesg.encode()))', opts=opts)
            self.ne(psig1, psig2)

            for sigv in (psig1, psig2):
                opts = {'vars': dict(base, sig=sigv)}
                self.true(await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig))', opts=opts))

            # padding schemes do not cross-validate
            opts = {'vars': dict(base, sig=psig1, pad='pkcs1v15')}
            self.false(await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig, padding=$pad))', opts=opts))

            opts = {'vars': dict(base, sig=sig)}
            self.false(await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig))', opts=opts))

            # each supported hash algorithm round-trips under both paddings
            for pad in ('pkcs1v15', 'pss'):
                for hashalgo in ('sha256', 'sha384', 'sha512'):
                    opts = {'vars': dict(base, pad=pad, hashalgo=hashalgo)}
                    asig = await core.callStorm(
                        LOAD + 'return($key.sign($mesg.encode(), padding=$pad, hashalgo=$hashalgo))', opts=opts)
                    opts = {'vars': dict(base, sig=asig, pad=pad, hashalgo=hashalgo)}
                    self.true(await core.callStorm(
                        LOAD + 'return($pub.verify($mesg.encode(), $sig, padding=$pad, hashalgo=$hashalgo))', opts=opts))

            # a signature made with one hash does not verify under another
            opts = {'vars': dict(base, hashalgo='sha384')}
            sig384 = await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), hashalgo=$hashalgo))', opts=opts)
            opts = {'vars': dict(base, sig=sig384, hashalgo='sha512')}
            self.false(await core.callStorm(
                LOAD + 'return($key.verify($mesg.encode(), $sig, hashalgo=$hashalgo))', opts=opts))

            # padding and hash names are case insensitive
            opts = {'vars': base}
            usig = await core.callStorm(
                LOAD + 'return($key.sign($mesg.encode(), padding="PSS", hashalgo="SHA256"))', opts=opts)
            opts = {'vars': dict(base, sig=usig)}
            self.true(await core.callStorm(
                LOAD + 'return($key.verify($mesg.encode(), $sig, padding="PSS", hashalgo="SHA256"))', opts=opts))

            # cross-check both schemes against cryptography directly
            pubobj = s_rsa.PubKey.load(pubpem.encode(), fmt='pem')
            self.none(pubobj.publ.verify(sig, mesg.encode(), c_padding.PKCS1v15(), c_hashes.SHA256()))
            cpad = c_padding.PSS(c_padding.MGF1(c_hashes.SHA256()), c_padding.PSS.MAX_LENGTH)
            self.none(pubobj.publ.verify(psig1, mesg.encode(), cpad, c_hashes.SHA256()))

            # BadArg on non-bytes byts / signature, bad padding, bad hashalgo
            opts = {'vars': base}
            with self.raises(s_exc.BadArg):
                await core.callStorm(LOAD + 'return($key.sign((1234)))', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), padding="newp"))', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm(LOAD + 'return($key.sign($mesg.encode(), hashalgo="newp"))', opts=opts)

            opts = {'vars': dict(base, sig=sig)}
            with self.raises(s_exc.BadArg):
                await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), (1234)))', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm(LOAD + 'return($key.verify($mesg.encode(), $sig, padding="newp"))', opts=opts)

    async def test_stormlib_rsa_load(self):

        async with self.getTestCore() as core:

            prvpem, pubpem, prvder, pubder = await self._genKeyForms(core)

            # each encoding/kind auto-detects on load
            for key, isprivate in ((prvpem, True), (pubpem, False), (prvder, True), (pubder, False)):
                opts = {'vars': {'key': key}}
                self.eq(isprivate, await core.callStorm('return($lib.crypto.rsa.load($key).isPrivate)', opts=opts))

            # a PEM key may also be provided as bytes
            opts = {'vars': {'key': prvpem.encode()}}
            self.true(await core.callStorm('return($lib.crypto.rsa.load($key).isPrivate)', opts=opts))

            # a blob containing multiple keys is rejected
            opts = {'vars': {'key': prvpem + pubpem}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($key))', opts=opts)

            # an ECC key is rejected by the RSA loader
            eccpem = await core.callStorm('return($lib.crypto.ecc.generate().encode())')
            opts = {'vars': {'key': eccpem}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($key))', opts=opts)

            # garbage and unsupported key-argument types are rejected
            opts = {'vars': {'key': b'not a real key'}}
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load($key))', opts=opts)

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.crypto.rsa.load((1234)))')

    async def test_stormlib_rsa_generate(self):

        async with self.getTestCore() as core:

            # the lower bound on bits is accepted
            self.true(await core.callStorm('return($lib.crypto.rsa.generate(bits=(1024)).isPrivate)'))

            # sizes outside 1024-8192 are rejected with BadArg
            for bits in (8, 512, 1023, 8193, 16384):
                with self.raises(s_exc.BadArg):
                    await core.callStorm('return($lib.crypto.rsa.generate(bits=$bits))',
                                         opts={'vars': {'bits': bits}})

    async def test_stormlib_rsa_jwt(self):

        async with self.getTestCore() as core:

            prvpem, pubpem, _, _ = await self._genKeyForms(core)

            # build an RS256 JWT purely from a crypto:rsa:key object
            header = '{"alg":"RS256","typ":"JWT"}'
            payload = '{"sub":"1234567890","name":"vtx"}'

            q = '''
            $key = $lib.crypto.rsa.load($prvpem)
            $h64 = $lib.base64.encode($header.encode(), urlsafe=(true)).rstrip("=")
            $p64 = $lib.base64.encode($payload.encode(), urlsafe=(true)).rstrip("=")
            $signin = `{$h64}.{$p64}`
            $sig = $key.sign($signin.encode(), padding="pkcs1v15")
            $s64 = $lib.base64.encode($sig, urlsafe=(true)).rstrip("=")
            return(`{$signin}.{$s64}`)
            '''
            opts = {'vars': {'prvpem': prvpem, 'header': header, 'payload': payload}}
            token = await core.callStorm(q, opts=opts)

            parts = token.split('.')
            self.len(3, parts)

            # the signing input round-trips through verify on the public key
            signin = f'{parts[0]}.{parts[1]}'
            s64 = parts[2]
            sigbytes = base64.urlsafe_b64decode(s64 + '=' * (-len(s64) % 4))

            opts = {'vars': {'pubpem': pubpem, 'signin': signin, 'sig': sigbytes}}
            self.true(await core.callStorm(
                'return($lib.crypto.rsa.load($pubpem).verify($signin.encode(), $sig, padding="pkcs1v15"))', opts=opts))
