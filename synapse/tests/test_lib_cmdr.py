import asyncio

import synapse.exc as s_exc

import synapse.lib.cli as s_cli
import synapse.lib.cmdr as s_cmdr
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

class CmdrTest(s_t_utils.SynTest):

    async def test_getItemCmdr(self):
        async with self.getTestCore() as core:
            outp = self.getTestOutp()
            async with core.getLocalProxy() as prox:
                cli = await s_cmdr.getItemCmdr(prox, outp=outp, color=False,
                                         key='valu')
                self.isinstance(cli, s_cli.Cli)
                self.eq(cli.locs.get('key'), 'valu')

    async def test_interface_registration(self):
        self.none(s_cmdr.cmdsbyinterface.get('_cmdrtest'))
        s_cmdr.addInterfaceCmd('_cmdrtest', str)
        self.eq(s_cmdr.cmdsbyinterface.get('_cmdrtest'), (str,))
        s_cmdr.addInterfaceCmd('_cmdrtest', int)
        self.eq(s_cmdr.cmdsbyinterface.get('_cmdrtest'), (str, int))
