import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils


class CmdTriggersTest(s_t_utils.SynTest):

    async def test_triggers(self):
        async with self.getTestDmon('dmoncore') as dmon, await self.agetTestProxy(dmon, 'core') as core:
            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

            await cmdr.runCmdLine('trigger.add node:add teststr [ testint=1 ]')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo ]'))
            await self.agenlen(1, await core.eval('testint'))

            await cmdr.runCmdLine('trigger.add tag:add teststr #footag.* [ +#count teststr=$tag ]')
            await s_common.aspin(await core.eval('sudo | [ teststr=bar +#footag.bar ]'))
            await self.agenlen(1, await core.eval('#count'))
            await self.agenlen(1, await core.eval('teststr=footag.bar'))

            await cmdr.runCmdLine('trigger.add prop:set testtype10.intprop [ testint=6 ]')
            await s_common.aspin(await core.eval('sudo | [ testtype10=1 :intprop=25 ]'))
            await self.agenlen(1, await core.eval('testint=6'))

            await cmdr.runCmdLine('trigger.list')
            self.true(outp.expect('user'))
            self.true(outp.expect('<None>'))
            self.true(outp.expect('<None>'))
            self.true(outp.expect('<None>'))
            goodbuid = outp.mesgs[1].split()[1][:6]
            goodbuid2 = outp.mesgs[2].split()[1][:6]

            await cmdr.runCmdLine(f'trigger.del {goodbuid}')
            self.true(outp.expect('Deleted trigger'))

            await cmdr.runCmdLine(f'trigger.del deadbeef12341234')
            self.true(outp.expect('does not match'))

            await cmdr.runCmdLine(f'trigger.mod {goodbuid2} [ teststr=different ]')
            self.true(outp.expect('Modified trigger'))

            await cmdr.runCmdLine(f'trigger.mod deadbeef12341234')
            self.true(outp.expect('does not match'))

            await cmdr.runCmdLine('trigger.add tag:add #another [ +#count2 ]')

            # Syntax mistake
            await cmdr.runCmdLine('trigger.add tag:add another [ +#count2 ]')
            self.true(outp.expect('starting with #'))
            await cmdr.runCmdLine('trigger.add tug:udd another [ +#count2 ]')
            self.true(outp.expect('Unrecognized'))
            await cmdr.runCmdLine('trigger.add tag:add')
            self.true(outp.expect('Valid values for condition'))
