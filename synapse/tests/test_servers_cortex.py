import os
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.servers.cortex as s_s_cortex

import synapse.tests.utils as s_t_utils

class CortexServerTest(s_t_utils.SynTest):

    async def test_server(self):

        with self.getTestDir() as dirn:

            outp = self.getTestOutp()
            opts = s_s_cortex.parse([dirn])

            guid = s_common.guid()

            async with await s_s_cortex.mainopts(opts, outp) as core:

                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    # Make a node with the cortex
                    podes = await s_t_utils.alist(await proxy.eval(f'[ou:org={guid}]'))
                    self.len(1, podes)

            # And data persists...
            async with await s_s_cortex.mainopts(opts, outp) as core:
                async with await s_telepath.openurl(f'cell://{dirn}') as proxy:
                    podes = await s_t_utils.alist(await proxy.eval(f'ou:org={guid}'))
                    self.len(1, podes)
