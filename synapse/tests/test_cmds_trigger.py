import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils

class CmdTriggersTest(s_t_utils.SynTest):

    async def test_triggers(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

            await cmdr.runCmdLine('trigger add Node:add test:str {[ test:int=1 ] }')
            await s_common.aspin(core.eval('[ test:str=foo ]'))
            await self.agenlen(1, core.eval('test:int'))

            await cmdr.runCmdLine('trigger add tag:add test:str #footag.* {[ +#count test:str=$tag ]}')
            await s_common.aspin(core.eval('[ test:str=bar +#footag.bar ]'))
            await self.agenlen(1, core.eval('#count'))
            await self.agenlen(1, core.eval('test:str=footag.bar'))

            await cmdr.runCmdLine('trigger add prop:set test:type10:intprop {[ test:int=6 ]}')
            await s_common.aspin(core.eval('[ test:type10=1 :intprop=25 ]'))
            await self.agenlen(1, core.eval('test:int=6'))

            await cmdr.runCmdLine('trigger list')
            self.true(outp.expect('user'))
            self.true(outp.expect('root'))
            goodbuid = outp.mesgs[-2].split()[1][:6]
            goodbuid2 = outp.mesgs[-1].split()[1][:6]

            await cmdr.runCmdLine(f'trigger del {goodbuid}')
            self.true(outp.expect('Deleted trigger'))

            await cmdr.runCmdLine(f'trigger del deadbeef12341234')
            self.true(outp.expect('does not match'))

            await cmdr.runCmdLine(f'trigger mod {goodbuid2} {{[ test:str=different ]}}')
            self.true(outp.expect('Modified trigger'))

            await cmdr.runCmdLine(f'trigger mod deadbeef12341234')
            self.true(outp.expect('does not match'))

            await cmdr.runCmdLine('trigger add tag:add #another {[ +#count2 ]}')

            # Syntax mistakes
            await cmdr.runCmdLine(f'trigger')
            self.true(outp.expect('Manipulate triggers in a '))

            await cmdr.runCmdLine('trigger add tag:add another {[ +#count2 ]}')
            self.true(outp.expect('Missing tag parameter'))

            await cmdr.runCmdLine('trigger add tug:udd another {[ +#count2 ]}')
            self.true(outp.expect('invalid choice'))

            await cmdr.runCmdLine('trigger add tag:add')
            self.true(outp.expect('trigger add: error: the following'))

            await cmdr.runCmdLine('trigger add tag:add inet:ipv4')
            self.true(outp.expect('Missing argument for trigger add'))

            await cmdr.runCmdLine('trigger add')
            self.true(outp.expect('Add triggers in a cortex.'))

            await cmdr.runCmdLine('trigger add tag:add #foo #bar')
            self.true(outp.expect('single tag'))

            await cmdr.runCmdLine('trigger add tag:add {test:str} {test:str}')
            self.true(outp.expect('single query'))

            await cmdr.runCmdLine('trigger add node:add test:str #foo {test:str}')
            self.true(outp.expect('node:* does not support'))

            await cmdr.runCmdLine('trigger add prop:set #foo {test:str}')
            self.true(outp.expect('Missing prop parameter'))

            await cmdr.runCmdLine('trigger add prop:set test:type10.intprop #foo {test:str}')
            self.true(outp.expect('prop:set does not support a tag'))

            await cmdr.runCmdLine('trigger add node:add test:str test:int {test:str}')
            self.true(outp.expect('Only a single form'))

            await cmdr.runCmdLine('trigger add prop:set test:type10.intprop test:str {test:str}')
            self.true(outp.expect('single prop'))

            await cmdr.runCmdLine('trigger add tag:add #tag test:int')
            self.true(outp.expect('Missing query'))

            await cmdr.runCmdLine('trigger add node:add #tag1 {test:str}')
            self.true(outp.expect('Missing form'))

            await cmdr.runCmdLine(f'trigger mod {goodbuid2} test:str')
            self.true(outp.expect('start with {'))

            # Bad storm syntax
            await cmdr.runCmdLine('trigger add node:add test:str {[ | | test:int=1 ] }')
            self.true(outp.expect('BadSyntax'))

            # (Regression) Just a command as the storm query
            await cmdr.runCmdLine('trigger add Node:add test:str {[ test:int=99 ] | spin }')
            await s_common.aspin(core.eval('[ test:str=foo4 ]'))
            await self.agenlen(1, core.eval('test:int=99'))
