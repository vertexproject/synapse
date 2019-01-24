import os
import asyncio
import hashlib

import synapse.common as s_common

import synapse.lib.scope as s_scope
import synapse.tests.utils as s_t_utils

import synapse.tools.pushfile as s_pushfile
import synapse.tools.pullfile as s_pullfile


class TestPullFile(s_t_utils.SynTest):

    async def test_pullfile(self):

        async with self.getTestDmonCortexAxon():

            coreurl = s_scope.get('coreurl')
            axonurl = s_scope.get('axonurl')

            def pullfile():

                with self.getTestDir() as dirn:
                    testpath = os.path.join(dirn, 'test.txt')
                    visipath = os.path.join(dirn, 'visi.txt')
                    with s_common.genfile(testpath) as fd:
                        fd.write(b'test')
                    with s_common.genfile(visipath) as fd:
                        fd.write(b'visi')

                    pushargs = ['-a', axonurl,
                                '-c', coreurl]
                    outp = self.getTestOutp()
                    self.eq(0, s_pushfile.main(pushargs + [testpath], outp=outp))
                    self.eq(0, s_pushfile.main(pushargs + [visipath], outp=outp))

                    testhash = hashlib.sha256(b'test').hexdigest()
                    visihash = hashlib.sha256(b'visi').hexdigest()
                    nonehash = hashlib.sha256(b'none').hexdigest()
                    pullargs = ['-a', axonurl,
                                '-o', dirn,
                                '-l', [testhash, visihash, nonehash]]
                    outp = self.getTestOutp()
                    self.eq(0, s_pullfile.main(pullargs, outp))
                    self.true(outp.expect(f'b\'{nonehash}\' not in axon store'))
                    self.true(outp.expect(f'Fetching {testhash} to file'))
                    self.true(outp.expect(f'Fetching {visihash} to file'))

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, pullfile)
