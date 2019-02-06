import os
import argparse

import synapse.common as s_common

import synapse.servers.cortex as s_s_cortex

import synapse.tests.utils as s_t_utils

class CortexServerTest(s_t_utils.SynTest):

    async def test_server(self):
        with self.getTestDir() as dirn:
            outp = self.getTestOutp()

            opts = argparse.Namespace(port=0,
                                      coredir=dirn,
                                      host='127.0.01',
                                      )
            dmon = await s_s_cortex.mainopts(opts, outp)

            # Make a node with the cortex
            guid = s_common.guid()
            async with await self.getTestProxy(dmon, 'cortex') as proxy:
                podes = await s_t_utils.alist(await proxy.eval(f'[ou:org={guid}]'))
                self.len(1, podes)

            await dmon.fini()

            # And data persists...
            dmon = await s_s_cortex.mainopts(opts, outp)
            async with await self.getTestProxy(dmon, 'cortex') as proxy:
                podes = await s_t_utils.alist(await proxy.eval(f'ou:org={guid}'))
                self.len(1, podes)
            await dmon.fini()
