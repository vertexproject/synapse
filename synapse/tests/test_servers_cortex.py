import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

class CortexServerTest(s_t_utils.SynTest):

    async def test_server(self):

        with self.getTestDir() as dirn, self.withSetLoggingMock() as mock:
            outp = self.getTestOutp()
            guid = s_common.guid()

            argv = [dirn,
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'telecore']
            async with await s_cortex.Cortex.initFromArgv(argv, outp=outp) as core:

                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    # Make a node with the cortex
                    podes = await s_t_utils.alist(proxy.eval(f'[ou:org={guid}]'))
                    self.len(1, podes)

                self.true(core.dmon.shared.get('*') is core)
                self.true(core.dmon.shared.get('cortex') is core)
                self.true(core.dmon.shared.get('telecore') is core)

            # And data persists...
            async with await s_cortex.Cortex.initFromArgv(argv, outp=outp) as core:
                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    podes = await s_t_utils.alist(proxy.eval(f'ou:org={guid}'))
                    self.len(1, podes)

            self.eq(2, mock.call_count)

    async def test_server_mirror(self):

        with self.getTestDir() as dirn, self.withSetLoggingMock():

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                outp = self.getTestOutp()
                argv = ['--telepath', 'tcp://127.0.0.1:0/',
                        '--https', '0',
                        '--mirror', core00.getLocalUrl(),
                        path01]

                # add a node for core01 to sync before window
                await core00.nodes('[ inet:ipv4=5.5.5.5 ]')

                s_common.yamlsave({'nexslog:en': True}, path01, 'cell.yaml')

                async with await s_cortex.Cortex.initFromArgv(argv, outp=outp) as core01:

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:ipv4=5.5.5.5'))

                    # add a node for core01 to sync via window
                    self.len(1, await core00.nodes('[ inet:ipv4=6.6.6.6 ]'))

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:ipv4=6.6.6.6'))

    async def test_server_mirror_restart(self):

        with self.getTestDir() as dirn, self.withSetLoggingMock():

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            conf00 = {
                'layer:lmdb:map_async': True,
                'provenance:en': True,
                'nexslog:en': True,
                'layers:logedits': True,
                'auth:passwd': 'secret',
            }

            async with await s_cortex.Cortex.anit(dirn=path00, conf=conf00) as core00:
                await core00.nodes('[ inet:asn=0 ]')

            s_tools_backup.backup(path00, path01)

            async with await s_cortex.Cortex.anit(dirn=path00, conf=conf00) as core00:

                # add a node for core01 to sync before window
                await core00.nodes('[ inet:asn=1 ]')

                outp = self.getTestOutp()
                argv = ['--telepath', 'tcp://127.0.0.1:0/',
                        '--https', '0',
                        '--auth-passwd', 'secret',
                        '--mirror', core00.getLocalUrl(),
                        path01]

                async with await s_cortex.Cortex.initFromArgv(argv, outp=outp) as core01:
                    await core01.sync()

                    self.len(1, await core01.nodes('inet:asn=0'))
                    self.len(1, await core01.nodes('inet:asn=1'))

                    # get the nexus index
                    nexusind = core01.nexsroot.nexslog.index()

                await core00.nodes('[ inet:asn=2 ]')

                async with await s_cortex.Cortex.initFromArgv(argv, outp=outp) as core01:

                    # check that startup does not create any events
                    self.eq(nexusind, core01.nexsroot.nexslog.index())

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:asn=0'))
                    self.len(1, await core01.nodes('inet:asn=1'))
                    self.len(1, await core01.nodes('inet:asn=2'))

                    await core00.nodes('[ inet:asn=3 ]')

                    await core01.sync()

                    self.len(4, await core01.nodes('inet:asn'))

    async def test_server_mirror_badiden(self):

        with self.getTestDir() as dirn, self.withSetLoggingMock():

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            argv0 = ['--telepath', 'tcp://127.0.0.1:0/',
                     '--https', '0',
                     '--name', 'srccore',
                     path00,
                     ]
            out0 = self.getTestOutp()
            async with await s_cortex.Cortex.initFromArgv(argv0, outp=out0) as core00:

                out1 = self.getTestOutp()
                argv1 = ['--telepath', 'tcp://127.0.0.1:0/',
                         '--https', '0',
                         '--mirror', core00.getLocalUrl(),
                         path01,
                         ]

                s_common.yamlsave({'nexslog:en': True}, path01, 'cell.yaml')

                with self.getAsyncLoggerStream('synapse.lib.nexus',
                                               'has different iden') as stream:
                    async with await s_cortex.Cortex.initFromArgv(argv1, outp=out1) as core01:
                        await stream.wait(timeout=2)
                        self.true(await core01.waitfini(6))
