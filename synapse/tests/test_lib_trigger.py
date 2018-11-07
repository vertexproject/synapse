import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class TrigTest(s_t_utils.SynTest):
    async def test_trigger_with_auth(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            await self.trigger_tests(dmon)

    async def test_trigger_no_auth(self):
        async with self.getTestDmon(mirror='dmoncore') as dmon:
            await self.trigger_tests(dmon)

    async def trigger_tests(self, dmon):
        pconf = {'user': 'root', 'passwd': 'root'}
        async with await self.agetTestProxy(dmon, 'core', **pconf) as core:

            # node:add case
            await core.addTrigger('node:add', 'sudo | [ testint=1 ]', form='teststr')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo ]'))
            await self.agenlen(1, await core.eval('testint'))

            # node:del case
            await core.addTrigger('node:del', 'sudo | [ testint=2 ]', form='teststr')
            await s_common.aspin(await core.eval('sudo | teststr=foo | delnode'))
            await self.agenlen(2, await core.eval('testint'))

            # tag:add case
            await core.addTrigger('tag:add', 'sudo | [ testint=3 ]', tag='footag')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo +#footag ]'))
            await self.agenlen(3, await core.eval('testint'))

            # tag:add globbing and storm var
            await core.addTrigger('tag:add', 'sudo | [ +#count teststr=$tag ]', tag='footag.*')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo +#footag.bar ]'))
            await s_common.aspin(await core.eval('sudo | [ teststr=foo +#footag ]'))
            await s_common.aspin(await core.eval('sudo | [ teststr=foo +#foota.bar ]'))
            await self.agenlen(1, await core.eval('#count'))
            await self.agenlen(1, await core.eval('teststr=footag.*'))

            # tag:del case
            await core.addTrigger('tag:del', 'sudo | [ testint=4 ]', tag='footag')
            await s_common.aspin(await core.eval('teststr=foo | sudo | [ -#footag ]'))
            await self.agenlen(1, await core.eval('testint=4'))

            # Form/tag add
            await core.addTrigger('tag:add', 'sudo | [ testint=5 ]', tag='bartag', form='teststr')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo +#bartag ]'))
            await self.agenlen(1, await core.eval('testint=5'))

            # Wrong form/right tag add doesn't fire
            await s_common.aspin(await core.eval('sudo | testint=5 | delnode'))
            await self.agenlen(0, await core.eval('testint=5'))
            await s_common.aspin(await core.eval('sudo | [ testauto=1 +#bartag ]'))
            await self.agenlen(0, await core.eval('testint=5'))

            # Right form/wrong tag add doesn't fire
            await s_common.aspin(await core.eval('sudo | [ teststr=bar +#footag ]'))
            await self.agenlen(0, await core.eval('testint=5'))

            # Prop set
            await core.addTrigger('prop:set', 'sudo | [ testint=6 ]', prop='testtype10.intprop')
            await s_common.aspin(await core.eval('sudo | [ testtype10=1 ]'))
            await self.agenlen(1, await core.eval('testint=6'))  # Triggered by default value setting
            await s_common.aspin(await core.eval('sudo | [ testtype10=1 :intprop=25 ]'))
            await self.agenlen(1, await core.eval('testint=6'))

            # Test re-setting doesn't fire
            await s_common.aspin(await core.eval('sudo | testint=6 | delnode'))
            await s_common.aspin(await core.eval('sudo | [ testtype10=1 :intprop=25 ]'))
            await self.agenlen(0, await core.eval('testint=6'))

            # Bad trigger parms
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('nocond', 'testint=4', form='teststr'))
            await self.asyncraises(s_exc.BadStormSyntax,
                                   core.addTrigger('node:add', ' | | badstorm ', form='teststr'))
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('node:add', 'testint=4'))
            await self.asyncraises(s_exc.BadOptValu,
                                   core.addTrigger('node:add', 'testint=4', form='teststr', tag='foo'))
            await self.asyncraises(s_exc.BadOptValu,
                                   core.addTrigger('prop:set', 'testint=4', form='teststr', prop='foo'))
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('tag:add', 'testint=4'))
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('prop:set', 'testint=4'))
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('tag:add', 'testint=4', tag='foo*'))
            await self.asyncraises(s_exc.BadOptValu, core.addTrigger('tag:add', 'testint=4', tag='*foo'))

            # Trigger list
            triglist = await core.listTriggers()
            self.len(7, triglist)

            # Delete trigger
            buid = [b for b, r in triglist if r['cond'] == 'prop:set'][0]
            await s_common.aspin(await core.eval('sudo | testint=6 | delnode'))
            await core.delTrigger(buid)
            # Make sure it didn't fire
            await s_common.aspin(await core.eval('sudo | [ testtype10=3 :intprop=25 ]'))
            await self.agenlen(0, await core.eval('testint=6'))

            # Mod trigger
            buid = [b for b, r in triglist if r['cond'] == 'tag:add' and r.get('form') == 'teststr'][0]
            await core.updateTrigger(buid, 'sudo | [ testint=42 ]')
            await s_common.aspin(await core.eval('sudo | [ teststr=foo4 +#bartag ]'))
            await self.agenlen(1, await core.eval('testint=42'))

            auth_enabled = True
            try:
                await core.addAuthUser('fred')
                await core.setUserPasswd('fred', 'fred')
            except Exception:
                auth_enabled = False

        if auth_enabled:
            pconf = {'user': 'fred', 'passwd': 'fred'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:

                # Trigger list other user
                self.len(0 if auth_enabled else 6, await core.listTriggers())

                # Delete trigger auth failure
                await self.asyncraises(s_exc.AuthDeny, core.delTrigger(buid))

                # Mod trigger auth failure
                await self.asyncraises(s_exc.AuthDeny, core.updateTrigger(buid, '[ teststr=44 ]'))
