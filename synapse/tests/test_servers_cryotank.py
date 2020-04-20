import synapse.cryotank as s_cryo

import synapse.tests.utils as s_t_utils

class CryoServerTest(s_t_utils.SynTest):

    async def test_server(self):

        recs = (
            ('hehe', {'haha': 1}),
            ('woah', {'dude': 1}),
        )

        with self.getTestDir() as dirn, self.withSetLoggingMock() as mock:

            outp = self.getTestOutp()

            argv = [dirn,
                    '--telepath', 'tcp://127.0.0.1:0/',
                    '--https', '0',
                    '--name', 'telecryo']

            async with await s_cryo.CryoCell.initFromArgv(argv, outp=outp) as cryotank:
                async with cryotank.getLocalProxy() as proxy:
                    await proxy.puts('foo', recs)

                self.true(cryotank.dmon.shared.get('telecryo') is cryotank)

            # And data persists...
            async with await s_cryo.CryoCell.initFromArgv(argv, outp=outp) as telecryo:
                async with telecryo.getLocalProxy() as proxy:
                    precs = await s_t_utils.alist(proxy.slice('foo', 0, 100))
                    precs = [rec for offset, rec in precs]
                    self.eq(precs, recs)
