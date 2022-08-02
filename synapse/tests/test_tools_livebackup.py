import os

import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.tests.utils as s_test
import synapse.tools.livebackup as s_t_livebackup

class LivebackupTest(s_test.SynTest):

    async def test_tools_livebackup(self):
        async with self.getTestCore() as core:

            svcurl = core.getLocalUrl()
            argv = (
                '--url', svcurl,
                '--name', 'visi123',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_livebackup.main(argv, outp=outp))
            self.isin(f'Running backup of: {svcurl}', str(outp))
            self.isin(f'...backup created: visi123', str(outp))
            self.true(os.path.isfile(s_common.genpath(core.dirn, 'backups', 'visi123', 'cell.guid')))
