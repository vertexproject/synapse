import os
import asyncio
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common


import synapse.tools.pushfile as s_pushfile

import synapse.tests.utils as s_t_utils

nullhash = hashlib.sha256(b'').digest()
visihash = hashlib.sha256(b'visi').digest()

class TestPushFile(s_t_utils.SynTest):

    async def test_pushfile(self):

        async with self.getTestAxon() as axon:

            async with self.getTestCore() as core:

                coreurl = core.getLocalUrl()
                axonurl = axon.getLocalUrl()

                async with axon.getLocalProxy() as axonprox:

                    async with core.getLocalProxy() as coreprox:

                        def pushfile():

                            with self.getTestDir() as dirn:

                                nullpath = os.path.join(dirn, 'null.txt')
                                visipath = os.path.join(dirn, 'visi.txt')

                                with s_common.genfile(visipath) as fd:
                                    fd.write(b'visi')

                                self.len(1, axonprox.wants([visihash]))

                                outp = self.getTestOutp()
                                args = ['-a', axonurl,
                                        '-c', coreurl,
                                        '-t', 'foo.bar,baz.faz',
                                        visipath]

                                self.eq(0, s_pushfile.main(args, outp))
                                self.true(outp.expect('Uploaded [visi.txt] to axon'))
                                self.true(outp.expect('file: visi.txt (4) added to core'))

                                self.len(0, axonprox.wants([visihash]))
                                self.eq(b'visi', b''.join([buf for buf in axonprox.get(visihash)]))

                                outp = self.getTestOutp()
                                self.eq(0, s_pushfile.main(args, outp))
                                self.true(outp.expect('Axon already had [visi.txt]'))

                                self.len(1, coreprox.eval(f'file:bytes={s_common.ehex(visihash)}'))
                                self.len(1, coreprox.eval('file:bytes:size=4'))
                                self.len(1, coreprox.eval('#foo.bar'))
                                self.len(1, coreprox.eval('#baz.faz'))

                                # Ensure user can't push a non-existant file and that it won't exist
                                args = ['-a', axonurl, nullpath]
                                self.raises(s_exc.NoSuchFile, s_pushfile.main, args, outp=outp)

                                self.len(1, axonprox.wants([nullhash]))

                                with s_common.genfile(nullpath) as fd:
                                    fd.write(b'')

                                outp = self.getTestOutp()
                                args = ['-a', axonurl,
                                        '-c', coreurl,
                                        '-t', 'empty',
                                        nullpath]

                                self.eq(0, s_pushfile.main(args, outp))

                                self.len(0, axonprox.wants([nullhash]))
                                self.eq(b'', b''.join([buf for buf in axonprox.get(nullhash)]))
                            return 1

                        loop = asyncio.get_running_loop()
                        ret = await loop.run_in_executor(None, pushfile)
                        self.eq(1, ret)
