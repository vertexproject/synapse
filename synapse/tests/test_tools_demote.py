import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell

import synapse.tools.demote as s_tools_demote

import synapse.tests.utils as s_test

class DemoteToolTest(s_test.SynTest):

    async def test_tool_demote(self):

        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:

                dirn00 = s_common.genpath(dirn, '00.cell')
                dirn01 = s_common.genpath(dirn, '01.cell')

                cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                   provinfo={'mirror': 'cell'}))
                self.true(cell00.isactive)
                self.false(cell01.isactive)

                await cell01.sync()

                outp = self.getTestOutp()
                argv = ['--url', cell00.getLocalUrl()]

                self.eq(1, await s_tools_demote.main(argv, outp=outp))

                self.false(cell00.isactive)
                self.true(cell01.isactive)

                await cell00.sync()
