import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell

import synapse.tools.service.demote as s_tools_demote

import synapse.tests.utils as s_test

async def boom(*args, **kwargs):
    raise s_exc.SynErr(mesg='BOOM')

async def zero(*args, **kwargs):
    return 0

class DemoteToolTest(s_test.SynTest):

    async def test_tool_demote_base(self):

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
                        await stream.expect('...error retrieving nexus index for', timeout=1)

                with mock.patch.object(cell00, 'promote', boom):
                    with self.getLoggerStream('synapse') as stream:
                        argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                        self.eq(1, await s_tools_demote.main(argv, outp=outp))
                        await stream.expect('...error promoting', timeout=1)

                with mock.patch.object(cell01, '_getDemotePeers', boom):
                    with self.getLoggerStream('synapse') as stream:
                        argv = ['--url', cell01.getLocalUrl(), '--timeout', '12']
                        outp.clear()
                        self.eq(1, await s_tools_demote.main(argv, outp=outp))
                        outp.expect('Error while demoting service')
                        await stream.expect('error during task: demote', timeout=1)

                self.false(cell00.isactive)
                self.true(cell01.isactive)

                outp.clear()
                self.eq(1, await s_tools_demote.main(['--url', 'newp://hehe'], outp=outp))
                outp.expect('Error while demoting service newp://hehe')

                self.true(await aha.schedCoro(cell01.shutdown(timeout=12)))
                self.true(cell00.isactive)
                self.false(cell01.isactive)

                self.true(await cell01.waitfini(timeout=12))

                # test demote with insufficient peers
                with self.getLoggerStream('synapse') as stream:
                    argv = ['--url', cell00.getLocalUrl(), '--timeout', '12']
                    self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    await stream.expect('...no suitable services discovered.', timeout=1)

                # a mirror which is not promotable is never selected
                dirn02 = s_common.genpath(dirn, '02.cell')
                provinfo = {'mirror': 'cell', 'conf': {'aha:promotable': False}}
                cell02 = await aha.enter_context(self.addSvcToAha(aha, '02.cell', s_cell.Cell, dirn=dirn02,
                                                                   provinfo=provinfo))
                self.false(cell02.conf.get('aha:promotable'))
                await cell02.sync()

                with self.getLoggerStream('synapse') as stream:
                    self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    await stream.expect('...no suitable services discovered.', timeout=1)

                self.true(cell00.isactive)
                self.false(cell02.isactive)

                dirn03 = s_common.genpath(dirn, '03.cell')
                cell03 = await aha.enter_context(self.addSvcToAha(aha, '03.cell', s_cell.Cell, dirn=dirn03,
                                                                   provinfo={'mirror': 'cell'}))
                await cell02.sync()
                await cell03.sync()

                self.eq(0, await s_tools_demote.main(argv, outp=outp))
                self.false(cell00.isactive)
                self.false(cell02.isactive)
                self.true(cell03.isactive)

                # two promotable mirrors at the same nexus index
                dirn04 = s_common.genpath(dirn, '04.cell')
                cell04 = await aha.enter_context(self.addSvcToAha(aha, '04.cell', s_cell.Cell, dirn=dirn04,
                                                                   provinfo={'mirror': 'cell'}))
                await cell00.sync()
                await cell02.sync()
                await cell04.sync()

                self.eq(await cell00.getNexsIndx(), await cell04.getNexsIndx())

                argv = ['--url', cell03.getLocalUrl(), '--timeout', '12']
                self.eq(0, await s_tools_demote.main(argv, outp=outp))
                self.false(cell02.isactive)
                self.false(cell03.isactive)
                self.ne(cell00.isactive, cell04.isactive)

                # the most current mirror is promoted first
                leader, othr = (cell00, cell04) if cell00.isactive else (cell04, cell00)
                await cell02.sync()
                await cell03.sync()
                await othr.sync()

                with mock.patch.object(cell03, 'getNexsIndx', zero):
                    argv = ['--url', leader.getLocalUrl(), '--timeout', '12']
                    self.eq(0, await s_tools_demote.main(argv, outp=outp))

                self.false(leader.isactive)
                self.false(cell02.isactive)
                self.false(cell03.isactive)
                self.true(othr.isactive)

    async def test_tool_demote_no_features(self):

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

                outp = self.getTestOutp()
                argv = ['--url', cell00.getLocalUrl()]
                with self.getLoggerStream('synapse.daemon') as stream:
                    self.eq(1, await s_tools_demote.main(argv, outp=outp))
                    await stream.expect('AHA server does not support feature: getAhaSvcsByIden >= 1', timeout=1)

                outp.expect('Error while demoting service')
