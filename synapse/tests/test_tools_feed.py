import unittest.mock as mock

import synapse.common as s_common

import synapse.lib.scope as s_scope

import synapse.tools.feed as s_feed

import synapse.tests.common as s_test

class FeedTest(s_test.SynTest):

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
            cmdg = s_test.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
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

    def test_syningest_remote(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            with dmon._getTestProxy('core', **pconf) as core:
                # Setup user permissions
                core.addAuthRole('creator')
                core.addAuthRule('creator', (True, ('node:add',)))
                core.addAuthRule('creator', (True, ('prop:set',)))
                core.addAuthRule('creator', (True, ('tag:add',)))
                core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

            guid = s_common.guid()
            seen = s_common.now()
            gestdef = self.getIngestDef(guid, seen)
            gestfp = s_common.genpath(dirn, 'gest.json')
            s_common.jssave(gestdef, gestfp)
            argv = ['--cortex', curl,
                    '--debug',
                    '--modules', 'synapse.tests.utils.TestModule',
                    gestfp]

            outp = self.getTestOutp()
            cmdg = s_test.CmdGenerator(['storm pivcomp -> *'], on_end=EOFError)
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                self.eq(s_feed.main(argv, outp=outp), 0)
            self.true(outp.expect('teststr=haha', throw=False))
            self.true(outp.expect('pivtarg=hehe', throw=False))

    def test_synsplice_remote(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            with dmon._getTestProxy('core', **pconf) as core:
                # Setup user permissions
                core.addAuthRole('creator')
                core.addAuthRule('creator', (True, ('node:add',)))
                core.addAuthRule('creator', (True, ('prop:set',)))
                core.addAuthRule('creator', (True, ('tag:add',)))
                core.addUserRole('root', 'creator')

            host, port = dmon.addr
            curl = f'tcp://root:root@{host}:{port}/core'
            dirn = s_scope.get('dirn')

            mesg = ('node:add', {'ndef': ('teststr', 'foo')})
            splicefp = s_common.genpath(dirn, 'splice.yaml')
            s_common.yamlsave(mesg, splicefp)

            argv = ['--cortex', curl,
                    '--format', 'syn.splice',
                    '--modules', 'synapse.tests.utils.TestModule',
                    splicefp]

            outp = self.getTestOutp()
            self.eq(s_feed.main(argv, outp=outp), 0)
            with dmon._getTestProxy('core', **pconf) as core:
                self.len(1, core.eval('teststr=foo'))
