import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.servers.cell as s_s_univ

import synapse.tests.utils as s_t_utils

class UnivServerTest(s_t_utils.SynTest):

    async def test_server(self):
        with self.getTestDir() as dirn:
            async with self.withSetLoggingMock() as mock:

                guid = s_common.guid()

                argv = [
                    'synapse.cortex.Cortex',
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'univtest',
                    dirn,
                ]

                # Start a cortex with the universal loader
                async with await s_s_univ.main(argv) as core:

                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        self.eq(1, await proxy.count(f'[ou:org={guid}]'))
                        self.eq('cortex', await proxy.getCellType())

                    self.true(core.dmon.shared.get('univtest') is core)

                # And data persists... and can be seen with the regular synapse cortex server
                argv = [
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'univtest',
                    dirn,
                ]
                async with await s_cortex.Cortex.initFromArgv(argv) as core:
                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        self.eq(1, await proxy.count(f'ou:org={guid}'))

                argv = [
                    'synapse.lib.cell.Cell',
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'univtest',
                    dirn,
                ]

                # Start a cortex as a regular Cell
                async with await s_s_univ.main(argv) as cell:
                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        self.eq('cell', await proxy.getCellType())

                argv = [
                    'synapse.tests.test_lib_cell.EchoAuth',
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'univtest',
                    dirn,
                ]
                # Or start the Cortex off a a EchoAuth (don't do this in practice...)
                async with await s_s_univ.main(argv) as cell:
                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        self.eq('echoauth', await proxy.getCellType())

                argv = ['synapse.lib.newp.Newp']
                with self.raises(s_exc.NoSuchCtor):
                    async with await s_s_univ.main(argv) as core:
                        pass

                argv = ['synapse.lib.cell.Cell', dirn,
                        '--telepath', 'tcp://127.0.0.1:9999999/',
                        '--https', '0',
                        '--name', 'telecore']
                # Coverage test, for a bad configuration
                with self.raises(OverflowError):
                    await s_s_univ.main(argv)
