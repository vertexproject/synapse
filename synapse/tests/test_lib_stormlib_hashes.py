import base64
import binascii

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.hashset as s_hashset

import synapse.tests.utils as s_test

class CryptoHashesTest(s_test.SynTest):

    async def test_stormlib_crypto_hashes(self):

        async with self.getTestCore() as core:
            for valu in ("", "hehe", "foobar", "foo.bar.baz.biz.com"):
                opts = {'vars': {'str': valu}}
                hashes = {
                    'md5': await core.callStorm('return($lib.crypto.hashes.md5($str.encode()))', opts=opts),
                    'sha1': await core.callStorm('return($lib.crypto.hashes.sha1($str.encode()))', opts=opts),
                    'sha256': await core.callStorm('return($lib.crypto.hashes.sha256($str.encode()))', opts=opts),
                    'sha512': await core.callStorm('return($lib.crypto.hashes.sha512($str.encode()))', opts=opts)
                }
                hashset = s_hashset.HashSet()
                hashset.update(valu.encode())
                digests = {k: binascii.hexlify(v).decode() for k, v in hashset.digests()}

                self.eq(hashes, digests)

    async def test_stormlib_crypto_hmac(self):

        async with self.getTestCore() as core:

            q = '''$key=$key.encode() $mesg=$mesg.encode()
            return ( $lib.crypto.hmac.digest(key=$key, mesg=$mesg, alg=$mode) )
            '''

            # RFC 2104 test vector
            key = "Jefe"
            data = "what do ya want for nothing?"
            mode = 'md5'
            digest = '750c783e6ab0b503eaa86e310a5db738'

            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            # some rfc4231 vectors
            mode = 'sha224'
            digest = 'a30e01098bc6dbbf45690f3a7e9e6d0f8bbea2a39e6148008fd05e44'
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            mode = 'sha256'
            digest = '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            mode = 'sha384'
            digest = 'af45d2e376484031617f78d2b58a6b1b9c7ef464f5a01b47e42ec3736322445e8' \
                     'e2240ca5e69e2c78b3239ecfab21649'
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            mode = 'sha512'
            digest = '164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549' \
                     '758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737'
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            # A few sad paths
            # bad mode
            mode = 'newp'
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            with self.raises(s_exc.BadArg):
                await core.callStorm(q, opts=opts)

            # bad key and data
            opts = {'vars': {'mesg': data}}
            bq = 'return( $lib.crypto.hmac.digest(key=1234, mesg=$mesg.encode()) )'
            with self.raises(s_exc.BadArg):
                await core.callStorm(bq, opts=opts)

            opts = {'vars': {'key': key}}
            bq = 'return( $lib.crypto.hmac.digest(key=$key.encode(), mesg=1234) )'
            with self.raises(s_exc.BadArg):
                await core.callStorm(bq, opts=opts)

            # rfc4231 - part of test case 3
            key = base64.b64encode(b'\xaa' * 20)
            data = base64.b64encode(b'\xdd' * 50)
            mode = 'sha256'
            digest = '773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe'
            b64q = '''
            $key=$lib.base64.decode($key) $mesg=$lib.base64.decode($mesg)
            return ( $lib.crypto.hmac.digest(key=$key, mesg=$mesg, alg=$mode) )
            '''
            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(b64q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            # Test vector for aws sig4 / signing key derivation
            # https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
            digest = 'c4afb1cc5771d871763a393e44b703571b55cc28424d1a5e86da6ed3c154a4b9'
            q = '''
            $date = 20150830
            $region = us-east-1
            $service = iam
            $const = aws4_request
            $kSecret = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
            $seed = `AWS4{$kSecret}`
            $kDate = $lib.crypto.hmac.digest(key=$seed.encode(), mesg=$date.encode())
            $kRegion = $lib.crypto.hmac.digest(key=$kDate, mesg=$region.encode())
            $kService = $lib.crypto.hmac.digest(key=$kRegion, mesg=$service.encode())
            $kSigning = $lib.crypto.hmac.digest(key=$kService, mesg=$const.encode())
            return ( $kSigning )
            '''
            ret = await core.callStorm(q)
            self.eq(ret, s_common.uhex(digest))

            q = """
            $signingKey=c4afb1cc5771d871763a393e44b703571b55cc28424d1a5e86da6ed3c154a4b9
            $signingKey=$lib.hex.decode($signingKey)
            $stringToSign='''AWS4-HMAC-SHA256
20150830T123600Z
20150830/us-east-1/iam/aws4_request
f536975d06c0309214f805bb90ccff089219ecd68b2577efef23edd43b7e1a59'''
            return ( $lib.crypto.hmac.digest($signingKey, $stringToSign.encode()) )
            """
            digest = '5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7'
            ret = await core.callStorm(q)
            self.eq(ret, s_common.uhex(digest))
