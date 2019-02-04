import os
import asyncio
import hashlib
import pathlib

import synapse.common as s_common

import synapse.lib.scope as s_scope
import synapse.tests.utils as s_t_utils

import synapse.telepath as s_telepath
import synapse.tools.pullfile as s_pullfile


class TestPullFile(s_t_utils.SynTest):

    async def test_pullfile(self):

        async with self.getTestDmonCortexAxon():

            axonurl = s_scope.get('axonurl')
            async with await s_telepath.openurl(s_scope.get('blobstorurl')) as blob:
                await blob.putmany([b'visi', b'test'])

                def pullfile():

                    testhash = hashlib.sha256(b'test').hexdigest()
                    visihash = hashlib.sha256(b'visi').hexdigest()
                    nonehash = hashlib.sha256(b'none').hexdigest()

                    with self.getTestDir() as wdir:
                        outp = self.getTestOutp()
                        self.eq(0, s_pullfile.main(['-a', axonurl,
                                                    '-o', wdir,
                                                    '-l', testhash,
                                                    '-l', nonehash], outp))
                        oldcwd = os.getcwd()
                        os.chdir(wdir)
                        self.eq(0, s_pullfile.main(['-a', axonurl,
                                                    '-l', visihash], outp))
                        os.chdir(oldcwd)
                        with open(pathlib.Path(wdir, testhash), 'rb') as fd:
                            self.eq(b'test', fd.read())
                        with open(pathlib.Path(wdir, visihash), 'rb') as fd:
                            self.eq(b'visi', fd.read())

                        self.true(outp.expect(f'b\'{nonehash}\' not in axon store'))
                        self.true(outp.expect(f'Fetching {testhash} to file'))
                        self.true(outp.expect(f'Fetching {visihash} to file'))

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, pullfile)
