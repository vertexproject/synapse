import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell

import synapse.tools.promote as s_tools_promote

import synapse.tests.utils as s_t_utils


class PromoteToolTest(s_t_utils.SynTest):

    async def test_tool_promote_simple(self):
        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                       provinfo={'mirror': 'cell'}))
                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    await cell01.sync()

                    outp = self.getTestOutp()
                    argv = ['--svcurl', cell00.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(1, ret)
                    outp.expect('Failed to promote service')
                    outp.expect('promote() called on non-mirror')

                    outp.clear()
                    argv = ['--svcurl', cell01.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(0, ret)
                    self.false(cell00.isactive)
                    self.true(cell01.isactive)
                    await cell00.sync()

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
                    # Note: The following message may change when SYN-7659 is addressed
                    outp.expect('ahaname=01.cell is not the current leader and cannot handoff leadership to aha://02.cell.synapse')
