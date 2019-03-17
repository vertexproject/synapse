import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils

class TrigTest(s_t_utils.SynTest):

    async def test_trigger_recursion(self):
        async with self.getTestCoreAndProxy() as (realcore, core):
            await core.addTrigger('node:add', '[ test:guid="*" ]', info={'form': 'test:guid'})
            await s_common.aspin(core.eval('[ test:guid="*" ]'))

    async def test_modification_persistence(self):

        with self.getTestDir() as fdir:

            async with self.getTestCore(dirn=fdir) as core:
                rootiden = core.auth.getUserByName('root').iden
                core.triggers.add('root', 'node:add', '[inet:user=1] | testcmd', info={'form': 'inet:ipv4'})
                triggers = core.triggers.list()
                self.eq(triggers[0][1].get('storm'), '[inet:user=1] | testcmd')
                iden = triggers[0][0]
                core.triggers.mod(iden, '[inet:user=2 .test:univ=4] | testcmd')
                triggers = core.triggers.list()
                self.eq(triggers[0][1].get('storm'), '[inet:user=2 .test:univ=4] | testcmd')

                # Sad case
                self.raises(s_exc.BadSyntax, core.triggers.mod, iden, ' | | badstorm ')
                self.raises(s_exc.NoSuchIden, core.triggers.mod, 'deadb33f', 'inet:user')

                # Manually store a v0 trigger
                ruledict = {'ver': 0, 'cond': 'node:add', 'form': 'inet:ipv4', 'user': 'root', 'storm': 'testcmd'}
                iden = b'\xff' * 16
                core.slab.put(iden, s_msgpack.en(ruledict), db=core.triggers.trigdb)

            async with self.getTestCore(dirn=fdir) as core:
                triggers = core.triggers.list()
                self.len(2, triggers)
                self.eq(triggers[0][1].get('storm'), '[inet:user=2 .test:univ=4] | testcmd')

                # Verify that the v0 trigger was migrated correctly
                iden2, trig2 = triggers[1]
                self.eq(iden2, 'ff' * 16)
                self.eq(trig2['useriden'], rootiden)
                self.eq(trig2['ver'], 1)
                self.eq(trig2['storm'], 'testcmd')

    async def test_trigger_basics(self):

        async with self.getTestCore() as real:

            async with real.getLocalProxy() as core:

                # node:add case
                await core.addTrigger('node:add', '[ test:int=1 ]', info={'form': 'test:str'})
                await s_common.aspin(core.eval('[ test:str=foo ]'))
                await self.agenlen(1, core.eval('test:int'))

                # node:del case
                await core.addTrigger('node:del', '[ test:int=2 ]', info={'form': 'test:str'})
                await s_common.aspin(core.eval('test:str=foo | delnode'))
                await self.agenlen(2, core.eval('test:int'))

                # tag:add case
                await core.addTrigger('tag:add', '[ test:int=3 ]', info={'tag': 'footag'})
                await s_common.aspin(core.eval('[ test:str=foo +#footag ]'))
                await self.agenlen(3, core.eval('test:int'))

                # tag:add globbing and storm var
                await core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={'tag': 'a.*.c'})
                await s_common.aspin(core.eval('[ test:str=foo +#a.b ]'))
                await s_common.aspin(core.eval('[ test:str=foo +#a.b.c ]'))
                await s_common.aspin(core.eval('[ test:str=foo +#a.b.ccc ]'))
                await self.agenlen(1, core.eval('#count'))
                await self.agenlen(1, core.eval('test:str=a.b.c'))

                await core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={'tag': 'foo.**.baz'})
                await s_common.aspin(core.eval('[ test:str=foo +#foo.1.2.3.baz ]'))
                await self.agenlen(1, core.eval('test:str=foo.1.2.3.baz'))

                # tag:del case
                await core.addTrigger('tag:del', '[ test:int=4 ]', info={'tag': 'footag'})
                await s_common.aspin(core.eval('test:str=foo [ -#footag ]'))
                await self.agenlen(1, core.eval('test:int=4'))

                # Form/tag add
                await core.addTrigger('tag:add', '[ test:int=5 ]', info={'tag': 'bartag', 'form': 'test:str'})
                await s_common.aspin(core.eval('[ test:str=foo +#bartag ]'))
                await self.agenlen(1, core.eval('test:int=5'))

                # Wrong form/right tag add doesn't fire
                await s_common.aspin(core.eval('test:int=5 | delnode'))
                await self.agenlen(0, core.eval('test:int=5'))
                await s_common.aspin(core.eval('[ test:auto=1 +#bartag ]'))
                await self.agenlen(0, core.eval('test:int=5'))

                # Right form/wrong tag add doesn't fire
                await s_common.aspin(core.eval('[ test:str=bar +#footag ]'))
                await self.agenlen(0, core.eval('test:int=5'))

                # Prop set
                await core.addTrigger('prop:set', '[ test:int=6 ]', info={'prop': 'test:type10:intprop'})
                await s_common.aspin(core.eval('[ test:type10=1 ]'))
                await self.agenlen(1, core.eval('test:int=6'))  # Triggered by default value setting
                await s_common.aspin(core.eval('[ test:type10=1 :intprop=25 ]'))
                await self.agenlen(1, core.eval('test:int=6'))

                # Test re-setting doesn't fire
                await s_common.aspin(core.eval('test:int=6 | delnode'))
                await s_common.aspin(core.eval('[ test:type10=1 :intprop=25 ]'))
                await self.agenlen(0, core.eval('test:int=6'))

                # Prop set univ
                await core.addTrigger('prop:set', '[ test:int=7 ]', info={'prop': '.test:univ'})
                await s_common.aspin(core.eval('[ test:type10=1 .test:univ=1 ]'))
                await self.agenlen(1, core.eval('test:int=7'))

                # Prop set form specific univ
                await core.addTrigger('prop:set', '[ test:int=8 ]', info={'prop': 'test:str.test:univ'})
                await s_common.aspin(core.eval('[ test:str=beep .test:univ=1 ]'))
                await self.agenlen(1, core.eval('test:int=8'))

                # Bad trigger parms
                await self.asyncraises(s_exc.BadOptValu, core.addTrigger('nocond', 'test:int=4',
                                                                         info={'form': 'test:str'}))
                await self.asyncraises(s_exc.BadSyntax,
                                       core.addTrigger('node:add', ' | | badstorm ', info={'form': 'test:str'}))
                await self.asyncraises(s_exc.BadOptValu,
                                       core.addTrigger('node:add', 'test:int=4', info={'form': 'test:str', 'tag': 'foo'}))
                await self.asyncraises(s_exc.BadOptValu,
                                       core.addTrigger('prop:set', 'test:int=4',
                                                       info={'form': 'test:str', 'prop': 'foo'}))
                await self.asyncraises(s_exc.BadOptValu,
                                       core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={}))
                await self.asyncraises(s_exc.BadOptValu, core.addTrigger('tag:add', '[ +#count test:str=$tag ]',
                                                                         info={'tag': 'foo', 'prop': 'test:str'}))
                # bad tagmatch
                await self.asyncraises(s_exc.BadTag,
                                       core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={'tag': 'foo&baz'}))

                # Trigger list
                triglist = await core.listTriggers()
                self.len(10, triglist)

                # Delete trigger
                buid = [b for b, r in triglist if r['cond'] == 'prop:set'][0]
                await s_common.aspin(core.eval('test:int=6 | delnode'))
                await core.delTrigger(buid)
                # Make sure it didn't fire
                await s_common.aspin(core.eval('[ test:type10=3 :intprop=25 ]'))
                await self.agenlen(0, core.eval('test:int=6'))

                await self.asyncraises(s_exc.NoSuchIden, core.delTrigger(b'badbuid'))

                # Mod trigger
                buid = [b for b, r in triglist if r['cond'] == 'tag:add' and r.get('form') == 'test:str'][0]
                buid2 = [b for b, r in triglist if r['cond'] == 'tag:add' and r.get('form') is None][0]
                await core.updateTrigger(buid, '[ test:int=42 ]')
                await s_common.aspin(core.eval('[ test:str=foo4 +#bartag ]'))
                await self.agenlen(1, core.eval('test:int=42'))

                # Delete a tag:add
                await core.delTrigger(buid2)

                await core.addAuthUser('fred')
                await core.setUserPasswd('fred', 'fred')

                url = real.getLocalUrl()

                async with await s_telepath.openurl(url, user='fred') as fred:

                    # Trigger list other user
                    self.len(0, await fred.listTriggers())

                    # Delete trigger auth failure
                    await self.asyncraises(s_exc.AuthDeny, fred.delTrigger(buid))

                    # Mod trigger auth failure
                    await self.asyncraises(s_exc.AuthDeny, fred.updateTrigger(buid, '[ test:str=44 ]'))

    async def test_trigger_delete(self):

        async with self.getTestCore() as core:
            rootiden = core.auth.getUserByName('root').iden

            iden0 = core.triggers.add(rootiden, 'node:add', '[test:str=add]', {'form': 'test:guid'})
            iden1 = core.triggers.add(rootiden, 'node:del', '[test:str=del]', {'form': 'test:guid'})
            iden2 = core.triggers.add(rootiden, 'prop:set', '[test:str=set]', {'prop': 'test:guid:tick'})

            await core.eval('[test:guid="*" :tick=2015] | delnode').list()
            self.len(3, await core.eval('test:str').list())

            core.triggers.delete(iden0)
            core.triggers.delete(iden1)
            core.triggers.delete(iden2)

            await core.eval('test:str | delnode').list()
            await core.eval('[test:guid="*" :tick=2015] | delnode').list()

            self.len(0, await core.eval('test:str').list())

    async def test_trigger_tag_globs(self):

        async with self.getTestCore() as core:

            rootiden = core.auth.getUserByName('root').iden
            iden0 = core.triggers.add(rootiden, 'tag:add', '[ +#count0 ]', {'tag': 'foo.*.bar'})
            iden1 = core.triggers.add(rootiden, 'tag:del', '[ +#count1 ]', {'tag': 'baz.*.faz'})

            await core.eval('[ test:guid="*" +#foo.asdf.bar ]').list()
            await core.eval('[ test:guid="*" +#baz.asdf.faz ]').list()
            await core.eval('#baz.asdf.faz [ -#baz.asdf.faz ]').list()

            self.len(1, await core.eval('#count0').list())
            self.len(1, await core.eval('#count1').list())

            core.triggers.delete(iden0)
            core.triggers.delete(iden1)

            await core.eval('test:guid | delnode').list()

            await core.eval('[ test:guid="*" +#foo.asdf.bar ]').list()
            await core.eval('[ test:guid="*" +#baz.asdf.faz ]').list()
            await core.eval('#baz.asdf.faz [ -#baz.asdf.faz ]').list()

            self.len(0, await core.eval('#count0').list())
            self.len(0, await core.eval('#count1').list())
