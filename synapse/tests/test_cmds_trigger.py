import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils

class CmdTriggersTest(s_t_utils.SynTest):

    async def test_triggers(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            outp = self.getTestOutp()
            cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

            await cmdr.runCmdLine('trigger list')
            self.true(outp.expect('No triggers found'))

            await cmdr.runCmdLine('trigger add node:add test:str {[ test:int=1 ] }')
            trigs = await realcore.view.listTriggers()
            self.len(1, trigs)
            self.true(outp.expect(f'Added trigger {trigs[0][0]}'))
            self.eq(1, await core.count('[ test:str=foo ]'))
            self.eq(1, await core.count('test:int'))

            await cmdr.runCmdLine('trigger add tag:add test:str #footag.* {[ +#count test:str=$tag ]}')
            self.eq(1, await core.count('[ test:str=bar +#footag.bar ]'))
            self.eq(1, await core.count('#count'))
            self.eq(1, await core.count('test:str=footag.bar'))

            await cmdr.runCmdLine('trigger add prop:set --disabled test:type10:intprop {[ test:int=6 ]}')
            outp.clear()
            await cmdr.runCmdLine('trigger list')
            self.true(outp.expect('user'))
            self.true(outp.expect('root'))
            goodbuid = outp.mesgs[-2].split()[1][:6]
            goodbuid2 = outp.mesgs[-1].split()[1][:6]

            # Trigger is created disabled, so no nodes yet
            self.eq(0, await core.count('test:int=6'))
            await cmdr.runCmdLine(f'trigger enable {goodbuid2}')

            # Trigger is enabled, so it should fire
            self.eq(1, await core.count('[ test:type10=1 :intprop=25 ]'))
            self.eq(1, await core.count('test:int=6'))

            await cmdr.runCmdLine(f'trigger del {goodbuid}')
            self.true(outp.expect('Deleted trigger'))

            await cmdr.runCmdLine(f'trigger del deadbeef12341234')
            self.true(outp.expect('does not match'))

            outp.clear()
            await cmdr.runCmdLine(f'trigger enable deadbeef12341234')
            self.true(outp.expect('does not match'))

            outp.clear()
            await cmdr.runCmdLine(f'trigger disable deadbeef12341234')
            self.true(outp.expect('does not match'))

            await cmdr.runCmdLine(f'trigger disable {goodbuid2}')
            self.true(outp.expect('Disabled trigger'))

            await cmdr.runCmdLine(f'trigger enable {goodbuid2}')
            self.true(outp.expect('Enabled trigger'))

            await cmdr.runCmdLine(f'trigger mod {goodbuid2} {{[ test:str=different ]}}')
            self.true(outp.expect('Modified trigger'))

            outp.clear()
            await cmdr.runCmdLine('trigger mod deadbeef12341234 {#foo}')
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
            self.eq(1, await core.count('[ test:str=foo4 ]'))
            self.eq(1, await core.count('test:int=99'))

            # Test manipulating triggers as another user
            bond = await realcore.auth.addUser('bond')

            async with realcore.getLocalProxy(user='bond') as tcore:

                toutp = self.getTestOutp()
                tcmdr = await s_cmdr.getItemCmdr(tcore, outp=toutp)

                await tcmdr.runCmdLine('trigger list')
                self.true(toutp.expect('No triggers found'))

                await tcmdr.runCmdLine(f'trigger mod {goodbuid2} {{[ test:str=yep ]}}')
                self.true(toutp.expect('provided iden does not match'))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger disable {goodbuid2}')
                self.true(toutp.expect('provided iden does not match'))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger enable {goodbuid2}')
                self.true(toutp.expect('provided iden does not match'))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger del {goodbuid2}')
                self.true(toutp.expect('provided iden does not match'))

                # Give explicit perm
                await core.addUserRule(bond.iden, (True, ('trigger', 'get')))

                toutp.clear()
                await tcmdr.runCmdLine('trigger list')
                self.true(toutp.expect('root'))

                await core.addUserRule(bond.iden, (True, ('trigger', 'set')))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger mod {goodbuid2} {{[ test:str=yep ]}}')
                self.true(toutp.expect('Modified trigger'))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger disable {goodbuid2}')
                self.true(toutp.expect('Disabled trigger '))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger enable {goodbuid2}')
                self.true(toutp.expect('Enabled trigger '))

                await core.addUserRule(bond.iden, (True, ('trigger', 'del')))

                toutp.clear()
                await tcmdr.runCmdLine(f'trigger del {goodbuid2}')
                self.true(toutp.expect('Deleted trigger '))
