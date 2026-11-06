import synapse.exc as s_exc

import synapse.lib.cell as s_cell

import synapse.tools.service.v3ready as s_tools_v3ready

import synapse.tests.utils as s_test
import synapse.tests.test_lib_cell as s_t_cell

class V3ReadyToolTest(s_test.SynTest):

    async def test_tool_v3ready(self):

        async with self.getTestCell(s_t_cell.V3Cell) as cell:

            argv = ['--url', cell.getLocalUrl()]

            cell.v3mesgs = [('print', 'Checking...'), ('warning', 'Something to know.')]

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3ready.main(argv + ['check'], outp=outp))
            outp.expect('Checking...')
            outp.expect('WARNING: Something to know.')
            outp.expect('The service is ready for Synapse 3.x.')
            self.true((await cell.getV3Value('preflight', 'result'))['ok'])

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3ready.main(argv + ['prepare'], outp=outp))
            self.len(2, [line for line in str(outp).splitlines() if line == 'Checking...'])
            outp.expect('The service is ready for Synapse 3.x.')
            self.true((await cell.getV3Value('prepare', 'result'))['ok'])

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3ready.main(argv + ['prepare', '--no-check'], outp=outp))
            self.len(1, [line for line in str(outp).splitlines() if line == 'Checking...'])
            self.notin('ready for Synapse 3.x', str(outp))

            cell.v3mesgs = [('error', 'Not ready.')]

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3ready.main(argv + ['check'], outp=outp))
            outp.expect('ERROR: Not ready.')
            outp.expect('The service is not ready for Synapse 3.x.')

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3ready.main(argv + ['prepare'], outp=outp))
            outp.expect('ERROR: Not ready.')
            outp.expect('The service could not be prepared for Synapse 3.x.')
            self.notin('The service is not ready', str(outp))

            cell.v3mesgs = [s_exc.BadState(mesg='Nope.')]

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3ready.main(argv + ['check'], outp=outp))
            outp.expect('ERROR: BadState: Nope.')

        async with self.getTestCell(s_cell.Cell) as cell:

            argv = ['--url', cell.getLocalUrl()]

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3ready.main(argv + ['prepare'], outp=outp))
            outp.expect('The service has nothing to prepare for Synapse 3.x.')
            outp.expect('ERROR: NoSuchImpl: cell has no Synapse 3.x readiness check.')

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3ready.main(argv + ['prepare', '--no-check'], outp=outp))
            outp.expect('The service has nothing to prepare for Synapse 3.x.')
