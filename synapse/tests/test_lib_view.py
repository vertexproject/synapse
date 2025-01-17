import asyncio
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):

    async def test_view_protected(self):
        async with self.getTestCore() as core:
            view = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': view}

            await core.nodes('[ ou:org=* ]', opts=opts)
            await core.nodes('$lib.view.get().set(protected, $lib.true)', opts=opts)

            with self.raises(s_exc.CantMergeView):
                await core.nodes('$lib.view.get().merge()', opts=opts)

            with self.raises(s_exc.CantDelView):
                await core.nodes('$lib.view.del($lib.view.get().iden)', opts=opts)

            await core.nodes('$lib.view.get().set(protected, $lib.false)', opts=opts)
            await core.nodes('$lib.view.get().merge()', opts=opts)

            self.len(1, await core.nodes('ou:org'))

            # mop up some coverage issues
            with self.raises(s_exc.BadOptValu):
                await core.view.setViewInfo('hehe', 10)

        async with self.getTestCore() as core:
            # Delete this block when nomerge is removed
            view = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': view}

            # Setting/getting nomerge should be redirected to protected
            getnomerge = 'return($lib.view.get().get(nomerge))'
            setnomerge = '$lib.view.get().set(nomerge, $valu)'

            getprotected = 'return($lib.view.get().get(protected))'
            setprotected = '$lib.view.get().set(protected, $valu)'

            nomerge = await core.callStorm(getnomerge, opts=opts)
            protected = await core.callStorm(getprotected, opts=opts)
            self.false(nomerge)
            self.false(protected)

            opts['vars'] = {'valu': True}
            await core.callStorm(setnomerge, opts=opts)

            nomerge = await core.callStorm(getnomerge, opts=opts)
            protected = await core.callStorm(getprotected, opts=opts)
            self.true(nomerge)
            self.true(protected)

            opts['vars'] = {'valu': False}
            await core.callStorm(setprotected, opts=opts)

            nomerge = await core.callStorm(getnomerge, opts=opts)
            protected = await core.callStorm(getprotected, opts=opts)
            self.false(nomerge)
            self.false(protected)

    async def test_view_set_parent(self):

        async with self.getTestCore() as core:

            view00 = core.getView()
            view01 = core.getView((await view00.fork())['iden'])

            await view00.nodes('[ inet:fqdn=vertex.link ]')
            await view01.nodes('inet:fqdn=vertex.link [ +#foo ]')

            # one to insert on the bottom
            layr02 = await core.addLayer()
            vdef02 = {'layers': [layr02['iden']]}
            view02 = core.getView((await core.addView(vdef=vdef02))['iden'])
            view03 = await core.callStorm('$view=$lib.view.get($view02).fork() return ( $view.iden )',
                                          opts={'vars': {'view02': view02.iden}})

            # test the storm APIs for setting view parent
            opts = {'vars': {'base': view02.iden, 'fork': view00.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $base)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            # test that merging selected nodes works correctly
            self.len(0, await view02.nodes('inet:fqdn=vertex.link'))
            msgs = await view00.stormlist('inet:fqdn | merge --apply')
            self.len(1, await view02.nodes('inet:fqdn=vertex.link'))
            self.len(0, await view02.nodes('inet:fqdn=vertex.link +#foo'))

            # check that edits made to the new base layer are reflected in forks
            self.len(1, await view02.nodes('inet:fqdn=vertex.link [+#bar]'))
            self.len(1, await view00.nodes('#bar'))
            self.len(1, await view01.nodes('#bar'))

            # setting the parent value the the existing value is okay
            opts = {'vars': {'base': view02.iden, 'fork': view00.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $base)', opts=opts)
            self.stormHasNoWarnErr(msgs)

            # test that the API prevents you from setting view parent that's already set
            opts = {'vars': {'base': view03, 'fork': view00.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $base)', opts=opts)
            self.stormIsInErr('You may not set parent on a view which already has one', msgs)

            opts = {'vars': {'fork': view00.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $lib.guid())', opts=opts)
            self.stormIsInErr('The parent view must already exist', msgs)

            opts = {'vars': {'fork': view00.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $fork)', opts=opts)
            self.stormIsInErr('A view may not have parent set to itself', msgs)

            opts = {'vars': {'fork': view00.iden, 'base': view01.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $base)', opts=opts)
            self.stormIsInErr('Circular dependency of view parents is not supported', msgs)

            layr03 = await core.addLayer()
            layr04 = await core.addLayer()
            vdef03 = {'layers': [layr03['iden'], layr04['iden']]}
            vdef03 = await core.addView(vdef=vdef03)

            opts = {'vars': {'fork': vdef03['iden'], 'base': view01.iden}}
            msgs = await core.stormlist('$lib.view.get($fork).set(parent, $base)', opts=opts)
            self.stormIsInErr('You may not set parent on a view which has more than one layer', msgs)

    async def test_view_fork_merge(self):

        async with self.getTestCore() as core:
            await core.nodes('[ test:int=8 +#faz ]')
            await core.nodes('[ test:int=9 test:int=10 ]')
            await core.auth.addUser('visi')
            await core.addTagProp('score', ('int', {}), {})

            self.eq(1, await core.count('test:int=8 +#faz'))
            self.eq(2, await core.count('test:int=9 test:int=10'))
            self.eq(3, (await core.getFormCounts()).get('test:int'))

            # Fork the main view
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')
            view2 = core.getView(view2_iden)

            # The new view has the same nodes as the old view
            nodes = await alist(view2.eval('test:int=10'))
            self.len(1, nodes)

            await core.nodes('[ test:int=11 ]')

            # A node added to the parent after the fork is still seen by the child
            nodes = await alist(view2.eval('test:int=11'))
            self.len(1, nodes)
            self.eq(4, (await core.getFormCounts()).get('test:int'))

            # A node added to the child is not seen by the parent
            nodes = await alist(view2.eval('[ test:int=12 ]'))
            self.len(1, nodes)

            nodes = await core.nodes('test:int=12')
            self.len(0, nodes)
            self.eq(4, (await core.view.getFormCounts()).get('test:int'))

            # Deleting nodes from the child view should not affect the main
            await alist(view2.eval('test:int | delnode'))

            self.eq(4, (await core.view.getFormCounts()).get('test:int'))
            nodes = await alist(view2.eval('test:int=10'))
            self.len(0, nodes)

            self.eq(4, (await core.getFormCounts()).get('test:int'))
            await self.agenlen(0, view2.eval('test:int=12'))

            # The child view can delete a node in the lower layer
            await self.agenlen(0, view2.eval('test:int=10'))

            # Add a node back
            await self.agenlen(1, view2.eval('[ test:int=12 ]'))

            # Add a bunch of test nodes to the view.
            for i in range(20):
                await self.agenlen(1, view2.eval('[test:int=$val]', opts={'vars': {'val': i + 1000}}))

            await core.nodes('[ test:int=15 test:int=16 test:int=17 ]')

            # Add prop that will only exist in the child
            await alist(view2.eval('test:int=15 [:loc=us]'))
            self.len(1, await alist(view2.eval('test:int=15 +:loc=us')))
            self.len(0, await core.nodes('test:int=15 +:loc=us'))

            # Add tag that will only exist in child
            await alist(view2.eval('test:int=15 [+#foo.bar]'))
            self.len(1, await alist(view2.eval('test:int=15 +#foo.bar')))
            self.len(0, await core.nodes('test:int=15 +#foo.bar'))

            # Add tag prop that will only exist in child
            await alist(view2.eval('test:int=15 [+#faz:score=55]'))
            self.len(1, await alist(view2.eval('test:int=15 +#faz:score=55')))
            self.len(0, await core.nodes('test:int=15 +#faz:score=55'))

            # Add nodedata that will only exist in child
            await alist(view2.eval('test:int=15 $node.data.set(spam, ham)'))
            self.len(1, await view2.callStorm('test:int=15 return($node.data.list())'))
            self.len(0, await core.callStorm('test:int=15 return($node.data.list())'))

            # Add edges that will only exist in the child
            await alist(view2.eval('test:int=15 [ +(refs)> {test:int=16} ]'))
            await alist(view2.eval('test:int=16 [ +(refs)> {test:int=17} ]'))
            self.len(2, await alist(view2.eval('test:int -(refs)> *')))
            self.len(0, await core.nodes('test:int -(refs)> *'))

            # Forker and forkee have their layer configuration frozen
            tmplayr = await core.addLayer()
            tmpiden = tmplayr['iden']
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.addLayer(tmpiden))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.addLayer(tmpiden))
            await self.asyncraises(s_exc.BadArg, view2.setLayers([tmpiden]))

            # You can't merge a non-forked view
            await self.asyncraises(s_exc.SynErr, view2.core.view.merge())

            # You can't merge if the parent's write layer is readonly
            view2.parent.layers[0].readonly = True
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.merge())
            view2.parent.layers[0].readonly = False

            vdef3 = await view2.fork()
            view3_iden = vdef3.get('iden')
            view3 = core.getView(view3_iden)

            # You can't delete a view or merge it if it has children
            await self.asyncraises(s_exc.SynErr, view2.merge())
            await self.asyncraises(s_exc.SynErr, view2.core.delView(view2.iden))
            await self.asyncraises(s_exc.SynErr, view2.core.delView(view2.iden))
            layr = await core.addLayer()
            layriden = layr['iden']
            await self.asyncraises(s_exc.SynErr, view2.addLayer(layriden))
            await view3.core.delView(view3.iden)

            async with core.getLocalProxy(user='visi') as prox:
                with self.raises(s_exc.AuthDeny):
                    await prox.count('test:int=12', opts={'view': view2.iden})

            # The parent count is correct
            self.eq(7, (await core.view.getFormCounts()).get('test:int'))

            # Merge the child back into the parent
            await view2.merge()
            await view2.wipeLayer()

            # The parent counts includes all the nodes that were merged
            self.eq(24, (await core.view.getFormCounts()).get('test:int'))

            # A node added to the child is now present in the parent
            nodes = await core.nodes('test:int=12')
            self.len(1, nodes)

            # A node deleted in the child is now deleted in the parent
            nodes = await core.nodes('test:int=11')
            self.len(0, nodes)

            # The child can still see the parent's pre-existing node
            nodes = await view2.nodes('test:int=15')
            self.len(1, nodes)

            # Prop that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +:loc=us'))
            self.len(1, await core.nodes('test:int:loc=us'))

            # Tag that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +#foo.bar'))
            self.len(1, await core.nodes('test:int#foo.bar'))

            # Tagprop that as only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +#faz:score=55'))
            self.len(1, await core.nodes('test:int#faz:score=55'))

            # Node data that was only set in child is present in parent
            self.len(1, await core.callStorm('test:int=15 return($node.data.list())'))
            self.len(1, await core.nodes('yield $lib.lift.byNodeData(spam)'))

            # Edge that was only set in child present in parent
            self.len(2, await core.nodes('test:int -(refs)> *'))

            # The child count includes all the nodes in the view
            self.eq(24, (await view2.getFormCounts()).get('test:int'))

            # The child can see nodes that got merged
            nodes = await view2.nodes('test:int=12')
            self.len(1, nodes)
            nodes = await view2.nodes('test:int=1000')
            self.len(1, nodes)
            nodes = await view2.nodes('test:int=1019')
            self.len(1, nodes)

            await core.delView(view2.iden)
            await core.view.addLayer(layriden)

            # But not the same layer twice
            await self.asyncraises(s_exc.DupIden, core.view.addLayer(layriden))

    async def test_view_merge_ival(self):

        async with self.getTestCore() as core:

            forkview = await core.callStorm('return($lib.view.get().fork().iden)')
            forkopts = {'view': forkview}

            seen_maxval = (s_time.parse('2010'), s_time.parse('2020') + 1)
            seen_midval = (s_time.parse('2010'), s_time.parse('2015'))
            seen_minval = (s_time.parse('2000'), s_time.parse('2015'))
            seen_exival = (s_time.parse('2000'), s_time.parse('2021'))

            await core.nodes('[ test:str=maxval .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=maxval [ .seen=2020 ]', opts=forkopts)
            self.eq(seen_maxval, nodes[0].get('.seen'))
            nodes = await core.nodes('test:str=maxval', opts=forkopts)
            self.eq(seen_maxval, nodes[0].get('.seen'))

            await core.nodes('[ test:str=midval .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=midval [ .seen=2012 ]', opts=forkopts)
            self.eq(seen_midval, nodes[0].get('.seen'))
            nodes = await core.nodes('test:str=midval', opts=forkopts)
            self.eq(seen_midval, nodes[0].get('.seen'))

            await core.nodes('[ test:str=minval .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=minval [ .seen=2000 ]', opts=forkopts)
            self.eq(seen_minval, nodes[0].get('.seen'))
            nodes = await core.nodes('test:str=minval', opts=forkopts)
            self.eq(seen_minval, nodes[0].get('.seen'))

            await core.nodes('[ test:str=exival .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=exival [ .seen=(2000, 2021) ]', opts=forkopts)
            self.eq(seen_exival, nodes[0].get('.seen'))
            nodes = await core.nodes('test:str=exival', opts=forkopts)
            self.eq(seen_exival, nodes[0].get('.seen'))

            await core.nodes('$lib.view.get().merge()', opts=forkopts)

            nodes = await core.nodes('test:str=maxval')
            self.eq(seen_maxval, nodes[0].get('.seen'))

            nodes = await core.nodes('test:str=midval')
            self.eq(seen_midval, nodes[0].get('.seen'))

            nodes = await core.nodes('test:str=minval')
            self.eq(seen_minval, nodes[0].get('.seen'))

            nodes = await core.nodes('test:str=exival')
            self.eq(seen_exival, nodes[0].get('.seen'))

            # bad type

            await self.asyncraises(s_exc.BadTypeValu, core.nodes('test:str=maxval [ .seen=newp ]', opts=forkopts))
            await core.nodes('test:str=maxval [ .seen?=newp +#foo ]', opts=forkopts)
            self.len(1, await core.nodes('test:str#foo', opts=forkopts))

    async def test_view_trigger(self):
        async with self.getTestCore() as core:

            # Fork the main view
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')
            view2 = core.getView(view2_iden)

            await core.view.addTrigger({
                'cond': 'node:add',
                'form': 'test:int',
                'storm': '[ test:str=mainhit ]'
            })

            nodes = await core.nodes('[ test:int=11 ]', opts={'view': view2.iden})
            self.len(1, nodes)

            self.len(0, await core.view.nodes('test:str=mainhit'))

            # A trigger on the child view fires on the child view but not the main view
            await view2.addTrigger({
                'cond': 'node:add',
                'form': 'test:int',
                'storm': '[ test:str=forkhit ]',
            })

            nodes = await alist(view2.eval('[ test:int=12 ]'))

            nodes = await view2.nodes('test:str=forkhit')
            self.len(1, nodes)

            nodes = await alist(core.view.eval('test:str=forkhit'))
            self.len(0, nodes)

            # listTriggers should show only that view's triggers
            trigs = await view2.listTriggers()
            self.len(1, trigs)

            await view2.addTrigger({
                'cond': 'tag:add',
                'tag': 'foo',
                'storm': '[ +#bar ]',
            })

            await view2.addTrigger({
                'cond': 'tag:del',
                'tag': 'foo',
                'storm': '[ -#bar ]',
            })

            await view2.addTrigger({
                'cond': 'tag:add',
                'tag': 'foo',
                'storm': '| newpnewp',
            })

            await view2.addTrigger({
                'cond': 'tag:del',
                'tag': 'foo',
                'storm': '| newpnewp',
            })

            nodes = await view2.nodes('test:str=forkhit [+#foo]')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo'))
            self.nn(nodes[0].getTag('bar'))

            nodes = await view2.nodes('test:str=forkhit [-#foo]')
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo'))
            self.none(nodes[0].getTag('bar'))

            await view2.merge()

            # Trigger runs on merged nodes in main view
            self.len(1, await core.view.nodes('test:str=mainhit'))

            await view2.fini()
            await view2.delete()

    async def test_storm_editformat(self):
        async with self.getTestCore() as core:
            mesgs = await core.stormlist('[test:str=foo1 :hehe=bar]', opts={'editformat': 'nodeedits'})
            count = collections.Counter(m[0] for m in mesgs)
            self.eq(1, count['init'])
            self.eq(1, count['fini'])
            self.eq(1, count['node'])
            self.eq(2, count['node:edits'])
            self.eq(0, count['node:add'])

            mesgs = await core.stormlist('[test:str=foo3 :hehe=bar]', opts={'editformat': 'count'})
            count = collections.Counter(m[0] for m in mesgs)
            self.eq(1, count['init'])
            self.eq(1, count['node'])
            self.eq(1, count['fini'])
            self.eq(2, count['node:edits:count'])
            self.eq(0, count['node:edits'])
            self.eq(0, count['node:add'])
            cmsgs = [m[1] for m in mesgs if m[0] == 'node:edits:count']
            self.eq([{'count': 2}, {'count': 1}], cmsgs)

            mesgs = await core.stormlist('[test:str=foo3 :hehe=bar]', opts={'editformat': 'none'})
            count = collections.Counter(m[0] for m in mesgs)
            self.eq(1, count['init'])
            self.eq(0, count['node:edits:count'])
            self.eq(0, count['node:edits'])
            self.eq(0, count['node:add'])
            self.eq(1, count['node'])
            self.eq(1, count['fini'])

            with self.raises(s_exc.BadConfValu):
                await core.stormlist('[test:str=foo3 :hehe=bar]', opts={'editformat': 'jsonl'})

    async def test_lib_view_addNodeEdits(self):

        async with self.getTestCore() as core:

            view = await core.callStorm('''
                $layr = $lib.layer.add().iden
                $view = $lib.view.add(($layr,))
                return($view.iden)
            ''')

            await core.nodes('trigger.add node:add --form ou:org --query {[+#foo]}', opts={'view': view})

            nodes = await core.nodes('[ ou:org=* ]')
            self.len(0, await core.nodes('ou:org', opts={'view': view}))

            await core.stormlist('''
                $view = $lib.view.get($viewiden)
                for ($offs, $edits) in $lib.layer.get().edits(wait=$lib.false) {
                    $view.addNodeEdits($edits)
                }
            ''', opts={'vars': {'viewiden': view}})

            self.len(1, await core.nodes('ou:org +#foo', opts={'view': view}))

            # test node:del triggers
            await core.nodes('trigger.add node:del --form ou:org --query {[test:str=foo]}', opts={'view': view})

            nextoffs = await core.getView(iden=view).layers[0].getEditIndx()

            await core.nodes('ou:org | delnode')

            await core.stormlist('''
                $view = $lib.view.get($viewiden)
                for ($offs, $edits) in $lib.layer.get().edits(offs=$offs, wait=$lib.false) {
                    $view.addNodeEdits($edits)
                }
            ''', opts={'vars': {'viewiden': view, 'offs': nextoffs}})

            self.len(0, await core.nodes('ou:org +#foo', opts={'view': view}))

            self.len(1, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_storNodeEdits(self):

        async with self.getTestCore() as core:

            view = await core.callStorm('''
                $layr = $lib.layer.add().iden
                $view = $lib.view.add(($layr,))
                return($view.iden)
            ''')

            await core.nodes('trigger.add node:add --form ou:org --query {[+#foo]}', opts={'view': view})
            await core.nodes('trigger.add node:del --form inet:ip --query {[test:str=foo]}', opts={'view': view})

            await core.nodes('[ ou:org=* ]')
            self.len(0, await core.nodes('ou:org', opts={'view': view}))

            await core.nodes('[ inet:ip=([4, 0]) ]')
            self.len(0, await core.nodes('inet:ip', opts={'view': view}))

            await core.nodes('inet:ip=([4, 0]) | delnode')

            edits = await core.callStorm('''
                $nodeedits = ()
                for ($offs, $edits) in $lib.layer.get().edits(wait=$lib.false) {
                    $nodeedits.extend($edits)
                }
                return($nodeedits)
            ''')

            user = await core.auth.addUser('user')
            await user.addRule((True, ('view', 'read')))

            async with core.getLocalProxy(share=f'*/view/{view}', user='user') as prox:
                self.eq(0, await prox.getEditSize())
                await self.asyncraises(s_exc.AuthDeny, prox.storNodeEdits(edits, None))

            await user.addRule((True, ('node',)))

            async with core.getLocalProxy(share=f'*/view/{view}', user='user') as prox:
                self.none(await prox.storNodeEdits(edits, None))

            self.len(1, await core.nodes('ou:org#foo', opts={'view': view}))
            self.len(0, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_wipeLayer(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            opts = {
                'vars': {
                    'arrayguid': s_common.guid('arrayguid'),
                },
            }

            await core.addTagProp('score', ('int', {}), {})

            await core.nodes('trigger.add node:del --query { $lib.globals.trig = $lib.true } --form test:str')

            await core.nodes('[ test:str=foo :hehe=hifoo +#test ]')
            await core.nodes('[ test:arrayprop=$arrayguid :strs=(faz, baz) ]', opts=opts)
            await core.nodes('''
                [ test:str=bar
                    :bar=(test:str, foo)
                    :baz="test:str:hehe=hifoo"
                    :tick=2020
                    :hehe=hibar
                    .seen=2021
                    +#test
                    +#test.foo:score=100
                    <(refs)+ { test:str=foo }
                    +(refs)> { test:arrayprop=$arrayguid }
                ]
                $node.data.set(bardata, ({"hi": "there"}))
            ''', opts=opts)

            nodecnt = await core.count('.created')

            offs = await layr.getEditOffs()

            # must have perms for each edit

            user = await core.addUser('redox')
            useriden = user['iden']
            opts = {'user': useriden}

            await self.asyncraises(s_exc.AuthDeny, core.nodes('$lib.view.get().wipeLayer()', opts=opts))

            await core.addUserRule(useriden, (True, ('node', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'prop', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'tag', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'edge', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'data', 'pop')), gateiden=layr.iden)

            await core.nodes('$lib.view.get().wipeLayer()', opts=opts)

            self.len(nodecnt, layr.nodeeditlog.iter(offs + 1)) # one del nodeedit for each node

            self.len(0, await core.nodes('.created'))

            self.true(await core.callStorm('return($lib.globals.trig)'))

            self.eq({}, await layr.getFormCounts())

            self.eq(0, layr.layrslab.stat(db=layr.bynid)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.indxdb)['entries'])

            self.eq(0, layr.dataslab.stat(db=layr.nodedata)['entries'])
            self.eq(0, layr.dataslab.stat(db=layr.dataname)['entries'])

            # only the write layer gets deletes

            scmd = '$fork=$lib.view.get().fork() return(($fork.iden, $fork.layers.0.iden))'
            forkviden, forkliden = await core.callStorm(scmd)

            await core.nodes('[ test:str=chicken :hehe=finger ]')
            await core.nodes('test:str=chicken [ :hehe=patty ]', opts={'view': forkviden})
            await core.nodes('[ test:str=turkey ]', opts={'view': forkviden})

            await core.nodes('$lib.view.get().wipeLayer()', opts={'view': forkviden})

            self.len(1, await core.nodes('test:str=chicken +:hehe=finger'))
            self.len(1, await core.nodes('test:str=chicken +:hehe=finger', opts={'view': forkviden}))
            self.len(0, await core.nodes('test:str=turkey', opts={'view': forkviden}))

            await core.nodes('view.merge $forkviden --delete', opts={'vars': {'forkviden': forkviden}})

            # can wipe through layer push/pull

            self.len(1, await core.nodes('test:str=chicken'))
            baseoffs = await layr.getEditOffs()

            async def waitPushOffs(core_, iden_, offs_):
                gvar = f'push:{iden_}'
                while True:
                    if await core_.getStormVar(gvar, -1) >= offs_:
                        return
                    await asyncio.sleep(0)

            async with self.getTestCore() as core2:

                opts = {
                    'vars': {
                        'baseiden': layr.iden,
                        'baseurl': core.getLocalUrl('*/layer'),
                        'syncurl': core2.getLocalUrl('*/layer'),
                    },
                }

                puller_iden, puller_view, puller_layr = await core2.callStorm('''
                    $lyr = $lib.layer.add()
                    $view = $lib.view.add(($lyr.iden,))
                    $pdef = $lyr.addPull($lib.str.concat($baseurl, "/", $baseiden))
                    return(($pdef.iden, $view.iden, $lyr.iden))
                ''', opts=opts)

                await asyncio.wait_for(waitPushOffs(core2, puller_iden, baseoffs), timeout=5)
                self.len(1, await core2.nodes('test:str=chicken', opts={'view': puller_view}))
                puller_offs = await core2.getLayer(iden=puller_layr).getEditOffs()

                pushee_view, pushee_layr = await core2.callStorm('''
                    $lyr = $lib.layer.add()
                    $view = $lib.view.add(($lyr.iden,))
                    return(($view.iden, $lyr.iden))
                ''', opts=opts)

                opts['user'] = None
                opts['vars']['pushiden'] = pushee_layr
                pushee_iden = await core.callStorm('''
                    $lyr = $lib.layer.get()
                    $pdef = $lyr.addPush($lib.str.concat($syncurl, "/", $pushiden))
                    return($pdef.iden)
                ''', opts=opts)

                await asyncio.wait_for(waitPushOffs(core, pushee_iden, baseoffs), timeout=5)
                self.len(1, await core2.nodes('test:str=chicken', opts={'view': pushee_view}))
                pushee_offs = await core2.getLayer(iden=pushee_layr).getEditOffs()

                await core.nodes('$lib.view.get().wipeLayer()')

                self.len(0, await core.nodes('test:str=chicken'))

                self.true(await core2.getLayer(iden=puller_layr).waitEditOffs(puller_offs + 1, timeout=2))
                self.len(0, await core2.nodes('test:str=chicken', opts={'view': puller_view}))

                self.true(await core2.getLayer(iden=pushee_layr).waitEditOffs(pushee_offs + 1, timeout=2))
                self.len(0, await core2.nodes('test:str=chicken', opts={'view': pushee_view}))

    async def test_lib_view_merge_perms(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})

            baselayr = core.getLayer().iden

            user = await core.addUser('redox')
            useriden = user['iden']
            useropts = {'user': useriden}

            await core.addUserRule(useriden, (True, ('view', 'add')))

            forkview = await core.callStorm('return($lib.view.get().fork().iden)', opts=useropts)
            viewopts = {**useropts, 'view': forkview}

            q = '''
            [ test:str=foo
                .seen = now
                +#seen:score = 5
                <(refs)+ { [ test:str=bar ] }
            ]
            $node.data.set(foo, bar)
            '''
            await core.nodes(q, opts=viewopts)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.eq('node.prop.set.syn:tag.base', cm.exception.errinfo['perm'])

            await core.addUserRule(useriden, (True, ('node', 'prop', 'set')), gateiden=baselayr)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.eq('node.add.syn:tag', cm.exception.errinfo['perm'])

            await core.addUserRule(useriden, (True, ('node', 'add')), gateiden=baselayr)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.eq('node.tag.add.seen', cm.exception.errinfo['perm'])

            await core.addUserRule(useriden, (True, ('node', 'tag', 'add')), gateiden=baselayr)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.eq('node.data.set.foo', cm.exception.errinfo['perm'])

            await core.addUserRule(useriden, (True, ('node', 'data', 'set')), gateiden=baselayr)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.eq('node.edge.add.refs', cm.exception.errinfo['perm'])

            await core.addUserRule(useriden, (True, ('node', 'edge', 'add')), gateiden=baselayr)

            await core.nodes('$lib.view.get().merge()', opts=viewopts)

            msgs = await core.stormlist('test:str=foo $node.data.load(foo)')
            podes = [n[1] for n in msgs if n[0] == 'node']
            self.len(1, podes)
            self.nn(podes[0][1]['props'].get('.seen'))
            self.nn(podes[0][1]['tags'].get('seen'))
            self.nn(podes[0][1]['tagprops']['seen']['score'])
            self.nn(podes[0][1]['nodedata'].get('foo'))

            await core.delUserRule(useriden, (True, ('node', 'tag', 'add')), gateiden=baselayr)

            await core.addUserRule(useriden, (True, ('node', 'tag', 'del', 'seen')), gateiden=baselayr)
            await core.addUserRule(useriden, (True, ('node', 'tag', 'add', 'rep', 'foo')), gateiden=baselayr)

            await core.nodes('test:str=foo [ -#seen +#rep.foo ]', opts=viewopts)

            await core.nodes('$lib.view.get().merge()', opts=viewopts)
            nodes = await core.nodes('test:str=foo')
            self.nn(nodes[0].get('#rep.foo'))

            await core.nodes('test:str=foo [ -#rep ]')

            await core.nodes('test:str=foo | merge --apply', opts=viewopts)
            nodes = await core.nodes('test:str=foo')
            self.nn(nodes[0].get('#rep.foo'))

            await core.nodes('test:str=foo [ -#rep ]')
            await core.nodes('test:str=foo [ +#rep=now ]', opts=viewopts)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)

    async def test_addNodes(self):
        async with self.getTestCore() as core:

            view = core.getView()

            ndefs = ()
            self.len(0, await alist(view.addNodes(ndefs)))

            ndefs = (
                (('test:str', 'hehe'), {'props': {'.created': 5, 'tick': 3}, 'tags': {'cool': (1, 2)}}, ),
            )
            result = await alist(view.addNodes(ndefs))
            self.len(1, result)

            node = result[0]
            self.eq(node.get('tick'), 3)
            self.ge(node.get('.created', 0), 5)
            self.eq(node.get('#cool'), (1, 2))

            nodes = await alist(view.nodesByPropValu('test:str', '=', 'hehe'))
            self.len(1, nodes)
            self.eq(nodes[0], node)

            # Make sure that we can still add secondary props even if the node already exists
            node2 = await view.addNode('test:str', 'hehe', props={'baz': 'test:guid:tick=2020'})
            self.eq(node2, node)
            self.nn(node2.get('baz'))

    async def test_addNodesAuto(self):
        '''
        Secondary props that are forms when set make nodes
        '''
        async with self.getTestCore() as core:

            view = core.getView()

            node = await view.addNode('test:guid', '*')
            await node.set('size', 42)
            nodes = await alist(view.nodesByPropValu('test:int', '=', 42))
            self.len(1, nodes)

            # For good measure, set a secondary prop that is itself a comp type that has an element that
            # is a form
            node = await view.addNode('test:haspivcomp', 42)
            await node.set('have', ('woot', 'rofl'))
            nodes = await alist(view.nodesByPropValu('test:pivcomp', '=', ('woot', 'rofl')))
            self.len(1, nodes)
            nodes = await alist(view.nodesByProp('test:pivcomp:lulz'))
            self.len(1, nodes)
            nodes = await alist(view.nodesByPropValu('test:str', '=', 'rofl'))
            self.len(1, nodes)

            # Make sure the sodes didn't get misordered
            node = await view.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))
            self.eq(node.ndef[0], 'inet:dns:a')

    @contextlib.asynccontextmanager
    async def _getTestCoreMultiLayer(self):
        '''
        Create a cortex with a second view which has an additional layer above the main layer.

        Notes:
            This method is broken out so subclasses can override.
        '''
        async with self.getTestCore() as core0:

            view0 = core0.view
            layr0 = view0.layers[0]

            ldef1 = await core0.addLayer()
            layr1 = core0.getLayer(ldef1.get('iden'))
            vdef1 = await core0.addView({'layers': [layr1.iden, layr0.iden]})

            yield view0, core0.getView(vdef1.get('iden'))

    async def test_cortex_lift_layers_simple(self):
        async with self._getTestCoreMultiLayer() as (view0, view1):
            ''' Test that you can write to view0 and read it from view1 '''
            self.len(1, await alist(view0.eval('[ inet:ip=1.2.3.4 :asn=42 +#woot=(2014, 2015)]')))
            self.len(1, await alist(view1.eval('inet:ip')))
            self.len(1, await alist(view1.eval('inet:ip=1.2.3.4')))
            self.len(1, await alist(view1.eval('inet:ip:asn=42')))
            self.len(1, await alist(view1.eval('inet:ip +:asn=42')))
            self.len(1, await alist(view1.eval('inet:ip +#woot')))

    async def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):

            self.len(1, await alist(view0.eval('[ inet:ip=1.2.3.4 :asn=42 +#woot=(2014, 2015)]')))
            self.len(1, await alist(view1.eval('inet:ip#woot@=2014')))
            self.len(1, await alist(view1.eval('inet:ip=1.2.3.4 [ :asn=31337 +#woot=2016 ]')))

            self.len(0, await alist(view0.eval('inet:ip:asn=31337')))
            self.len(1, await alist(view1.eval('inet:ip:asn=31337')))

            self.len(1, await alist(view0.eval('inet:ip:asn=42')))
            self.len(0, await alist(view1.eval('inet:ip:asn=42')))

            self.len(1, await alist(view0.eval('[ test:arrayprop="*" :ints=(1, 2, 3) ]')))
            self.len(1, await alist(view1.eval('test:int=2 -> test:arrayprop')))
            self.len(1, await alist(view1.eval('test:arrayprop [ :ints=(4, 5, 6) ]')))

            self.len(0, await alist(view0.eval('test:int=5 -> test:arrayprop')))
            self.len(1, await alist(view1.eval('test:int=5 -> test:arrayprop')))

            self.len(1, await alist(view0.eval('test:int=2 -> test:arrayprop')))
            self.len(0, await alist(view1.eval('test:int=2 -> test:arrayprop')))

            self.len(1, await alist(view1.eval('[ test:int=7 +#atag=2020 ]')))
            self.len(1, await alist(view0.eval('[ test:int=7 +#atag=2021 ]')))

            self.len(0, await alist(view0.eval('test:int#atag@=2020')))
            self.len(1, await alist(view1.eval('test:int#atag@=2020')))

            self.len(1, await alist(view0.eval('test:int#atag@=2021')))
            self.len(0, await alist(view1.eval('test:int#atag@=2021')))

    async def test_cortex_lift_layers_dup(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            # add to view1 first so we can cause creation in both...
            self.len(1, await alist(view1.eval('[ inet:ip=1.2.3.4 :asn=42 ]')))
            self.len(1, await alist(view0.eval('[ inet:ip=1.2.3.4 :asn=42 ]')))

            # lift by primary and ensure only one...
            self.len(1, await alist(view1.eval('inet:ip')))

            # lift by secondary and ensure only one...
            self.len(1, await alist(view1.eval('inet:ip:asn=42')))

            # now set one to a diff value that we will ask for but should be masked
            self.len(1, await alist(view0.eval('[ inet:ip=1.2.3.4 :asn=99 ]')))
            self.len(0, await alist(view1.eval('inet:ip:asn=99')))

            self.len(1, await alist(view0.eval('[ inet:ip=1.2.3.5 :asn=43 ]')))
            self.len(2, await alist(view1.eval('inet:ip:asn')))

            await view0.core.addTagProp('score', ('int', {}), {})

            self.len(1, await alist(view1.eval('inet:ip=1.2.3.4 [ +#foo:score=42 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.4 [ +#foo:score=42 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.4 [ +#foo:score=99 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.5 [ +#foo:score=43 ]')))

            nodes = await alist(view1.eval('#foo:score'))
            self.len(2, await alist(view1.eval('#foo:score')))

    async def test_cortex_lift_bytype(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            nodes = await core.nodes('inet:ip*type=1.2.3.4')
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', (4, 0x01020304))))

    async def test_clearcache(self):

        async with self.getTestCore() as core:

            view = core.getView()

            original_node0 = await view.addNode('test:str', 'node0')
            self.len(2, view.nodecache)
            self.len(2, view.livenodes)
            self.len(0, view.tagcache)
            self.len(0, core.tagnorms)

            await original_node0.addTag('foo.bar.baz')
            self.len(5, view.nodecache)
            self.len(5, view.livenodes)
            self.len(3, core.tagnorms)

            new_node0 = await view.getNodeByNdef(('test:str', 'node0'))
            await new_node0.delTag('foo.bar.baz')
            self.notin('foo.bar.baz', new_node0.getTags())
            # Original reference is updated as well
            self.notin('foo.bar.baz', original_node0.getTags())

            # We rely on the layer's row cache to be correct in this test.

            # Lift is cached..
            same_node0 = await view.getNodeByNdef(('test:str', 'node0'))
            self.eq(id(original_node0), id(same_node0))

            # flush caches!
            view.clearCache()
            core.tagnorms.clear()

            self.len(0, view.nodecache)
            self.len(0, view.livenodes)
            self.len(0, view.tagcache)
            self.len(0, core.tagnorms)

            # After clearing the cache and lifting nodes, the new node
            # was lifted directly from the layer.
            new_node0 = await view.getNodeByNdef(('test:str', 'node0'))
            self.ne(id(original_node0), id(new_node0))
            self.notin('foo.bar.baz', new_node0.getTags())

    async def test_cortex_lift_layers_bad_filter_tagprop(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result, with tagprops
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=20 ]'))
            self.len(1, await view1.nodes('#woot:score=20'))
            self.len(1, await view1.nodes('[ test:int=10 +#woot:score=40 ]'))

            self.len(0, await view0.nodes('#woot:score=40'))
            self.len(1, await view1.nodes('#woot:score=40'))

            self.len(1, await view0.nodes('#woot:score=20'))
            self.len(0, await view1.nodes('#woot:score=20'))

    async def test_cortex_lift_layers_dup_tagprop(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view1.nodes('[ test:int=10 +#woot:score=20 ]'))
            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=20 ]'))

            self.len(1, await view1.nodes('#woot:score=20'))

            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=40 ]'))

    async def test_cortex_lift_layers_ordering(self):

        async with self._getTestCoreMultiLayer() as (view0, view1):

            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})
            await view0.core.addTagProp('data', ('data', {}), {'doc': 'hi there'})

            await view0.nodes('[ inet:ip=1.1.1.4 ]')
            await view1.nodes('inet:ip=1.1.1.4 [+#tag]')
            await view0.nodes('inet:ip=1.1.1.4 | delnode')
            nodes = await view1.nodes('#tag | uniq')
            self.len(0, nodes)

            await view0.nodes('[ inet:ip=1.1.1.4 :asn=4 +#woot:score=4] $node.data.set(woot, 4)')
            await view0.nodes('[ inet:ip=1.1.1.1 :asn=1 +#woot:score=1] $node.data.set(woot, 1)')
            await view1.nodes('[ inet:ip=1.1.1.2 :asn=2 +#woot:score=2] $node.data.set(woot, 2)')
            await view0.nodes('[ inet:ip=1.1.1.3 :asn=3 +#woot:score=3] $node.data.set(woot, 3)')

            await view1.nodes('[ test:str=foo +#woot=2001 ]')
            await view0.nodes('[ test:str=foo +#woot=2001 ]')
            await view0.nodes('[ test:int=1 +#woot=2001 ]')
            await view0.nodes('[ test:int=2 +#woot=2001 ]')

            nodes = await view1.nodes('#woot')
            self.len(7, nodes)

            nodes = await view1.nodes('inet:ip')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                valu = node.ndef[1][1]
                self.gt(valu, last)
                last = valu

            nodes = await view1.nodes('inet:ip:asn')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                asn = node.get('asn')
                self.lt(asn, last)
                last = asn

            nodes = await view1.nodes('#woot:score')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.lt(scor, last)
                last = scor

            await view0.nodes('[ test:arrayform=(3,5,6)]')
            await view0.nodes('[ test:arrayform=(1,2,3)]')
            await view1.nodes('[ test:arrayform=(2,3,4)]')
            await view0.nodes('[ test:arrayform=(3,4,5)]')

            nodes = await view1.nodes('test:arrayform*[=3]')
            self.len(4, nodes)

            nodes = await view1.nodes('test:arrayform*[=2]')
            self.len(2, nodes)

            nodes = await view1.nodes('yield $lib.lift.byNodeData(woot)')
            self.len(4, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(2, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(4, nodes)

            await view0.nodes('[ test:data=(123) :data=(123) +#woot:data=(123)]')
            await view1.nodes('[ test:data=foo :data=foo +#woot:data=foo]')
            await view0.nodes('[ test:data=(0) :data=(0) +#woot:data=(0)]')
            await view0.nodes('[ test:data=bar :data=foo +#woot:data=foo]')

            nodes = await view1.nodes('test:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data=foo')
            self.len(1, nodes)

            nodes = await view1.nodes('test:data:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data:data=foo')
            self.len(2, nodes)

            nodes = await view1.nodes('#woot:data')
            self.len(4, nodes)

            nodes = await view1.nodes('#woot:data=foo')
            self.len(2, nodes)

    async def test_node_editor(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'verbs': ('_pwns', '_foo')}}
            await core.nodes('for $verb in $verbs { $lib.model.ext.addEdge(*, $verb, *, ({})) }', opts=opts)

            await core.nodes('$lib.model.ext.addTagProp(test, (str, ({})), ({}))')
            await core.nodes('[ media:news=63381924986159aff183f0c85bd8ebad +(refs)> {[ inet:fqdn=vertex.link ]} ]')
            root = core.auth.rootuser

            async with core.view.getEditor() as editor:
                fqdn = await editor.addNode('inet:fqdn', 'vertex.link')
                news = await editor.addNode('media:news', '63381924986159aff183f0c85bd8ebad')

                self.true(s_common.isbuidhex(fqdn.iden()))

                self.false(await news.addEdge('refs', fqdn.nid))
                self.len(0, editor.getNodeEdits())

                self.true(await news.addEdge('_pwns', fqdn.nid))
                self.false(await news.addEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(1, nodeedits)
                self.len(1, nodeedits[0][2])

                self.true(await news.delEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(0, nodeedits)

                self.true(await news.addEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(1, nodeedits)
                self.len(1, nodeedits[0][2])

                self.false(await news.hasData('foo'))
                await news.setData('foo', 'bar')
                self.true(await news.hasData('foo'))

                self.false(news.hasTagProp('foo', 'test'))
                await news.setTagProp('foo', 'test', 'bar')
                self.true(news.hasTagProp('foo', 'test'))

            async with core.view.getEditor() as editor:
                news = await editor.addNode('media:news', '63381924986159aff183f0c85bd8ebad')

                self.true(await news.delEdge('_pwns', fqdn.nid))
                self.false(await news.delEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(1, nodeedits)
                self.len(1, nodeedits[0][2])

                self.true(await news.addEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(0, nodeedits)

                self.true(await news.hasData('foo'))

                self.true(news.hasTagProp('foo', 'test'))

                with self.raises(s_exc.NoSuchProp):
                    await news.pop('newp')

                with self.raises(s_exc.ReadOnlyProp):
                    await news.pop('.created')

                with self.raises(s_exc.NoSuchTagProp):
                    await news.delTagProp('newp', 'newp')

            self.len(1, await core.nodes('media:news -(_pwns)> *'))

            self.len(1, await core.nodes('[ test:ro=foo :writeable=hehe :readable=haha ]'))
            self.len(1, await core.nodes('test:ro=foo [ :readable = haha ]'))
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('test:ro=foo [ :readable=newp ]')

            await core.addTagProp('score', ('int', {}), {})

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            addq = '''[
            inet:ip=1.2.3.4
                :asn=4
                +#foo.tag=2024
                +#bar.tag:score=5
                +(_foo)> {[ it:dev:str=n2 ]}
            ]
            $node.data.set(foodata, bar)
            '''
            await core.nodes(addq)
            nodes = await core.nodes('inet:ip=1.2.3.4 [ +#baz.tag:score=6 ]', opts=viewopts2)

            n2node = (await core.nodes('it:dev:str=n2'))[0]
            n2nid = n2node.nid

            async with view2.getEditor() as editor:
                node = await editor.getNodeByBuid(nodes[0].buid)
                self.true(await node.delEdge('_foo', n2nid))
                self.true(await node.addEdge('_foo', n2nid))
                self.true(await node.delEdge('_foo', n2nid))

                self.true(await node.setTagProp('cool.tag', 'score', 7))
                self.isin('score', node.getTagProps('cool.tag'))
                self.isin(('score', 0), node.getTagPropsWithLayer('cool.tag'))
                self.eq(7, node.getTagProp('cool.tag', 'score'))
                self.eq((7, 0), node.getTagPropWithLayer('cool.tag', 'score'))

                self.true(await node.delTag('bar.tag'))
                self.true(await node.delTag('baz.tag'))

                self.none(node.getTag('bar.tag'))
                self.none(node.getTagProp('bar.tag', 'score'))
                self.eq((None, None), node.getTagPropWithLayer('bar.tag', 'score'))

                self.true(await node.set('asn', 7))
                self.true(await node.pop('asn'))
                self.none(node.get('asn'))
                self.eq((None, None), node.getWithLayer('asn'))

                self.eq('bar', await node.popData('foodata'))

                await core.nodes('for $verb in $lib.range(1001) { $lib.model.ext.addEdge(*, `_a{$verb}`, *, ({})) }')

                manynode = await editor.addNode('it:dev:str', 'manyedges')
                for x in range(1001):
                    await manynode.addEdge(f'_a{str(x)}', node.nid)

                self.eq((None, None), manynode.getTagPropWithLayer('bar.tag', 'score'))

            self.len(0, await alist(nodes[0].iterEdgeVerbs(n2node.nid)))

            async with view2.getEditor() as editor:
                node = await editor.getNodeByBuid(nodes[0].buid)
                self.false(await node.delEdge('_foo', n2nid))
                await node.delEdgesN2()

                self.true(await node.set('asn', 5))

                n2node = await editor.getNodeByNid(n2nid)
                await n2node.delEdgesN2()

                self.false(node.istomb())
                await node.delete()
                self.true(node.istomb())
                await node.delete()

                newnode = await editor.addNode('it:dev:str', 'new')
                self.false(newnode.istomb())
                self.false(await newnode.delEdge('_foo', n2nid))

            self.len(0, await core.nodes('inet:ip=1.2.3.4 <(*)- *', opts=viewopts2))

    async def test_subs_depth(self):

        async with self.getTestCore() as core:
            fqdn = '.'.join(['x' for x in range(300)]) + '.foo.com'
            q = f'[ inet:fqdn="{fqdn}"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].get('zone'), 'foo.com')

    async def test_view_insert_parent_fork(self):

        async with self.getTestCore() as core:

            role = await core.auth.addRole('ninjas')
            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            view00 = core.getView()
            view02 = core.getView((await view00.fork())['iden'])
            view03 = core.getView((await view02.fork())['iden'])

            self.eq(view02.parent, view00)

            self.len(2, view02.layers)
            self.len(3, view03.layers)

            await view00.nodes('[ inet:fqdn=vertex.link ]')
            await view02.nodes('inet:fqdn=vertex.link [ +#foo ]')

            await view02.nodes('auth.user.addrule visi node --gate $lib.view.get().iden')
            await view02.nodes('auth.user.mod visi --admin $lib.true --gate $lib.view.get().iden')
            userrules = visi.getRules(gateiden=view02.iden)

            await view02.nodes('auth.role.addrule ninjas node.add --gate $lib.view.get().iden')
            rolerules = role.getRules(gateiden=view02.iden)

            msgs = await core.stormlist('auth.user.addrule visi node --gate $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)

            opts = {'vars': {'role': role.iden}}
            quorum = await core.callStorm('return($lib.view.get().set(quorum, ({"count": 1, "roles": [$role]})))', opts=opts)

            forkopts = {'view': view02.iden}
            await core.callStorm('return($lib.view.get().setMergeRequest(comment=woot))', opts=forkopts)

            merging = 'return($lib.view.get().getMergingViews()) '
            self.eq([view02.iden], await core.callStorm(merging))

            q = 'return($lib.view.get().insertParentFork(name=staging).iden)'
            newiden = await core.callStorm(q, opts=forkopts)

            self.eq([], await core.callStorm(merging))

            view01 = core.getView(newiden)

            self.ne(view02.parent, view00)
            self.eq(view03.parent, view02)
            self.eq(view02.parent, view01)
            self.eq(view01.parent, view00)

            self.len(2, view01.layers)
            self.len(3, view02.layers)
            self.len(4, view03.layers)
            self.isin(view01.layers[0], view02.layers)
            self.isin(view01.layers[0], view03.layers)

            self.eq(userrules, visi.getRules(gateiden=view01.iden))
            self.eq(rolerules, role.getRules(gateiden=view01.iden))

            nodes = await view01.nodes('inet:fqdn=vertex.link')
            self.none(nodes[0].getTag('foo'))

            await core.nodes('merge --diff --apply', opts=forkopts)

            nodes = await core.nodes('inet:fqdn=vertex.link')
            self.none(nodes[0].getTag('foo'))

            nodes = await view01.nodes('inet:fqdn=vertex.link')
            self.nn(nodes[0].getTag('foo'))

            with self.raises(s_exc.BadState):
                await view00.insertParentFork(visi.iden)

            with self.raises(s_exc.BadState):
                await core.callStorm('return($lib.view.get().insertParentFork().iden)')

    async def test_view_children(self):

        async with self.getTestCore() as core:

            view00 = core.getView()
            view01 = core.getView((await view00.fork())['iden'])
            view02 = core.getView((await view01.fork())['iden'])
            view03 = core.getView((await view01.fork())['iden'])

            q = '''
            $kids = ([])
            for $child in $lib.view.get($iden).children() { $kids.append($child.iden) }
            return($kids)
            '''

            opts = {'vars': {'iden': view00.iden}}
            self.eq([view01.iden], await core.callStorm(q, opts=opts))

            opts['vars']['iden'] = view01.iden
            self.eq([view02.iden, view03.iden], await core.callStorm(q, opts=opts))

            opts['vars']['iden'] = view02.iden
            self.eq([], await core.callStorm(q, opts=opts))
