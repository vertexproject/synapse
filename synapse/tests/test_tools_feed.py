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
            cmdg = s_t_utils.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg):
                self.eq(s_feed.main(argv, outp=outp), 0)
            self.true(outp.expect('teststr=haha', throw=False))
            self.true(outp.expect('pivtarg=hehe', throw=False))

    def test_syningest_fail(self):
        with self.getTestDir() as dirn:
            gestdef = {'forms': {'teststr': ['yes', ],
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

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            def testmain():

                pconf = {'user': 'root', 'passwd': 'root'}
                with self.getTestProxy(dmon, 'core', **pconf) as core:
                    # Setup user permissions
                    core.addAuthRole('creator')
                    core.addAuthRule('creator', (True, ('node:add',)))
                    core.addAuthRule('creator', (True, ('prop:set',)))
                    core.addAuthRule('creator', (True, ('tag:add',)))
                    core.addUserRole('root', 'creator')

                host, port = dmon.addr
                curl = f'tcp://root:root@{host}:{port}/core'

                guid = s_common.guid()
                seen = s_common.now()
                gestdef = self.getIngestDef(guid, seen)

                with self.getTestDir() as dirn:

                    # Test yaml support here
                    gestfp = s_common.genpath(dirn, 'gest.yaml')
                    s_common.yamlsave(gestdef, gestfp)
                    argv = ['--cortex', curl,
                            '--debug',
                            '--modules', 'synapse.tests.utils.TestModule',
                            gestfp]

                    outp = self.getTestOutp()
                    cmdg = s_t_utils.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
                    with mock.patch('synapse.lib.cli.get_input', cmdg):
                        self.eq(s_feed.main(argv, outp=outp), 0)
                    self.true(outp.expect('teststr=haha', throw=False))
                    self.true(outp.expect('pivtarg=hehe', throw=False))

            await s_coro.executor(testmain)

    async def test_synsplice_remote(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            host, port = dmon.addr
            curl = f'tcp://pennywise:cottoncandy@{host}:{port}/core'

            async with await self.getTestProxy(dmon, 'core', user='root', passwd='root') as core:

                await self.addCreatorDeleterRoles(core)
                await core.addAuthUser('pennywise')
                await core.setUserPasswd('pennywise', 'cottoncandy')
                await core.addUserRole('pennywise', 'creator')

            def testmain():

                mesg = ('node:add', {'ndef': ('teststr', 'foo')})
                splicefp = s_common.genpath(dmon.dirn, 'splice.mpk')
                with s_common.genfile(splicefp) as fd:
                    fd.write(s_msgpack.en(mesg))

                argv = ['--cortex', curl,
                        '--format', 'syn.splice',
                        '--modules', 'synapse.tests.utils.TestModule',
                        splicefp]

                outp = self.getTestOutp()
                self.eq(s_feed.main(argv, outp=outp), 0)
                with self.getTestProxy(dmon, 'core', user='pennywise', passwd='cottoncandy') as core:
                    self.len(1, list(core.eval('teststr=foo')))
                return True

            ret = await s_coro.executor(testmain)
            self.true(ret)

    async def test_synnodes_remote(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            host, port = dmon.addr

            pconf = {'user': 'root', 'passwd': 'root'}

            curl = f'tcp://root:root@{host}:{port}/core'

            async with await s_telepath.openurl(curl) as core:

                await self.addCreatorDeleterRoles(core)
                await core.addUserRole('root', 'creator')

                with self.getTestDir() as dirn:

                    def testmain():

                        mpkfp = s_common.genpath(dirn, 'podes.mpk')
                        with s_common.genfile(mpkfp) as fd:
                            for i in range(20):
                                pode = (('testint', i), {})
                                fd.write(s_msgpack.en(pode))

                        argv = ['--cortex', curl,
                                '--format', 'syn.nodes',
                                '--modules', 'synapse.tests.utils.TestModule',
                                '--chunksize', '3',
                                mpkfp]

                        outp = self.getTestOutp()
                        self.eq(s_feed.main(argv, outp=outp), 0)
                        with self.getTestProxy(dmon, 'core', **pconf) as core:
                            self.len(20, list(core.eval('testint')))

                    await s_coro.executor(testmain)

    async def test_synnodes_offset(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            def testmain():

                pconf = {'user': 'root', 'passwd': 'root'}
                with self.getTestProxy(dmon, 'core', **pconf) as core:
                    s_glob.sync(self.addCreatorDeleterRoles(core))
                    core.addUserRole('root', 'creator')

                host, port = dmon.addr
                curl = f'tcp://root:root@{host}:{port}/core'

                with self.getTestDir() as dirn:

                    mpkfp = s_common.genpath(dirn, 'podes.mpk')
                    with s_common.genfile(mpkfp) as fd:
                        for i in range(20):
                            pode = (('testint', i), {})
                            fd.write(s_msgpack.en(pode))

                    argv = ['--cortex', curl,
                            '--format', 'syn.nodes',
                            '--modules', 'synapse.tests.utils.TestModule',
                            '--chunksize', '4',
                            '--offset', '15',
                            mpkfp]

                    outp = self.getTestOutp()
                    self.eq(s_feed.main(argv, outp=outp), 0)
                    with self.getTestProxy(dmon, 'core', **pconf) as core:
                        self.len(8, list(core.eval('testint')))

                    # Sad path catch
                    outp = self.getTestOutp()
                    argv.append(mpkfp)
                    self.eq(s_feed.main(argv, outp=outp), 1)
                    self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))

            await s_coro.executor(testmain)
