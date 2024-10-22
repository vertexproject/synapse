import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell

import synapse.tools.promote as s_tools_promote

import synapse.tests.utils as s_t_utils


class PromoteToolTest(s_t_utils.SynTest):

    async def test_tool_promote_schism(self):

        # Create a mirror of mirrors and try promoting the end mirror.
        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')
                    dirn02 = s_common.genpath(dirn, '02.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                       provinfo={'mirror': '00.cell'}))
                    cell02 = await base.enter_context(self.addSvcToAha(aha, '02.cell', s_cell.Cell, dirn=dirn02,
                                                                       provinfo={'mirror': '01.cell'}))
                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    self.false(cell02.isactive)
                    await cell02.sync()

                    outp = self.getTestOutp()
                    argv = ['--svcurl', cell02.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(1, ret)
                    outp.expect('Failed to promote service')
                    outp.expect('it is currently following ahaname=01.cell which is not a leader')
