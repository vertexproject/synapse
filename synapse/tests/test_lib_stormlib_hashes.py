import binascii

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
            return ( $lib.crypto.hmac.sign(key=$key, mesg=$mesg, digest=$mode) )
            '''

            # RFC 2104 test vector
            key = "Jefe"
            data = "what do ya want for nothing?"
            mode = 'md5'
            digest = '750c783e6ab0b503eaa86e310a5db738'

            opts = {'vars': {'key': key, 'mesg': data, 'mode': mode}}
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, s_common.uhex(digest))

            # rfc4231 vectors

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
            $kDate = $lib.crypto.hmac.sign(key=$seed.encode(), mesg=$date.encode())
            $kRegion = $lib.crypto.hmac.sign(key=$kDate, mesg=$region.encode())
            $kService = $lib.crypto.hmac.sign(key=$kRegion, mesg=$service.encode())
            $kSigning = $lib.crypto.hmac.sign(key=$kService, mesg=$const.encode())
            return ( $kSigning )
            '''
            ret = await core.callStorm(q)
            print('---------------------------')
            self.eq(ret, s_common.uhex(digest))

            q = """
            $signingKey=c4afb1cc5771d871763a393e44b703571b55cc28424d1a5e86da6ed3c154a4b9
            $signingKey=$lib.hex.decode($signingKey)
            $stringToSign='''AWS4-HMAC-SHA256
20150830T123600Z
20150830/us-east-1/iam/aws4_request
f536975d06c0309214f805bb90ccff089219ecd68b2577efef23edd43b7e1a59'''
            return ( $lib.crypto.hmac.sign($signingKey, $stringToSign.encode()) )
            """
            digest = '5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7'
            ret = await core.callStorm(q)
            self.eq(ret, s_common.uhex(digest))
