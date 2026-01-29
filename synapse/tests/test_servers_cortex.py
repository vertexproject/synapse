import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.tests.utils as s_t_utils

class CortexServerTest(s_t_utils.SynTest):

    async def test_server(self):
        with self.getTestDir() as dirn:
            async with self.withSetLoggingMock() as mock:
                guid = s_common.guid()

                argv = [dirn,
                        '--telepath', 'tcp://127.0.0.1:0/',
                        '--https', '0',
                        '--name', 'telecore']
                async with await s_cortex.Cortex.initFromArgv(argv) as core:

                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        # Make a node with the cortex
                        self.eq(1, await proxy.count(f'[ou:org={guid}]'))

                    self.true(core.dmon.shared.get('*') is core)
                    self.true(core.dmon.shared.get('cortex') is core)
                    self.true(core.dmon.shared.get('telecore') is core)

                # And data persists...
                async with await s_cortex.Cortex.initFromArgv(argv) as core:
                    async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                        self.eq(1, await proxy.count(f'ou:org={guid}'))

                self.eq(2, mock.call_count)
