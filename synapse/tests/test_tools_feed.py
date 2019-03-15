import unittest.mock as mock

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.msgpack as s_msgpack

import synapse.tools.feed as s_feed

import synapse.tests.utils as s_t_utils

class FeedTest(s_t_utils.SynTest):

    def test_syningest_local(self):

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
            cmdg = s_t_utils.CmdGenerator(['storm test:pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg):
                self.eq(s_feed.main(argv, outp=outp), 0)
            self.true(outp.expect('test:str=haha', throw=False))
            self.true(outp.expect('test:pivtarg=hehe', throw=False))

    def test_syningest_fail(self):
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
                self.eq(s_feed.main(argv, outp=outp), 0)
                self.true(stream.wait(1))

    async def test_syningest_remote(self):

        async with self.getTestCore() as core:

            def testmain():

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
                    cmdg = s_t_utils.CmdGenerator(['storm test:pivcomp -> *'], on_end=EOFError)
                    with mock.patch('synapse.lib.cli.get_input', cmdg):
                        self.eq(s_feed.main(argv, outp=outp), 0)
                    self.true(outp.expect('test:str=haha', throw=False))
                    self.true(outp.expect('test:pivtarg=hehe', throw=False))

            await s_coro.executor(testmain)

    async def test_synsplice_remote(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            def testmain():

                mesg = ('node:add', {'ndef': ('test:str', 'foo')})
                splicefp = s_common.genpath(core.dirn, 'splice.mpk')
                with s_common.genfile(splicefp) as fd:
                    fd.write(s_msgpack.en(mesg))

                argv = ['--cortex', curl,
                        '--format', 'syn.splice',
                        '--modules', 'synapse.tests.utils.TestModule',
                        splicefp]

                outp = self.getTestOutp()
                self.eq(s_feed.main(argv, outp=outp), 0)
                return True

            await s_coro.executor(testmain)
            nodes = await core.eval('test:str=foo').list()
            self.len(1, nodes)

    async def test_synnodes_remote(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                def testmain():

                    mpkfp = s_common.genpath(dirn, 'podes.mpk')
                    with s_common.genfile(mpkfp) as fd:
                        for i in range(20):
                            pode = (('test:int', i), {})
                            fd.write(s_msgpack.en(pode))

                    argv = ['--cortex', curl,
                            '--format', 'syn.nodes',
                            '--modules', 'synapse.tests.utils.TestModule',
                            '--chunksize', '3',
                            mpkfp]

                    outp = self.getTestOutp()
                    self.eq(s_feed.main(argv, outp=outp), 0)

                await s_coro.executor(testmain)

            nodes = await core.eval('test:int').list()
            self.len(20, nodes)

    async def test_synnodes_offset(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            def testmain():

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
                    self.eq(s_feed.main(argv, outp=outp), 0)

                    # Sad path catch
                    outp = self.getTestOutp()
                    argv.append(mpkfp)
                    self.eq(s_feed.main(argv, outp=outp), 1)
                    self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))

            await s_coro.executor(testmain)
            nodes = await core.eval('test:int').list()
            self.len(8, nodes)
