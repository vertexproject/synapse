import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell

import synapse.tools.demote as s_tools_demote
import synapse.tools.shutdown as s_tools_shutdown

import synapse.tests.utils as s_test

async def boom(*args, **kwargs):
    raise s_exc.SynErr(mesg='BOOM')

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

                self.eq(0, await s_tools_demote.main(argv, outp=outp))
                outp.expect('Demoting leader: cell://')

                self.false(cell00.isactive)
                self.true(cell01.isactive)

                await cell00.sync()

                outp.clear()
                self.eq(1, await s_tools_demote.main(argv, outp=outp))
                outp.expect('Failed to demote service cell:')

                # get some test coverage for the various levels of exception handlers...

                with mock.patch.object(cell00, 'getNexsIndx', boom):
                    with self.getLoggerStream('synapse') as stream:
                        argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                        self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    self.isin('...error retrieving nexus index for', str(stream))

                with mock.patch.object(cell00, 'promote', boom):
                    with self.getLoggerStream('synapse') as stream:
                        argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                        self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    self.isin('...error promoting', str(stream))

                with mock.patch.object(cell01, '_getDemotePeers', boom):
                    with self.getLoggerStream('synapse') as stream:
                        argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                        self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    self.isin('...error demoting service', str(stream))

                self.false(cell00.isactive)
                self.true(cell01.isactive)

                outp.clear()
                self.eq(1, await s_tools_demote.main(['--url', 'newp://hehe'], outp=outp))
                outp.expect('Error while demoting service newp://hehe')

                # confirm that graceful shutdown with peers also demotes...
                outp.clear()
                argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                self.eq(0, await s_tools_shutdown.main(argv, outp=outp))

                self.true(cell00.isactive)
                self.false(cell01.isactive)

                self.true(await cell01.waitfini())

                # test demote with insufficient peers
                with self.getLoggerStream('synapse') as stream:
                    argv = ['--url', cell00.getLocalUrl(), '--timeout', '12']
                    self.eq(1, await s_tools_demote.main(argv, outp=outp))
                self.isin('...no suitable services discovered.', str(stream))

                # and that graceful shutdown without any cluster peers works too...
                outp.clear()
                argv = ['--url', cell00.getLocalUrl(), '--timeout', '12']
                self.eq(0, await s_tools_shutdown.main(argv, outp=outp))
