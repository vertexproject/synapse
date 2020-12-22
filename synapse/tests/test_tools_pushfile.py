import os
import asyncio
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common


import synapse.tools.pushfile as s_pushfile

import synapse.tests.utils as s_t_utils

nullhash = hashlib.sha256(b'').digest()
visihash = hashlib.sha256(b'visi').digest()
foohash = hashlib.sha256(b'foo').digest()
barhash = hashlib.sha256(b'bar').digest()

class TestPushFile(s_t_utils.SynTest):

    async def test_pushfile(self):

        async with self.getTestAxon() as axon:

            async with self.getTestCore() as core:

                coreurl = core.getLocalUrl()
                axonurl = axon.getLocalUrl()

                async with axon.getLocalProxy() as axonprox:

                    async with core.getLocalProxy() as coreprox:

                        with self.getTestDir() as dirn:

                            nullpath = os.path.join(dirn, 'null.txt')
                            visipath = os.path.join(dirn, 'visi.txt')

                            with s_common.genfile(visipath) as fd:
                                fd.write(b'visi')

                            self.len(1, await axonprox.wants([visihash]))

                            outp = self.getTestOutp()
                            args = ['-a', axonurl,
                                    '-c', coreurl,
                                    '-t', 'foo.bar,baz.faz',
                                    visipath]

                            self.eq(0, await s_pushfile.main(args, outp))
                            self.true(outp.expect('Uploaded [visi.txt] to axon'))
                            self.true(outp.expect('file: visi.txt (4) added to core'))

                            self.len(0, await axonprox.wants([visihash]))
                            self.eq(b'visi', b''.join([buf async for buf in axonprox.get(visihash)]))

                            outp = self.getTestOutp()
                            self.eq(0, await s_pushfile.main(args, outp))
                            self.true(outp.expect('Axon already had [visi.txt]'))

                            self.eq(1, await coreprox.count(f'file:bytes={s_common.ehex(visihash)}'))
                            self.eq(1, await coreprox.count('file:bytes:size=4'))
                            self.eq(1, await coreprox.count('#foo.bar'))
                            self.eq(1, await coreprox.count('#baz.faz'))

                            # Ensure user can't push a non-existant file and that it won't exist
                            args = ['-a', axonurl, nullpath]

                            outp = self.getTestOutp()
                            self.eq(0, await s_pushfile.main(args, outp))
                            self.true(outp.expect(f'filepath does not contain any files: {nullpath}'))

                            self.len(1, await axonprox.wants([nullhash]))

                            with s_common.genfile(nullpath) as fd:
                                fd.write(b'')

                            outp = self.getTestOutp()
                            args = ['-a', axonurl,
                                    '-c', coreurl,
                                    '-t', 'empty',
                                    nullpath]

                            self.eq(0, await s_pushfile.main(args, outp))

                            self.len(0, await axonprox.wants([nullhash]))
                            self.eq(b'', b''.join([buf async for buf in axonprox.get(nullhash)]))

                            # Wilcard without recursive option
                            barpath = os.path.join(dirn, 'bar.txt')
                            foopath = os.path.join(dirn, 'foo', 'foo.txt')

                            with s_common.genfile(barpath) as fd:
                                fd.write(b'bar')

                            with s_common.genfile(foopath) as fd:
                                fd.write(b'foo')

                            self.len(2, await axonprox.wants([barhash, foohash]))

                            outp = self.getTestOutp()
                            args = ['-a', axonurl,
                                    '-c', coreurl,
                                    '-t', 'beef',
                                    f'{dirn}/**']

                            self.eq(0, await s_pushfile.main(args, outp))
                            self.true(outp.expect('Uploaded [bar.txt] to axon'))
                            self.true(outp.expect('file: bar.txt (3) added to core'))

                            self.len(0, await axonprox.wants([barhash]))
                            self.eq(b'bar', b''.join([buf async for buf in axonprox.get(barhash)]))

                            self.len(1, await axonprox.wants([foohash]))

                            # Wilcard with recursive option
                            self.len(1, await axonprox.wants([barhash, foohash]))

                            outp = self.getTestOutp()
                            args = ['-a', axonurl,
                                    '-c', coreurl,
                                    '-t', 'beef',
                                    '-r',
                                    f'{dirn}/**']

                            self.eq(0, await s_pushfile.main(args, outp))
                            self.true(outp.expect('Uploaded [foo.txt] to axon'))
                            self.true(outp.expect('file: foo.txt (3) added to core'))

                            self.len(0, await axonprox.wants([barhash]))
                            self.eq(b'bar', b''.join([buf async for buf in axonprox.get(barhash)]))

                            self.len(0, await axonprox.wants([foohash]))
