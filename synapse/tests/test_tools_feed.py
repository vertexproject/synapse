import json

import synapse.common as s_common

import synapse.lib.msgpack as s_msgpack

import synapse.tools.feed as s_feed

import synapse.tests.utils as s_t_utils

class FeedTest(s_t_utils.SynTest):

    async def test_syningest_local(self):

        with self.getTestDir() as dirn:

            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getIngestDef(guid, seen)
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--test', '--debug',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            cmdg = s_t_utils.CmdGenerator(['storm test:pivcomp -> *', EOFError()])
            with self.withCliPromptMockExtendOutp(outp):
                with self.withTestCmdr(cmdg):
                    self.eq(await s_feed.main(argv, outp=outp), 0)

            self.true(outp.expect('test:str=haha', throw=False))
            self.true(outp.expect('test:pivtarg=hehe', throw=False))

    async def test_syningest_fail(self):
        with self.getTestDir() as dirn:
            gestdef = {'forms': {'test:str': ['yes', ],
                                 'newp': ['haha', ],
                                 }
                       }
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--test',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            with self.getLoggerStream('synapse.lib.snap', 'NoSuchForm') as stream:
                self.eq(await s_feed.main(argv, outp=outp), 0)
                self.true(stream.wait(1))

    async def test_syningest_remote(self):

        async with self.getTestCore() as core:

            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getIngestDef(guid, seen)

            with self.getTestDir() as dirn:

                # Test yaml support here
                gestfp = s_common.genpath(dirn, 'gest.yaml')
                s_common.yamlsave(gestdef, gestfp)
                argv = ['--cortex', core.getLocalUrl(),
                        '--debug',
                        '--modules', 'synapse.tests.utils.TestModule',
                        gestfp]

                outp = self.getTestOutp()
                cmdg = s_t_utils.CmdGenerator(['storm test:pivcomp -> *', EOFError()])
                with self.withCliPromptMockExtendOutp(outp):
                    with self.withTestCmdr(cmdg):
                        self.eq(await s_feed.main(argv, outp=outp), 0)
                self.true(outp.expect('test:str=haha', throw=False))
                self.true(outp.expect('test:pivtarg=hehe', throw=False))

    async def test_synsplice_remote(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            mesg = ('node:add', {'ndef': ('test:str', 'foo')})
            splicefp = s_common.genpath(core.dirn, 'splice.mpk')
            with s_common.genfile(splicefp) as fd:
                fd.write(s_msgpack.en(mesg))

            argv = ['--cortex', curl,
                    '--format', 'syn.splice',
                    '--modules', 'synapse.tests.utils.TestModule',
                    splicefp]

            outp = self.getTestOutp()
            self.eq(await s_feed.main(argv, outp=outp), 0)

            nodes = await core.eval('test:str=foo').list()
            self.len(1, nodes)

    async def test_synnodes_remote(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                jsonlfp = s_common.genpath(dirn, 'podes.jsonl')
                with s_common.genfile(jsonlfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        _ = fd.write(json.dumps(pode).encode() + b'\n')

                argv = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule',
                        '--chunksize', '3',
                        jsonlfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

            nodes = await core.eval('test:int').list()
            self.len(20, nodes)

    async def test_synnodes_offset(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'podes.mpk')
                with s_common.genfile(mpkfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        fd.write(s_msgpack.en(pode))

                argv = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule',
                        '--chunksize', '4',
                        '--offset', '15',
                        mpkfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

                # Sad path catch
                outp = self.getTestOutp()
                argv.append(mpkfp)
                self.eq(await s_feed.main(argv, outp=outp), 1)
                self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))

            nodes = await core.eval('test:int').list()
            self.len(8, nodes)
