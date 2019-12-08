import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.servers.cell as s_s_univ
import synapse.servers.cortex as s_s_cortex
import synapse.servers.cryotank as s_s_cryo

import synapse.tests.utils as s_t_utils

class UnivServerTest(s_t_utils.SynTest):

    async def test_server(self):

        with self.getTestDir() as dirn:

            outp = self.getTestOutp()
            guid = s_common.guid()

            argv = ['--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'univtest',
                    ]
            argu = list(argv)
            argu.extend(['synapse.cortex.Cortex', dirn])
            # Start a cortex with the universal loader
            async with await s_s_univ.main(argu, outp=outp) as core:

                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    podes = await s_t_utils.alist(proxy.eval(f'[ou:org={guid}]'))
                    self.len(1, podes)
                    self.eq('cortex', await proxy.getCellType())

                self.true(core.dmon.shared.get('univtest') is core)

            # And data persists... and can be seen with the regular synapse cortex server
            argu = list(argv)
            argu.append(dirn)
            async with await s_s_cortex.main(argu, outp=outp) as core:
                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    podes = await s_t_utils.alist(proxy.eval(f'ou:org={guid}'))
                    self.len(1, podes)

            argu = list(argv)
            argu.extend(['synapse.lib.cell.Cell', dirn])
            # Start a cortex as a regular Cell
            async with await s_s_univ.main(argu, outp=outp) as cell:
                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    self.eq('cell', await proxy.getCellType())

            argu = list(argv)
            argu.extend(['synapse.tests.test_lib_cell.EchoAuth', dirn])
            # Or start the Cortex off a a EchoAuth (don't do this in practice...)
            async with await s_s_univ.main(argu, outp=outp) as cell:
                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    self.eq('echoauth', await proxy.getCellType())

            argu = list(argv)
            argu.extend(['synapse.lib.newp.Newp', dirn])
            with self.raises(s_exc.NoSuchCtor):
                async with await s_s_univ.main(argu, outp=outp) as core:
                    pass

            argu = ['synapse.lib.cell.Cell', dirn,
                    '--telepath', 'tcp://127.0.0.1:9999999/',
                    '--https', '0',
                    '--name', 'telecore']
            # Coverage test, for a bad configuration
            with self.raises(OverflowError):
                obj = await s_s_univ.main(argu, outp=outp)
