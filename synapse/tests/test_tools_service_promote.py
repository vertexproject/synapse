import synapse.common as s_common

import synapse.lib.base as s_base

import synapse.tools.service.promote as s_tools_promote

import synapse.tests.utils as s_t_utils


class PromoteToolTest(s_t_utils.SynTest):

    async def test_tool_promote_simple(self):
        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_t_utils.TestCell00, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_t_utils.TestCell00, dirn=dirn01))
                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    await cell01.sync()

                    outp = self.getTestOutp()
                    argv = ['--url', cell00.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(1, ret)
                    outp.expect('Failed to promote service')
                    outp.expect('promote() called on a service which is not a follower')

                    outp.clear()
                    argv = ['--url', cell01.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(0, ret)
                    self.false(cell00.isactive)
                    self.true(cell01.isactive)
                    await cell00.sync()

    async def test_tool_promote_failure(self):
        # --failure maps to a forced promotion, which does not coordinate
        # with the current leader ( unlike the default graceful handoff ).
        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_t_utils.TestCell00, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_t_utils.TestCell00, dirn=dirn01))
                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    await cell01.sync()

                    outp = self.getTestOutp()
                    argv = ['--url', cell01.getLocalUrl(), '--failure']
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(0, ret)

                    # the forced promotion never contacted the old leader, so
                    # it does not yet know it has been demoted ( split-brain ).
                    self.true(cell01.isactive)
                    self.true(cell00.isactive)

    async def test_tool_promote_schism(self):
        # under dynamic leadership every follower syncs from the current leader,
        # so promoting any follower gracefully hands off from the current leader.
        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')
                    dirn02 = s_common.genpath(dirn, '02.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_t_utils.TestCell00, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_t_utils.TestCell00, dirn=dirn01))
                    cell02 = await base.enter_context(self.addSvcToAha(aha, '02.cell', s_t_utils.TestCell00, dirn=dirn02))
                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    self.false(cell02.isactive)
                    await cell02.sync()

                    outp = self.getTestOutp()
                    argv = ['--url', cell02.getLocalUrl()]
                    ret = await s_tools_promote.main(argv, outp=outp)
                    self.eq(0, ret)
                    self.false(cell00.isactive)
                    self.true(cell02.isactive)
