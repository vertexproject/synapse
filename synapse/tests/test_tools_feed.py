import unittest.mock as mock

import synapse.common as s_common

import synapse.lib.scope as s_scope
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
            cmdg = s_t_utils.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg):
                self.eq(await s_feed.main(argv, outp=outp), 0)
            self.true(outp.expect('teststr=haha', throw=False))
            self.true(outp.expect('pivtarg=hehe', throw=False))

    async def test_syningest_fail(self):
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
                self.eq(await s_feed.main(argv, outp=outp), 0)
                self.true(stream.wait(1))

    async def test_syningest_remote(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                # Setup user permissions
                await core.addAuthRole('creator')
                await core.addAuthRule('creator', (True, ('node:add',)))
                await core.addAuthRule('creator', (True, ('prop:set',)))
                await core.addAuthRule('creator', (True, ('tag:add',)))
                await core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getIngestDef(guid, seen)
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
                self.eq(await s_feed.main(argv, outp=outp), 0)
            self.true(outp.expect('teststr=haha', throw=False))
            self.true(outp.expect('pivtarg=hehe', throw=False))

    async def test_synsplice_remote(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.addCreatorDeleterRoles(core)
                await core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

            mesg = ('node:add', {'ndef': ('teststr', 'foo')})
            splicefp = s_common.genpath(dirn, 'splice.mpk')
            with s_common.genfile(splicefp) as fd:
                fd.write(s_msgpack.en(mesg))

            argv = ['--cortex', curl,
                    '--format', 'syn.splice',
                    '--modules', 'synapse.tests.utils.TestModule',
                    splicefp]

            outp = self.getTestOutp()
            self.eq(await s_feed.main(argv, outp=outp), 0)
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.agenlen(1, await core.eval('teststr=foo'))

    async def test_synnodes_remote(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.addCreatorDeleterRoles(core)
                await core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

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
            self.eq(await s_feed.main(argv, outp=outp), 0)
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.agenlen(20, await core.eval('testint'))
            print(outp)

    async def test_synnodes_offset(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.addCreatorDeleterRoles(core)
                await core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

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
            self.eq(await s_feed.main(argv, outp=outp), 0)
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                await self.agenlen(8, await core.eval('testint'))

            # Sad path catch
            outp = self.getTestOutp()
            argv.append(mpkfp)
            self.eq(await s_feed.main(argv, outp=outp), 1)
            self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))
