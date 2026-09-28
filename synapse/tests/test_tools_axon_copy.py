import synapse.exc as s_exc

import synapse.tests.utils as s_test
import synapse.tools.axon.copy as s_copy

class Axon2AxonTest(s_test.SynTest):

    async def test_axon2axon(self):

        async with self.getTestAxon() as srcaxon:

            async with self.getTestAxon() as dstaxon:

                srcurl = srcaxon.getLocalUrl()
                dsturl = dstaxon.getLocalUrl()

                (size, sha256) = await srcaxon.put(b'visi')

                outp = self.getTestOutp()
                await s_copy.main([srcurl, dsturl], outp=outp)
                self.true(await dstaxon.has(sha256))
                outp.expect('Starting transfer at offset: 0')
                outp.expect('[         0] - e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f (4)')

                (size, sha256) = await srcaxon.put(b'vertex')

                outp = self.getTestOutp()
                await s_copy.main([srcurl, dsturl, '--offset', '1'], outp=outp)
                self.true(await dstaxon.has(sha256))
                outp.expect('Starting transfer at offset: 1')
                outp.expect('[         1] - e1b683e26a3aad218df6aa63afe9cf57fdb5dfaf5eb20cddac14305d67f48a02 (6)')

                outp = self.getTestOutp()
                with self.raises(s_exc.ParserExit) as cm:
                    await s_copy.main([], outp=outp)
                self.eq(2, cm.exception.get('exitcode'))
                outp.expect('arguments are required:')

                outp = self.getTestOutp()
                with self.raises(s_exc.ParserExit) as cm:
                    await s_copy.main(['--help'], outp=outp)
                self.eq(0, cm.exception.get('exitcode'))
                outp.expect('usage: synapse.tools.axon.copy')
