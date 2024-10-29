from unittest import mock

import synapse.tests.utils as s_t_utils

import synapse.tools.snapshot as s_tools_snapshot

class PromoteToolTest(s_t_utils.SynTest):

    async def test_tool_snapshot(self):

        async with self.getTestCore() as core:

            lurl = core.getLocalUrl()

            self.eq(0, await s_tools_snapshot.main(('freeze', '--svcurl', lurl)))
            self.true(core.paused)
            self.eq(1, await s_tools_snapshot.main(('freeze', '--svcurl', lurl)))

            self.eq(0, await s_tools_snapshot.main(('resume', '--svcurl', lurl)))
            self.false(core.paused)
            self.eq(1, await s_tools_snapshot.main(('resume', '--svcurl', lurl)))

            async with core.nexslock:
                argv = ('freeze', '--svcurl', lurl, '--timeout', '1')
                self.eq(1, await s_tools_snapshot.main(argv))

            def boom():
                raise Exception('boom')

            with mock.patch('os.sync', boom):
                self.eq(1, await s_tools_snapshot.main(('freeze', '--svcurl', lurl)))
                self.false(core.paused)
