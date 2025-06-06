import asyncio
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

    async def test_view_nomerge_migration(self):
        async with self.getRegrCore('cortex-defaults-v2') as core:
            view = core.getView('0df16dd693c74109da0d58ab87ba768a')
            self.none(view.info.get('nomerge'))
            self.true(view.info.get('protected'))

            with self.raises(s_exc.CantMergeView):
                await core.callStorm('return($lib.view.get(0df16dd693c74109da0d58ab87ba768a).merge())')
            with self.raises(s_exc.CantDelView):
                await core.callStorm('return($lib.view.del(0df16dd693c74109da0d58ab87ba768a))')

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
            self.len(1, nodes)

            self.eq(4, (await core.getFormCounts()).get('test:int'))
            await self.agenlen(0, view2.eval('test:int=12'))

            # Until we get tombstoning, the child view can't delete a node in the lower layer
            await self.agenlen(1, view2.eval('test:int=10'))

            # Add a node back
            await self.agenlen(1, view2.eval('[ test:int=12 ]'))

            # Add a bunch of test nodes to the view.
            for i in range(20):
                await self.agenlen(1, view2.eval('[test:int=$val]', opts={'vars': {'val': i + 1000}}))

            # Add prop that will only exist in the child
            await alist(view2.eval('test:int=10 [:loc=us]'))
            self.len(1, await alist(view2.eval('test:int=10 +:loc=us')))
            self.len(0, await core.nodes('test:int=10 +:loc=us'))

            # Add tag that will only exist in child
            await alist(view2.eval('test:int=11 [+#foo.bar:score=20]'))
            self.len(1, await alist(view2.eval('test:int=11 +#foo.bar:score=20')))
            self.len(0, await core.nodes('test:int=11 +#foo.bar:score=20'))

            # Add tag prop that will only exist in child
            await alist(view2.eval('test:int=8 [+#faz:score=55]'))
            self.len(1, await alist(view2.eval('test:int=8 +#faz:score=55')))
            self.len(0, await core.nodes('test:int=8 +#faz:score=55'))

            # Add nodedata that will only exist in child
            await alist(view2.eval('test:int=9 $node.data.set(spam, ham)'))
            self.len(1, await view2.callStorm('test:int=9 return($node.data.list())'))
            self.len(0, await core.callStorm('test:int=9 return($node.data.list())'))

            # Add edges that will only exist in the child
            await alist(view2.eval('test:int=9 [ +(refs)> {test:int=10} ]'))
            await alist(view2.eval('test:int=12 [ +(refs)> {test:int=11} ]'))
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
            self.eq(4, (await core.view.getFormCounts()).get('test:int'))

            # Merge the child back into the parent
            await view2.merge()
            await view2.wipeLayer()

            # The parent counts includes all the nodes that were merged
            self.eq(25, (await core.view.getFormCounts()).get('test:int'))

            # A node added to the child is now present in the parent
            nodes = await core.nodes('test:int=12')
            self.len(1, nodes)

            # The child can still see the parent's pre-existing node
            nodes = await view2.nodes('test:int=10')
            self.len(1, nodes)

            # Prop that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=10 +:loc=us'))
            self.len(1, await core.nodes('test:int:loc=us'))

            # Tag that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=11 +#foo.bar:score=20'))
            self.len(1, await core.nodes('test:int#foo.bar'))

            # Tagprop that as only set in child is present in parent
            self.len(1, await core.nodes('test:int=8 +#faz:score=55'))
            self.len(1, await core.nodes('test:int#faz:score=55'))

            # Node data that was only set in child is present in parent
            self.len(1, await core.callStorm('test:int=9 return($node.data.list())'))
            self.len(1, await core.nodes('yield $lib.lift.byNodeData(spam)'))

            # Edge that was only set in child present in parent
            self.len(2, await core.nodes('test:int -(refs)> *'))

            # The child count includes all the nodes in the view
            self.eq(25, (await view2.getFormCounts()).get('test:int'))

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

            # Nodes with a large number of edge edits may be chunked by iterLayerNodeEdits
            await core.nodes('[ test:str=foo ] for $i in $lib.range(102) {[ test:int=$i ]}')

            vdef2 = await core.view.fork()
            opts = {'view': vdef2['iden']}
            await core.nodes('[ test:str=foo +(refs)> { for $i in $lib.range(102) { test:int=$i } } ]', opts=opts)

            strt = core.nexsroot.nexslog.index()
            await core.nodes('$lib.view.get().merge()', opts=opts)

            self.len(102, await core.nodes('test:str=foo -(refs)> test:int'))

            edits = [edit async for edit in core.nexsroot.nexslog.iter(strt)]
            self.len(1, edits)

            nodeedit = edits[0][1][2][0]

            # We should have two chunks of edits for the same buid due to the number of edges
            self.eq(nodeedit[0][0], nodeedit[1][0])
            self.len(100, nodeedit[0][2])
            self.len(2, nodeedit[1][2])

            await core.nodes('[ test:str=lowertag +#a.b=2020]')

            vdef2 = await core.view.fork()
            opts = {'view': vdef2['iden']}
            await core.nodes('test:str=lowertag [ +#a.b.c ]', opts=opts)

            retn = await core.callStorm('test:str=lowertag return($node.getStorNodes())', opts=opts)

            # Only leaf tag is added in our top layer
            self.isin('a.b.c', retn[0].get('tags'))
            self.notin('a.b', retn[0].get('tags'))

            self.isin('a.b', retn[1].get('tags'))

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
            self.eq(seen_maxval, nodes[0].props.get('.seen'))
            nodes = await core.nodes('test:str=maxval', opts=forkopts)
            self.eq(seen_maxval, nodes[0].props.get('.seen'))

            await core.nodes('[ test:str=midval .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=midval [ .seen=2012 ]', opts=forkopts)
            self.eq(seen_midval, nodes[0].props.get('.seen'))
            nodes = await core.nodes('test:str=midval', opts=forkopts)
            self.eq(seen_midval, nodes[0].props.get('.seen'))

            await core.nodes('[ test:str=minval .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=minval [ .seen=2000 ]', opts=forkopts)
            self.eq(seen_minval, nodes[0].props.get('.seen'))
            nodes = await core.nodes('test:str=minval', opts=forkopts)
            self.eq(seen_minval, nodes[0].props.get('.seen'))

            await core.nodes('[ test:str=exival .seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=exival [ .seen=(2000, 2021) ]', opts=forkopts)
            self.eq(seen_exival, nodes[0].props.get('.seen'))
            nodes = await core.nodes('test:str=exival', opts=forkopts)
            self.eq(seen_exival, nodes[0].props.get('.seen'))

            await core.nodes('$lib.view.get().merge()', opts=forkopts)

            nodes = await core.nodes('test:str=maxval')
            self.eq(seen_maxval, nodes[0].props.get('.seen'))

            nodes = await core.nodes('test:str=midval')
            self.eq(seen_midval, nodes[0].props.get('.seen'))

            nodes = await core.nodes('test:str=minval')
            self.eq(seen_minval, nodes[0].props.get('.seen'))

            nodes = await core.nodes('test:str=exival')
            self.eq(seen_exival, nodes[0].props.get('.seen'))

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
            await core.nodes('trigger.add node:del --form inet:ipv4 --query {[test:str=foo]}', opts={'view': view})

            await core.nodes('[ ou:org=* ]')
            self.len(0, await core.nodes('ou:org', opts={'view': view}))

            await core.nodes('[ inet:ipv4=0 ]')
            self.len(0, await core.nodes('inet:ipv4', opts={'view': view}))

            await core.nodes('inet:ipv4=0 | delnode')

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
            self.len(1, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_wipeLayer(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            opts = {
                'vars': {
                    'arrayguid': s_common.guid('arrayguid'),
                },
            }

            await core.addTagProp('score', ('int', {}), {})

            await core.nodes('trigger.add node:del --query { $lib.globals.set(trig, $lib.true) } --form test:str')

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
                    <(seen)+ { test:str=foo }
                    +(seen)> { test:arrayprop=$arrayguid }
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

            self.true(await core.callStorm('return($lib.globals.get(trig))'))

            self.eq({
                'meta:source': 0,
                'syn:tag': 0,
                'test:arrayprop': 0,
                'test:str': 0,
            }, await layr.getFormCounts())

            self.eq(0, layr.layrslab.stat(db=layr.bybuidv3)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.byverb)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.edgesn1)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.edgesn2)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.bytag)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.byprop)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.byarray)['entries'])
            self.eq(0, layr.layrslab.stat(db=layr.bytagprop)['entries'])

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

            # can wipe push/pull/mirror layers

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
                    $pdef = $lyr.addPull(`{$baseurl}/{$baseiden}`)
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
                    $pdef = $lyr.addPush(`{$syncurl}/{$pushiden}`)
                    return($pdef.iden)
                ''', opts=opts)

                await asyncio.wait_for(waitPushOffs(core, pushee_iden, baseoffs), timeout=5)
                self.len(1, await core2.nodes('test:str=chicken', opts={'view': pushee_view}))
                pushee_offs = await core2.getLayer(iden=pushee_layr).getEditOffs()

                mirror_catchup = await core2.getNexsIndx() - 1 + 2 + layr.nodeeditlog.size
                mirror_view, mirror_layr = await core2.callStorm('''
                    $ldef = ({'mirror': `{$baseurl}/{$baseiden}`})
                    $lyr = $lib.layer.add(ldef=$ldef)
                    $view = $lib.view.add(($lyr.iden,))
                    return(($view.iden, $lyr.iden))
                ''', opts=opts)

                self.true(await core2.getLayer(iden=mirror_layr).waitEditOffs(mirror_catchup, timeout=2))
                self.len(1, await core2.nodes('test:str=chicken', opts={'view': mirror_view}))

                # wipe the mirror view which will writeback
                # and then get pushed/pulled into the other layers

                await core2.nodes('$lib.view.get().wipeLayer()', opts={'view': mirror_view})

                self.len(0, await core2.nodes('test:str=chicken', opts={'view': mirror_view}))
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

            nodes = await core.nodes('test:str=foo $node.data.load(foo)')
            self.len(1, nodes)
            self.nn(nodes[0].props.get('.seen'))
            self.nn(nodes[0].tags.get('seen'))
            self.nn(nodes[0].tagprops.get('seen'))
            self.nn(nodes[0].tagprops['seen'].get('score'))
            self.nn(nodes[0].nodedata.get('foo'))

            await core.delUserRule(useriden, (True, ('node', 'tag', 'add')), gateiden=baselayr)

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

            pname = view01.parent.info.get('name')
            vdef = await view01.insertParentFork(visi.iden)
            self.eq(vdef.get('name'), f'inserted fork of {pname}')

            piden = view03.parent.iden
            vdef = await view03.insertParentFork(visi.iden)
            self.eq(vdef.get('name'), f'inserted fork of {piden}')

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
