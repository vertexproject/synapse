import os
import json
import asyncio
import synapse.exc as s_exc
import synapse.common as s_common

from synapse.common import aspin

import synapse.cortex as s_cortex
import synapse.telepath as s_telepath
import synapse.tests.utils as s_t_utils
import synapse.tools.backup as s_tools_backup

class TrigTest(s_t_utils.SynTest):

    async def test_trigger_async(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                await core.stormlist('trigger.add node:add --async --form inet:ipv4 --query { [+#foo] $lib.queue.gen(foo).put($node.iden()) }')

                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
                self.none(nodes[0].tags.get('foo'))

                msgs = await core.stormlist('trigger.list')
                self.stormIsInPrint('True   True   node:add  inet:ipv4', msgs)

                self.nn(await core.callStorm('return($lib.queue.gen(foo).pop(wait=$lib.true))'))
                nodes = await core.nodes('inet:ipv4=1.2.3.4')
                self.nn(nodes[0].tags.get('foo'))

                # test dynamically updating the trigger async to off
                await core.stormlist('$lib.view.get().triggers.0.set(async, $lib.false)')
                nodes = await core.nodes('[ inet:ipv4=5.5.5.5 ]')
                self.nn(nodes[0].tags.get('foo'))
                self.nn(await core.callStorm('return($lib.queue.gen(foo).pop(wait=$lib.true))'))

                # reset the trigger to async...
                await core.stormlist('$lib.view.get().triggers.0.set(async, $lib.true)')

                # kill off the async consumer and queue up some requests
                # to test persistance and proper resuming...
                await core.view.finiTrigTask()

                trigiden = await core.callStorm('return($lib.view.get().triggers.0.iden)')
                self.nn(trigiden)

                await core.view.addTrigQueue({'buid': s_common.buid(), 'trig': trigiden})
                await core.view.addTrigQueue({'buid': s_common.buid(), 'trig': s_common.guid()})

                nodes = await core.nodes('[ inet:ipv4=9.9.9.9 ]')
                self.none(nodes[0].tags.get('foo'))
                self.none(await core.callStorm('return($lib.queue.gen(foo).pop())'))

            async with self.getTestCore(dirn=dirn) as core:

                self.nn(await core.callStorm('return($lib.queue.gen(foo).pop(wait=$lib.true))'))
                nodes = await core.nodes('inet:ipv4=9.9.9.9')
                self.nn(nodes[0].tags.get('foo'))
                self.none(core.view.trigqueue.last())

                # lets fork a view and hamstring it's trigger queue and make sure we can't merge
                viewiden = await core.callStorm('return($lib.view.get().fork().iden)')

                view = core.getView(viewiden)
                await view.finiTrigTask()

                opts = {'view': viewiden}
                await core.stormlist('trigger.add node:add --async --form inet:ipv4 --query { [+#foo] $lib.queue.gen(foo).put($node.iden()) }', opts=opts)
                nodes = await core.nodes('[ inet:ipv4=123.123.123.123 ]', opts=opts)

                with self.raises(s_exc.CantMergeView):
                    await core.nodes('$lib.view.get().merge()', opts=opts)

                await core.nodes('$lib.view.get().merge(force=$lib.true)', opts=opts)
                await core.nodes('$lib.view.del($view)', opts={'vars': {'view': viewiden}})

                self.false(os.path.isdir(view.dirn))

    async def test_trigger_async_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.stormlist('trigger.add node:add --async --form inet:ipv4 --query { [+#foo] $lib.queue.gen(foo).put($node.iden()) }')

                await core00.view.finiTrigTask()
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                url = core00.getLocalUrl()
                core01conf = {'mirror': url}

                async with await s_cortex.Cortex.anit(dirn=path01, conf=core01conf) as core01:
                    # ensure sync by forcing node construction
                    await core01.nodes('[ou:org=*]')
                    self.nn(await core00.callStorm('return($lib.queue.gen(foo).pop(wait=$lib.true))'))
                    self.none(await core00.callStorm('return($lib.queue.gen(foo).pop())'))

                    await core01.nodes('[inet:ipv4=8.8.8.8]')
                    self.nn(await core01.callStorm('return($lib.queue.gen(foo).pop(wait=$lib.true))'))
                    self.none(await core00.callStorm('return($lib.queue.gen(foo).pop())'))
                    self.none(await core01.callStorm('return($lib.queue.gen(foo).pop())'))

                    self.nn(core00.view.trigtask)
                    self.none(core01.view.trigtask)

    async def test_trigger_recursion(self):
        async with self.getTestCore() as core:
            tdef = {'cond': 'node:add', 'form': 'test:guid', 'storm': '[ test:guid="*" ]'}
            await core.view.addTrigger(tdef)
            await self.asyncraises(s_exc.RecursionLimitHit, core.nodes('[ test:guid="*" ]'))

    async def test_modification_persistence(self):

        with self.getTestDir() as fdir:

            async with self.getTestCore(dirn=fdir) as core:
                iden = s_common.guid()
                tdef = {'cond': 'node:add', 'form': 'inet:ipv4', 'storm': '[inet:user=1] | testcmd'}
                await core.view.addTrigger(tdef)

                triggers = await core.view.listTriggers()
                self.eq(triggers[0][1].tdef['storm'], '[inet:user=1] | testcmd')

                iden = triggers[0][0]
                await core.view.setTriggerInfo(iden, 'storm', '[inet:user=2 .test:univ=4] | testcmd')
                triggers = await core.view.listTriggers()
                self.eq(triggers[0][1].tdef['storm'], '[inet:user=2 .test:univ=4] | testcmd')

                # Sad cases
                await self.asyncraises(s_exc.BadSyntax, core.view.setTriggerInfo(iden, 'storm', ' | | badstorm '))
                await self.asyncraises(s_exc.NoSuchIden, core.view.setTriggerInfo('deadb33f', 'storm', 'inet:user'))

    async def test_trigger_basics(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            view = core.view

            # node:add case
            q = '''$s=$lib.str.format("f={f} v={v}", f=$auto.opts.form, v=$auto.opts.valu) $lib.log.info($s)
                    [ test:guid="*" +#nodeadd]'''
            tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': q}
            await view.addTrigger(tdef)
            with self.getAsyncLoggerStream('synapse.storm.log', 'f=') as stream:
                await core.nodes('[ test:str=foo ]')
                self.true(await stream.wait(6))
            self.eq(stream.getvalue().strip(), 'f=test:str v=foo')
            self.len(1, await core.nodes('test:guid#nodeadd'))

            # node:del case
            tdef = {'cond': 'node:del', 'storm': '[ test:guid="*" +#nodedel ]', 'form': 'test:str'}
            await view.addTrigger(tdef)
            await core.nodes('test:str=foo | delnode')
            self.len(1, await core.nodes('test:guid#nodedel'))

            # tag:add case
            tdef = {'cond': 'tag:add', 'storm': '[ test:guid="*" +#tagadd]', 'tag': 'footag'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:str=foo +#footag ]')
            self.len(1, await core.nodes('test:guid#tagadd'))

            # tag:add globbing and storm var
            tdef = {'cond': 'tag:add',
                    'storm': '$lib.log.info($auto.opts.tag) [ +#count test:str=$tag ]',
                    'tag': 'a.*.c'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:str=foo +#a.b ]')
            with self.getAsyncLoggerStream('synapse.storm.log', 'a.b.c') as stream:
                await core.nodes('[ test:str=foo +#a.b.c ]')
                self.true(await stream.wait(6))
            self.true(stream.getvalue().strip().startswith('a.b.c\n'))
            await core.nodes('[ test:str=foo +#a.b.ccc ]')
            self.len(1, await core.nodes('#count'))
            self.len(1, await core.nodes('test:str=a.b.c'))

            tdef = {'cond': 'tag:add', 'storm': '[ +#count test:str=$tag ]', 'tag': 'foo.**.baz'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:str=foo +#foo.1.2.3.baz ]')
            self.len(1, await core.nodes('test:str=foo.1.2.3.baz'))

            # tag:del case
            tdef = {'cond': 'tag:del', 'storm': '[ test:guid="*" +#tagdel ]', 'tag': 'footag'}
            await view.addTrigger(tdef)
            await core.nodes('test:str=foo [ -#footag ]')
            self.len(1, await core.nodes('test:guid#tagdel'))

            # Form/tag add
            tdef = {'cond': 'tag:add', 'storm': '[ test:guid="*" +#formtagadd]', 'tag': 'bartag',
                    'form': 'test:str'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:str=foo +#bartag ]')
            self.len(1, await core.nodes('test:guid#formtagadd'))

            # Wrong form/right tag add doesn't fire
            await core.nodes('test:int=5 | delnode')
            self.len(0, await core.nodes('test:int=5'))
            await core.nodes('[ test:auto=1 +#bartag ]')
            self.len(0, await core.nodes('test:int=5'))

            # Right form/wrong tag add doesn't fire
            await core.nodes('[ test:str=bar +#footag ]')
            self.len(0, await core.nodes('test:int=5'))

            # Prop set
            q = '''$s=$lib.str.format("pf={f} pn={n}", f=$auto.opts.propfull, n=$auto.opts.propname) $lib.log.info($s)
            [ test:guid="*" +#propset ]'''
            tdef = {'cond': 'prop:set',
                    'storm': q,
                    'prop': 'test:type10:intprop'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:type10=1 ]')
            with self.getAsyncLoggerStream('synapse.storm.log', 'pf=') as stream:
                await core.nodes('[ test:type10=1 :intprop=25 ]')
                self.true(await stream.wait(6))
            buf = stream.getvalue().strip()
            self.eq(buf, 'pf=test:type10:intprop pn=intprop')
            self.len(1, await core.nodes('test:guid#propset'))

            # Test re-setting doesn't fire
            await core.nodes('test:int=6 | delnode')
            await core.nodes('[ test:type10=1 :intprop=25 ]')
            self.len(0, await core.nodes('test:int=6'))

            # Prop set univ
            tdef = {'cond': 'prop:set', 'storm': '[ test:guid="*" +#propsetuniv ]', 'prop': '.test:univ'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:type10=1 .test:univ=1 ]')
            self.len(1, await core.nodes('test:guid#propsetuniv'))

            # Prop set form specific univ
            tdef = {'cond': 'prop:set', 'storm': '[ test:guid="*" +#propsetuniv2 ]', 'prop': 'test:str.test:univ'}
            await view.addTrigger(tdef)
            await core.nodes('[ test:str=beep .test:univ=1 ]')
            self.len(1, await core.nodes('test:guid#propsetuniv2'))

            # Add trigger with iden
            iden = s_common.guid()
            tdef0 = {'cond': 'node:add', 'storm': '[ +#withiden ]', 'form': 'test:int', 'iden': iden}
            pdef0 = await view.addTrigger(tdef0)
            self.nn(await view.getTrigger(iden))
            await core.nodes('[ test:int=77 ]')
            self.len(1, await core.nodes('test:int#withiden'))

            # iden embedded in vars
            q = '+test:str~=log $s=$lib.str.format("test {t} {i}", t=$auto.type, i=$auto.iden) $lib.log.info($s, ({"iden": $auto.iden}))'
            tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': q}
            await view.addTrigger(tdef)
            with self.getStructuredAsyncLoggerStream('synapse.storm.log', 'test trigger') as stream:
                await core.nodes('[ test:str=logit ]')
                self.true(await stream.wait(6))
            buf = stream.getvalue()
            mesg = json.loads(buf.split('\n')[-2])
            self.eq(mesg['message'], f'test trigger {tdef.get("iden")}')
            self.eq(mesg['iden'], tdef.get('iden'))

            # Attempting to add trigger with existing iden raises
            with self.raises(s_exc.DupIden):
                tdef = {'cond': 'node:add', 'storm': '[ +#dupiden ]', 'form': 'test:int', 'iden': iden}
                await view.addTrigger(tdef)
            self.eq(pdef0.get('storm'), (await view.getTrigger(iden)).tdef.get('storm'))

            # Bad trigger parms
            with self.raises(s_exc.SchemaViolation):
                await view.addTrigger({'cond': 'nocond', 'storm': 'test:int=4', 'form': 'test:str'})

            with self.raises(s_exc.BadSyntax):
                await view.addTrigger({'cond': 'node:add', 'storm': ' | | badstorm ', 'form': 'test:str'})

            with self.raises(s_exc.BadOptValu):
                await view.addTrigger({'cond': 'node:add', 'storm': 'test:int=4', 'form': 'test:str', 'tag': 'foo'})

            with self.raises(s_exc.SchemaViolation):
                await view.addTrigger({'cond': 'prop:set', 'storm': 'test:int=4', 'form': 'test:str', 'prop': 'foo'})

            with self.raises(s_exc.SchemaViolation):
                await view.addTrigger({'cond': 'tag:add', 'storm': '[ +#count test:str=$tag ]'})

            with self.raises(s_exc.BadOptValu):
                tdef = {'cond': 'tag:add', 'storm': '[ +#count test:str=$tag ]', 'tag': 'foo', 'prop': 'test:str'}
                await view.addTrigger(tdef)

            with self.raises(s_exc.SchemaViolation):
                await view.addTrigger({'cond': 'node:add', 'storm': 'test:int=4', 'form': 'test:str', 'iden': 'foo'})

            # bad tagmatch
            with self.raises(s_exc.SchemaViolation):
                await view.addTrigger({'cond': 'tag:add', 'storm': '[ +#count test:str=$tag ]', 'tag': 'foo&baz'})

            # Trigger list
            triglist = await view.listTriggers()
            self.len(12, triglist)

            # Delete not a trigger
            await self.asyncraises(s_exc.NoSuchIden, view.delTrigger('foo'))

            # Delete trigger
            iden = [iden for iden, r in triglist if r.tdef['cond'] == 'prop:set'][0]
            await core.nodes('test:int=6 | delnode')
            await view.delTrigger(iden)

            # The deleted trigger shall not fire
            await core.nodes('[ test:type10=3 :intprop=25 ]')
            self.len(0, await core.nodes('test:int=6'))

            await self.asyncraises(s_exc.NoSuchIden, view.delTrigger(b'badiden'))

            # Mod trigger

            iden = [iden for iden, r in triglist if r.tdef['cond'] == 'tag:add' and r.tdef.get('form') == 'test:str'][0]

            await view.setTriggerInfo(iden, 'storm', '[ test:int=42 ]')
            await core.nodes('[ test:str=foo4 +#bartag ]')
            self.len(1, await core.nodes('test:int=42'))

            # Delete a tag:add
            iden2 = [iden for iden, r in triglist if r.tdef['cond'] == 'tag:add' and r.tdef.get('form') is None][0]
            await view.delTrigger(iden2)

            # A rando user can't manipulate triggers

            user = await core.auth.addUser('fred')
            await user.setPasswd('fred')

            url = core.getLocalUrl()

            async with await s_telepath.openurl(url, user='fred') as fred:
                # Trigger list other user
                self.len(0, await fred.callStorm('return ($lib.trigger.list())'))

                with self.raises(s_exc.AuthDeny):
                    tdef = {'cond': 'node:add', 'storm': '[ test:int=1 ]', 'form': 'test:str'}
                    opts = {'vars': {'tdef': tdef}}
                    q = 'return ($lib.trigger.add($tdef))'
                    await fred.callStorm(q, opts=opts)

                # Delete trigger auth failure
                await self.asyncraises(s_exc.StormRuntimeError, fred.callStorm(f'$lib.trigger.del({iden})'))

                # Mod trigger auth failure
                opts = {'vars': {'iden': iden}}
                await self.asyncraises(s_exc.StormRuntimeError,
                                       fred.callStorm('$lib.trigger.mod($iden, "{#foo}")', opts=opts))

            # additional NoSuchIden failures
            await self.asyncraises(s_exc.NoSuchIden, view.getTrigger('newp'))
            await self.asyncraises(s_exc.NoSuchIden, view.delTrigger('newp'))
            await self.asyncraises(s_exc.NoSuchIden, view.setTriggerInfo('newp', 'enabled', True))

    async def test_trigger_delete(self):

        async with self.getTestCore() as core:

            tdef0 = {'cond': 'node:add', 'form': 'test:guid', 'storm': '[test:str=add]'}
            tdef1 = {'cond': 'node:del', 'form': 'test:guid', 'storm': '[test:str=del]'}
            tdef2 = {'cond': 'prop:set', 'prop': 'test:guid:tick', 'storm': '[test:str=set]'}

            tdef0 = await core.view.addTrigger(tdef0)
            tdef1 = await core.view.addTrigger(tdef1)
            tdef2 = await core.view.addTrigger(tdef2)

            await core.nodes('[test:guid="*" :tick=2015] | delnode')
            self.len(3, await core.nodes('test:str'))

            await core.view.delTrigger(tdef0.get('iden'))
            await core.view.delTrigger(tdef1.get('iden'))
            await core.view.delTrigger(tdef2.get('iden'))

            await core.nodes('test:str | delnode')
            await core.nodes('[test:guid="*" :tick=2015] | delnode')

            self.len(0, await core.nodes('test:str'))

    async def test_trigger_tag_globs(self):

        async with self.getTestCore() as core:

            root = await core.auth.getUserByName('root')

            tdef = {'iden': '1', 'user': root.iden, 'cond': 'tag:add', 'storm': '$lib.queue.get(foo).put(count0)',
                    'tag': 'foo.*.bar', 'enabled': True}
            trig1 = await core.view.triggers.load(tdef)

            tdef = {'iden': '2', 'user': root.iden, 'cond': 'tag:del', 'storm': '$lib.queue.get(foo).put(count1)',
                    'tag': 'baz.*.faz', 'form': 'test:guid', 'enabled': True}
            trig2 = await core.view.triggers.load(tdef)

            await core.nodes('$lib.queue.add(foo)')

            async def popNextFoo():
                return await core.callStorm('''
                    return ($lib.queue.get(foo).pop().index(1))
                ''')

            await core.nodes('[ test:guid="*" +#foo.asdf.bar ]')
            await core.nodes('[ test:guid="*" +#baz.asdf.faz ]')
            await core.nodes('#baz.asdf.faz [ -#baz.asdf.faz ]')

            self.eq('count0', await popNextFoo())
            self.eq('count1', await popNextFoo())

            core.view.triggers.pop(trig1.iden)
            core.view.triggers.pop(trig2.iden)

            await core.nodes('test:guid | delnode')

            # Triggers don't fire after they've been deleted

            await core.nodes('[ test:guid="*" +#foo.asdf.bar ]')
            await core.nodes('[ test:guid="*" +#baz.asdf.faz ]')

            await core.nodes('#baz.asdf.faz [ -#baz.asdf.faz ]')

            self.eq(0, await core.callStorm('return ($lib.queue.get(foo).size())'))

    async def test_trigger_running_perms(self):
        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')

            # Verify that triggers are run as user
            tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': '[ test:guid="*" +#nodeadd]', 'user': visi.iden}
            await core.view.addTrigger(tdef)
            await core.nodes('[ test:str=foo ]')
            self.len(0, await core.nodes('test:guid#nodeadd'))

            await visi.addRule((True, ('node', 'tag', 'add')))
            await visi.addRule((True, ('node', 'add')))
            await core.nodes('[ test:str=foo2 ]')
            self.len(1, await core.nodes('test:guid#nodeadd'))

            # If the user is locked, the trigger doesn't run
            await visi.setLocked(True)
            await core.nodes('[ test:str=foo3 ]')
            self.len(1, await core.nodes('test:guid#nodeadd'))

    async def test_trigger_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            newb = await core.auth.addUser('newb')

            await visi.addRule((True, ('node', 'tag', 'add', 'foo')))

            async with core.getLocalProxy(user='visi') as proxy:

                with self.raises(s_exc.AuthDeny):
                    tdef = {'cond': 'node:add', 'form': 'inet:ipv4', 'storm': '[ +#foo ]'}
                    await proxy.callStorm('return ($lib.trigger.add($tdef).get(iden))', opts={'vars': {'tdef': tdef}})

                await visi.addRule((True, ('trigger', 'add')))

                tdef = {'cond': 'node:add', 'form': 'inet:ipv4', 'storm': '[ +#foo ]'}
                opts = {'vars': {'tdef': tdef}}
                trig = await proxy.callStorm('return ($lib.trigger.add($tdef))', opts=opts)
                iden0 = trig['iden']

                iden1 = s_common.guid()
                tdef = {'cond': 'node:add', 'form': 'inet:ipv6', 'storm': '[ +#foo ]', 'iden': iden1}
                opts = {'vars': {'tdef': tdef}}
                trig = await proxy.callStorm('return ($lib.trigger.add($tdef))', opts=opts)

                nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
                self.nn(nodes[0].tags.get('foo'))

                await aspin(proxy.eval('$lib.trigger.del($iden)', opts={'vars': {'iden': iden1}}))

            trigs = await core.view.listTriggers()
            trigiden = trigs[0][0]
            self.eq(trigiden, iden0)

            async with core.getLocalProxy(user='newb') as proxy:

                await self.agenlen(1, proxy.eval('syn:trigger'))

                await newb.addRule((True, ('trigger', 'get')))
                with self.raises(s_exc.AuthDeny):
                    await proxy.eval('$lib.trigger.del($iden)', opts={'vars': {'iden': trigs[0][0]}}).list()

                await self.agenlen(1, proxy.eval('syn:trigger'))

                with self.raises(s_exc.AuthDeny):
                    opts = {'vars': {'iden': trigiden}}
                    await proxy.eval('$lib.trigger.get($iden).set(enabled, $(0))', opts=opts).list()

                await newb.addRule((True, ('trigger', 'set')))
                opts = {'vars': {'iden': trigiden}}
                await aspin(proxy.eval('$lib.trigger.get($iden).set(enabled, $(0))', opts=opts))

                await newb.addRule((True, ('trigger', 'del')))
                await aspin(proxy.eval('$lib.trigger.del($iden)', opts={'vars': {'iden': trigiden}}))

            # If the trigger owner loses read perms on the trigger's view, it doesn't fire.
            # Regression test:  it also doesn't stop the pipeline/raise an exception
            await visi.addRule((False, ('view', 'read')), gateiden=core.view.iden)
            await newb.addRule((True, ('node', 'add')))
            async with core.getLocalProxy(user='newb') as proxy:
                self.eq(0, await proxy.count('[inet:ipv4 = 99] +#foo'))

    async def test_trigger_runts(self):

        async with self.getTestCore() as core:

            tdef = await core.view.addTrigger({
                'cond': 'node:add',
                'form': 'test:str',
                'storm': '[ test:int=1 ]',
            })
            iden = tdef['iden']

            nodes = await core.nodes('syn:trigger')
            self.len(1, nodes)
            self.eq(nodes[0].get('doc'), '')

            nodes = await core.nodes(f'syn:trigger={iden} [ :doc="hehe haha" :name=visitrig ]')
            self.eq(nodes[0].get('doc'), 'hehe haha')
            self.eq(nodes[0].get('name'), 'visitrig')

            nodes = await core.nodes(f'syn:trigger={iden}')
            self.eq(nodes[0].get('doc'), 'hehe haha')
            self.eq(nodes[0].get('name'), 'visitrig')
