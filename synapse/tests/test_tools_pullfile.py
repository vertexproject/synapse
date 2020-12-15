import os
import asyncio
import hashlib
import pathlib

import synapse.tests.utils as s_t_utils
import synapse.tools.pullfile as s_pullfile

class TestPullFile(s_t_utils.SynTest):

    async def test_pullfile(self):

        async with self.getTestAxon() as axon:

            axonurl = axon.getLocalUrl()

            testhash = hashlib.sha256(b'test').hexdigest()
            visihash = hashlib.sha256(b'visi').hexdigest()
            nonehash = hashlib.sha256(b'none').hexdigest()

            testbash = hashlib.sha256(b'test').digest()
            visibash = hashlib.sha256(b'visi').digest()

            self.eq(((4, visibash), (4, testbash)), await axon.puts([b'visi', b'test']))

            with self.getTestDir() as wdir:

                outp = self.getTestOutp()
                self.eq(0, await s_pullfile.main(['-a', axonurl,
                                            '-o', wdir,
                                            '-l', testhash,
                                            '-l', nonehash], outp))
                oldcwd = os.getcwd()
                os.chdir(wdir)
                self.eq(0, await s_pullfile.main(['-a', axonurl,
                                            '-l', visihash], outp))

                os.chdir(oldcwd)

                with open(pathlib.Path(wdir, testhash), 'rb') as fd:
                    self.eq(b'test', fd.read())

                with open(pathlib.Path(wdir, visihash), 'rb') as fd:
                    self.eq(b'visi', fd.read())

                self.true(outp.expect(f'{nonehash} not in axon store'))
                self.true(outp.expect(f'Fetching {testhash} to file'))
                self.true(outp.expect(f'Fetching {visihash} to file'))
