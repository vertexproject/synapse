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
                core.view.triggers.add('root', 'node:add', '[inet:user=1] | testcmd', info={'form': 'inet:ipv4'})
                triggers = core.view.triggers.list()
                self.eq(triggers[0][1].storm, '[inet:user=1] | testcmd')
                iden = triggers[0][0]
                core.view.triggers.mod(iden, '[inet:user=2 .test:univ=4] | testcmd')
                triggers = core.view.triggers.list()
                self.eq(triggers[0][1].storm, '[inet:user=2 .test:univ=4] | testcmd')

                # Sad case
                self.raises(s_exc.BadSyntax, core.view.triggers.mod, iden, ' | | badstorm ')
                self.raises(s_exc.NoSuchIden, core.view.triggers.mod, 'deadb33f', 'inet:user')

                # Manually store a v0 trigger
                ruledict = {'ver': 0, 'cond': 'node:add', 'form': 'inet:ipv4', 'user': 'root', 'storm': 'testcmd'}
                v0iden = b'\xff' * 16
                core.slab.put(v0iden, s_msgpack.en(ruledict), db=core.trigstor.trigdb)

            async with self.getTestCore(dirn=fdir) as core:
                triggers = core.view.triggers.list()
                self.len(2, triggers)
                self.eq(triggers[0][1].storm, '[inet:user=2 .test:univ=4] | testcmd')

                # Verify that the v0 trigger was migrated correctly
                iden2, trig2 = triggers[1]
                self.eq(iden2, s_common.ehex(v0iden))
                self.eq(trig2.ver, 1)
                self.eq(trig2.storm, 'testcmd')
                self.eq(trig2.useriden, rootiden)

    async def test_view_migration(self):
        '''
        Make sure the trigger's view was migrated from iden=cortex.iden to its own
        '''
        async with self.getRegrCore('0.1.32-trigger') as core:
            triggers = await core.view.listTriggers()
            self.len(1, triggers)
            self.eq(triggers[0][1].viewiden, core.view.iden)

    async def test_trigger_basics(self):

        async with self.getTestCore() as real:

            async with real.getLocalProxy() as core:

                # node:add case
                waiter = real.waiter(1, 'core:trigger:action')
                await core.addTrigger('node:add', '[ test:int=1 ]', info={'form': 'test:str'})
                await s_common.aspin(core.eval('[ test:str=foo ]'))
                await self.agenlen(1, core.eval('test:int'))
                evnts = await waiter.wait(1)
                self.eq(evnts[0][1].get('action'), 'add')

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
                with self.raises(s_exc.BadOptValu):
                    await core.addTrigger('nocond', 'test:int=4', info={'form': 'test:str'})

                with self.raises(s_exc.BadSyntax):
                    await core.addTrigger('node:add', ' | | badstorm ', info={'form': 'test:str'})

                with self.raises(s_exc.BadOptValu):
                    await core.addTrigger('node:add', 'test:int=4', info={'form': 'test:str', 'tag': 'foo'})

                with self.raises(s_exc.BadOptValu):
                    await core.addTrigger('prop:set', 'test:int=4', info={'form': 'test:str', 'prop': 'foo'})

                with self.raises(s_exc.BadOptValu):
                    await core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={})

                with self.raises(s_exc.BadOptValu):
                    info = {'tag': 'foo', 'prop': 'test:str'}
                    await core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info=info)
                # bad tagmatch
                with self.raises(s_exc.BadTag):
                    await core.addTrigger('tag:add', '[ +#count test:str=$tag ]', info={'tag': 'foo&baz'})

                # Trigger list
                triglist = await core.listTriggers()
                self.len(10, triglist)

                # Delete trigger
                waiter = real.waiter(1, 'core:trigger:action')
                buid = [b for b, r in triglist if r['cond'] == 'prop:set'][0]
                await s_common.aspin(core.eval('test:int=6 | delnode'))
                await core.delTrigger(buid)
                evnts = await waiter.wait(1)
                self.eq(evnts[0][1].get('action'), 'delete')

                # Make sure it didn't fire
                await s_common.aspin(core.eval('[ test:type10=3 :intprop=25 ]'))
                await self.agenlen(0, core.eval('test:int=6'))

                await self.asyncraises(s_exc.NoSuchIden, core.delTrigger(b'badbuid'))

                # Mod trigger

                buid = [b for b, r in triglist if r['cond'] == 'tag:add' and r.get('form') == 'test:str'][0]

                waiter = real.waiter(1, 'core:trigger:action')
                await core.updateTrigger(buid, '[ test:int=42 ]')
                evnts = await waiter.wait(1)
                self.eq(evnts[0][1].get('action'), 'mod')

                await s_common.aspin(core.eval('[ test:str=foo4 +#bartag ]'))
                await self.agenlen(1, core.eval('test:int=42'))

                # Delete a tag:add
                buid2 = [b for b, r in triglist if r['cond'] == 'tag:add' and r.get('form') is None][0]
                await core.delTrigger(buid2)

                # A rando user can't manipulate triggers

                await core.addAuthUser('fred')
                await core.setUserPasswd('fred', 'fred')

                url = real.getLocalUrl()

                async with await s_telepath.openurl(url, user='fred') as fred:
                    # Trigger list other user
                    self.len(0, await fred.listTriggers())

                    with self.raises(s_exc.AuthDeny):
                        await fred.addTrigger('node:add', '[ test:int=1 ]', info={'form': 'test:str'})

                    # Delete trigger auth failure
                    await self.asyncraises(s_exc.AuthDeny, fred.delTrigger(buid))

                    # Mod trigger auth failure
                    await self.asyncraises(s_exc.AuthDeny, fred.updateTrigger(buid, '[ test:str=44 ]'))

                # additional NoSuchIden failures
                await self.asyncraises(s_exc.NoSuchIden, real.getTrigger('newp'))
                await self.asyncraises(s_exc.NoSuchIden, real.delTrigger('newp'))
                await self.asyncraises(s_exc.NoSuchIden, real.enableTrigger('newp'))
                await self.asyncraises(s_exc.NoSuchIden, real.disableTrigger('newp'))

    async def test_trigger_delete(self):

        async with self.getTestCore() as core:
            rootiden = core.auth.getUserByName('root').iden

            iden0 = core.view.triggers.add(rootiden, 'node:add', '[test:str=add]', {'form': 'test:guid'})
            iden1 = core.view.triggers.add(rootiden, 'node:del', '[test:str=del]', {'form': 'test:guid'})
            iden2 = core.view.triggers.add(rootiden, 'prop:set', '[test:str=set]', {'prop': 'test:guid:tick'})

            await core.eval('[test:guid="*" :tick=2015] | delnode').list()
            self.len(3, await core.eval('test:str').list())

            core.view.triggers.delete(iden0)
            core.view.triggers.delete(iden1)
            core.view.triggers.delete(iden2)

            await core.eval('test:str | delnode').list()
            await core.eval('[test:guid="*" :tick=2015] | delnode').list()

            self.len(0, await core.eval('test:str').list())

    async def test_trigger_tag_globs(self):

        async with self.getTestCore() as core:

            rootiden = core.auth.getUserByName('root').iden
            iden0 = core.view.triggers.add(rootiden, 'tag:add', '[ +#count0 ]', {'tag': 'foo.*.bar'})
            iden1 = core.view.triggers.add(rootiden, 'tag:del', '[ +#count1 ]', {'tag': 'baz.*.faz'})

            await core.eval('[ test:guid="*" +#foo.asdf.bar ]').list()
            await core.eval('[ test:guid="*" +#baz.asdf.faz ]').list()
            await core.eval('#baz.asdf.faz [ -#baz.asdf.faz ]').list()

            self.len(1, await core.eval('#count0').list())
            self.len(1, await core.eval('#count1').list())

            core.view.triggers.delete(iden0)
            core.view.triggers.delete(iden1)

            await core.eval('test:guid | delnode').list()

            await core.eval('[ test:guid="*" +#foo.asdf.bar ]').list()
            await core.eval('[ test:guid="*" +#baz.asdf.faz ]').list()
            await core.eval('#baz.asdf.faz [ -#baz.asdf.faz ]').list()

            self.len(0, await core.eval('#count0').list())
            self.len(0, await core.eval('#count1').list())

    async def test_trigger_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            newb = await core.auth.addUser('newb')

            await visi.addRule((True, ('tag:add', 'foo')))

            async with core.getLocalProxy(user='visi') as proxy:

                with self.raises(s_exc.AuthDeny):
                    await proxy.addTrigger('node:add', '[ +#foo ]', info={'form': 'inet:ipv4'})

                await visi.addRule((True, ('trigger', 'add')))

                trig0 = await proxy.addTrigger('node:add', '[ +#foo ]', info={'form': 'inet:ipv4'})
                trig1 = await proxy.addTrigger('node:add', '[ +#foo ]', info={'form': 'inet:ipv6'})

                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
                self.nn(nodes[0].tags.get('foo'))

                await proxy.delTrigger(trig0)

            async with core.getLocalProxy(user='newb') as proxy:

                with self.raises(s_exc.AuthDeny):
                    await proxy.delTrigger(trig1)

                self.eq(await proxy.listTriggers(), ())
                await newb.addRule((True, ('trigger', 'get')))
                self.len(1, await proxy.listTriggers())

                with self.raises(s_exc.AuthDeny):
                    await proxy.disableTrigger(trig1)
                await newb.addRule((True, ('trigger', 'set')))
                self.none(await proxy.disableTrigger(trig1))

                await newb.addRule((True, ('trigger', 'del')))
                await proxy.delTrigger(trig1)

    async def test_trigger_runts(self):

        async with self.getTestCore() as core:

            iden = await core.addTrigger('node:add', '[ test:int=1 ]', info={'form': 'test:str'})

            nodes = await core.nodes('syn:trigger')
            self.len(1, nodes)
            self.eq(nodes[0].get('doc'), '')

            nodes = await core.nodes(f'syn:trigger={iden} [ :doc="hehe haha" :name=visitrig ]')
            self.eq(nodes[0].get('doc'), 'hehe haha')
            self.eq(nodes[0].get('name'), 'visitrig')

            nodes = await core.nodes(f'syn:trigger={iden}')
            self.eq(nodes[0].get('doc'), 'hehe haha')
            self.eq(nodes[0].get('name'), 'visitrig')
