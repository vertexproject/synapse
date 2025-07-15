import synapse.common as s_common

import synapse.lib.cell as s_cell


import synapse.tests.utils as s_test
import synapse.tools.shutdown as s_t_shutdown

class ShutdownToolTest(s_test.SynTest):

    async def test_tool_shutdown_base(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('background { $lib.time.sleep(10) }')
            self.stormHasNoWarnErr(msgs)

            # add a dmon to ensure task.background=True works correctly
            await core.addStormDmon({
                'iden': s_common.guid(),
                'storm': 'while (true) { $lib.time.sleep(1) }',
            })

            argv = ['--url', core.getLocalUrl(), '--timeout', '0']

            self.eq(1, await s_t_shutdown.main(argv))

            for task in core.boss.ps():
                if task.name == 'storm':
                    await task.kill()

            self.eq(0, await s_t_shutdown.main(['--url', core.getLocalUrl()]))

            self.true(await core.waitfini(timeout=1))

        outp = self.getTestOutp()
        self.eq(1, await s_t_shutdown.main(['--url', 'newp://hehe'], outp=outp))
        outp.expect('Error while attempting graceful shutdown')

    async def test_tool_shutdown_leader(self):

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

                # confirm that graceful shutdown with peers also demotes...
                outp = self.getTestOutp()
                argv = ['--url', cell00.getLocalUrl(), '--timeout', '12']
                self.eq(0, await s_t_shutdown.main(argv, outp=outp))

                self.false(cell00.isactive)
                self.true(cell01.isactive)
                self.true(await cell00.waitfini(timeout=12))

                # and that graceful shutdown without any cluster peers works too...
                outp.clear()
                argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                self.eq(0, await s_t_shutdown.main(argv, outp=outp))
                self.true(await cell01.waitfini(timeout=12))

    async def test_tool_shutdown_no_features(self):

        async with self.getTestAha() as aha:
            aha.features.pop('getAhaSvcsByIden')

            with self.getTestDir() as dirn:

                dirn00 = s_common.genpath(dirn, '00.cell')
                dirn01 = s_common.genpath(dirn, '01.cell')

                cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                   provinfo={'mirror': 'cell'}))
                self.true(cell00.isactive)
                self.false(cell01.isactive)

                await cell01.sync()

                # confirm that graceful shutdown with peers also demotes...
                outp = self.getTestOutp()
                argv = ['--url', cell00.getLocalUrl(), '--timeout', '12']
                with self.getAsyncLoggerStream('synapse.daemon') as stream:
                    self.eq(1, await s_t_shutdown.main(argv, outp=outp))
                stream.expect('AHA server does not support feature: getAhaSvcsByIden >= 1')
