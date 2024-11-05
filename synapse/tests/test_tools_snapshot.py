from unittest import mock

import synapse.lib.output as s_output
import synapse.tools.snapshot as s_tools_snapshot

import synapse.tests.utils as s_t_utils

class PromoteToolTest(s_t_utils.SynTest):

    async def test_tool_snapshot(self):

        async with self.getTestCore() as core:

            lurl = core.getLocalUrl()

            self.eq(0, await s_tools_snapshot.main(('freeze', '--svcurl', lurl)))
            self.true(core.paused)

            outp = s_output.OutPutStr()
            self.eq(1, await s_tools_snapshot.main(('freeze', '--svcurl', lurl), outp=outp))
            self.isin('ERROR BadState', str(outp))

            self.eq(0, await s_tools_snapshot.main(('resume', '--svcurl', lurl)))
            self.false(core.paused)

            outp = s_output.OutPutStr()
            self.eq(1, await s_tools_snapshot.main(('resume', '--svcurl', lurl), outp=outp))
            self.isin('ERROR BadState', str(outp))

            outp = s_output.OutPutStr()
            async with core.nexslock:
                argv = ('freeze', '--svcurl', lurl, '--timeout', '1')
                self.eq(1, await s_tools_snapshot.main(argv, outp=outp))
                self.isin('ERROR TimeOut', str(outp))

            def boom():
                raise Exception('boom')

            outp = s_output.OutPutStr()
            with mock.patch('os.sync', boom):
                self.eq(1, await s_tools_snapshot.main(('freeze', '--svcurl', lurl), outp=outp))
                self.false(core.paused)
                self.isin('ERROR SynErr: boom', str(outp))

            outp = s_output.OutPutStr()
            self.eq(1, await s_tools_snapshot.main(('freeze', '--svcurl', 'newp://newp'), outp=outp))
            self.isin('ERROR BadUrl', str(outp))
