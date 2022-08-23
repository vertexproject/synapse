import synapse.tests.utils as s_test
import synapse.tools.axon2axon as s_axon2axon

class Axon2AxonTest(s_test.SynTest):

    async def test_axon2axon(self):

        async with self.getTestAxon() as srcaxon:

            async with self.getTestAxon() as dstaxon:

                srcurl = srcaxon.getLocalUrl()
                dsturl = dstaxon.getLocalUrl()

                (size, sha256) = await srcaxon.put(b'visi')

                outp = self.getTestOutp()
                await s_axon2axon.main([srcurl, dsturl], outp=outp)
                self.true(await dstaxon.has(sha256))
                outp.expect('Starting transfer at offset: 0')
                outp.expect('[         0] - e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f (4)')

                (size, sha256) = await srcaxon.put(b'vertex')

                outp = self.getTestOutp()
                await s_axon2axon.main([srcurl, dsturl, '--offset', '1'], outp=outp)
                self.true(await dstaxon.has(sha256))
                outp.expect('Starting transfer at offset: 1')
                outp.expect('[         1] - e1b683e26a3aad218df6aa63afe9cf57fdb5dfaf5eb20cddac14305d67f48a02 (6)')

                outp = self.getTestOutp()
                self.eq(1, await s_axon2axon.main([], outp=outp))
                outp.expect('arguments are required:')
