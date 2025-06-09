import synapse.common as s_common

import synapse.lib.output as s_output

import synapse.tests.utils as s_test
import synapse.tools.shutdown as s_shutdown

class ShutdownToolTest(s_test.SynTest):

    async def test_tool_shutdown(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('background { $lib.time.sleep(10) }')
            self.stormHasNoWarnErr(msgs)

            # add a dmon to ensure task.background=True works correctly
            await core.addStormDmon({
                'iden': s_common.guid(),
                'storm': 'while (true) { $lib.time.sleep(1) }',
            })

            argv = ['--url', core.getLocalUrl(), '--timeout', '0']

            self.eq(1, await s_shutdown.main(argv))

            for task in core.boss.ps():
                if task.name == 'storm':
                    await task.kill()

            self.eq(0, await s_shutdown.main(['--url', core.getLocalUrl()]))

            self.true(await core.waitfini(timeout=1))

        outp = s_output.OutPutStr()
        self.eq(1, await s_shutdown.main(['--url', 'newp://hehe'], outp=outp))

        self.isin('Error while attempting graceful shutdown', str(outp))
