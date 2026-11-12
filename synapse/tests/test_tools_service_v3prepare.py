import synapse.exc as s_exc

import synapse.lib.cell as s_cell

import synapse.tools.service.v3prepare as s_tools_v3prepare

import synapse.tests.utils as s_test
import synapse.tests.test_lib_cell as s_t_cell

class V3PrepareToolTest(s_test.SynTest):

    async def test_tool_v3prepare(self):

        async with self.getTestCell(s_t_cell.V3Cell) as cell:

            argv = ['--url', cell.getLocalUrl()]

            cell.v3check = [('print', 'Checking...'), ('warning', 'Something to know.')]

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3prepare.main(argv + ['--dry-run'], outp=outp))
            outp.expect('Checking...')
            outp.expect('WARNING: Something to know.')
            outp.expect('The service has no errors blocking Synapse 3.x.')
            outp.expect('This was a dry run, so nothing was prepared or recorded.')
            self.notin('Preparing...', str(outp))
            self.none(await cell.getV3Value('preflight', 'result', defval=None))

            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3prepare.main(argv, outp=outp))
            outp.expect('Checking...')
            outp.expect('Preparing...')
            outp.expect('The service is ready for Synapse 3.x.')
            self.true((await cell.getV3Value('preflight', 'result'))['ok'])

            cell.v3check = [('error', 'Fix the widgets.')]

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3prepare.main(argv + ['--dry-run'], outp=outp))
            outp.expect('ERROR: Fix the widgets.')
            outp.expect('The service has errors blocking Synapse 3.x.')

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3prepare.main(argv, outp=outp))
            outp.expect('ERROR: Fix the widgets.')
            outp.expect('This v3cell was not prepared for Synapse 3.x, as its check has errors.')
            outp.expect('The service is not ready for Synapse 3.x.')
            self.notin('Preparing...', str(outp))
            self.false((await cell.getV3Value('preflight', 'result'))['ok'])

            cell.v3check = [s_exc.BadState(mesg='Nope.')]

            outp = self.getTestOutp()
            self.eq(1, await s_tools_v3prepare.main(argv, outp=outp))
            outp.expect('ERROR: BadState: Nope.')

        async with self.getTestCell(s_cell.Cell) as cell:

            argv = ['--url', cell.getLocalUrl()]

            # a cell type with no checks and nothing to prepare is ready
            outp = self.getTestOutp()
            self.eq(0, await s_tools_v3prepare.main(argv, outp=outp))
            outp.expect('This cell has no Synapse 3.x readiness checks.')
            outp.expect('This cell has nothing to prepare for Synapse 3.x.')
            outp.expect('The service is ready for Synapse 3.x.')
            self.true((await cell.getV3Value('preflight', 'result'))['ok'])
