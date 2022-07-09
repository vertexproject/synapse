import binascii

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
