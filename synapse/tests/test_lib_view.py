import os
import asyncio
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):

    async def test_view_readonly(self):
        '''
        On a readonly Cortex, view metadata edits are skipped (the leader owns
        the shared storage): _delMergeMeta makes no durable write, and deleting a
        view fini's it but does not rmtree the shared on-disk storage.
        '''
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                await core.nodes('[ inet:ip=1.2.3.4 ]')

            async with await s_cortex.Cortex.anit(dirn, readonly=True) as core:

                view = core.getView()

                # _delMergeMeta is a no-op on a readonly cortex (no durable write)
                await view._delMergeMeta()

                # deleting a readonly view fini's it but must NOT rmtree the
                # shared storage
                viewdirn = view.dirn
                await view.delete()
                self.true(view.isfini)
                self.true(os.path.isdir(viewdirn))

    async def test_view_protected(self):
        async with self.getTestCore() as core:
            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': forkiden}

            await core.nodes('[ ou:org=* ]', opts=opts)
            await core.nodes('$lib.view.get().set(protected, (true))', opts=opts)

            with self.raises(s_exc.CantMergeView):
                await core.nodes('$lib.view.get().merge()', opts=opts)

            with self.raises(s_exc.CantDelView):
                await core.nodes('$lib.view.del($lib.view.get().iden)', opts=opts)

            await core.nodes('$lib.view.get().set(protected, (false))', opts=opts)
            forkview = core.getView(forkiden)
            await core.nodes('$lib.view.get().merge()', opts=opts)
            self.true(await forkview.waitfini(timeout=5))

            self.len(1, await core.nodes('ou:org'))

            # mop up some coverage issues
            with self.raises(s_exc.BadOptValu):
                await core.view.setViewInfo('hehe', 10)

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

    async def test_view_default_merge_readonly(self):

        # default View.merge() flips the forking layer to read-only for the
        # duration of the background task; the view and its top layer are
        # removed once the merge completes.
        async with self.getTestCore() as core:

            vdef = await core.view.fork()
            view = core.getView(vdef.get('iden'))
            view_iden = view.iden

            await core.nodes('[ test:int=1 test:int=2 ]', opts={'view': view_iden})

            # Suppress background task scheduling so we can observe the
            # mid-merge readonly state before completion races us.
            orig_init = view.initMergeTask
            view.initMergeTask = lambda: asyncio.sleep(0)

            try:
                mergeinfo = await view.merge()
                self.nn(mergeinfo.get('iden'))
                self.true(view.merging)
                self.true(view.wlyr.readonly)

                with self.raises(s_exc.IsReadOnly):
                    await core.nodes('[ test:int=3 ]', opts={'view': view_iden})

            finally:
                view.initMergeTask = orig_init

            await view.initMergeTask()
            self.true(await view.waitfini(timeout=5))

            # View and its top layer are removed by delView + delLayer.
            self.none(core.getView(view_iden))

            self.len(2, await core.nodes('test:int=1 test:int=2'))

    async def test_view_default_merge_resume(self):

        # Mid-merge cell restart should cleanly resume and finish.
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                vdef = await core.view.fork()
                viewiden = vdef.get('iden')
                view = core.getView(viewiden)

                await core.nodes('[ test:int=$x ] for $i in $lib.range(50) {[ test:str=$i ]}',
                                 opts={'view': viewiden, 'vars': {'x': 7}})

                await view.finiMergeTask()  # prevent background task from running

                await view.merge()

                self.true(view.merging)
                self.true(view.wlyr.readonly)

            # Re-open: initServiceActive resumes the merge automatically.
            async with self.getTestCore(dirn=dirn) as core:

                view = core.getView(viewiden)
                if view is not None:
                    self.true(await view.waitfini(timeout=10))
                self.none(core.getView(viewiden))

                self.len(1, await core.nodes('test:int=7'))
                self.len(50, await core.nodes('test:str'))

    async def test_view_children_index(self):

        # view.children() returns the in-memory list maintained alongside
        # info['parent'] mutations. Exercise add / detach / delView /
        # restart paths.
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                mainview = core.view

                vdef1 = await mainview.fork()
                child1 = core.getView(vdef1.get('iden'))
                vdef2 = await mainview.fork()
                child2 = core.getView(vdef2.get('iden'))

                self.sorteq([child1.iden, child2.iden],
                            [v.iden for v in mainview.children()])

                # detach removes from parent.children()
                await child1.detach()
                self.eq((child2,), mainview.children())

                # attach a fresh single-layer view via setViewInfo and
                # confirm it shows up under mainview.children()
                newlyr = await core.addLayer()
                newviewinfo = await core.addView({'layers': (newlyr['iden'],)})
                newview = core.getView(newviewinfo['iden'])
                await newview.setViewInfo('parent', mainview.iden)
                self.isin(newview.iden, [v.iden for v in mainview.children()])

                # delete an intermediate view; its children get re-parented
                middle = core.getView((await mainview.fork())['iden'])
                leaf = core.getView((await middle.fork())['iden'])
                self.eq((leaf,), middle.children())

                middle_iden = middle.iden
                await core.delView(middle_iden)
                self.none(core.getView(middle_iden))
                self.notin(middle_iden, [v.iden for v in mainview.children()])
                self.isin(leaf.iden, [v.iden for v in mainview.children()])

                pre_children = set(v.iden for v in mainview.children())

            # restart: init2 should reconstitute the list from viewdefs
            async with self.getTestCore(dirn=dirn) as core:
                mainview = core.view
                post_children = set(v.iden for v in mainview.children())
                self.eq(pre_children, post_children)

    async def test_view_merge_with_children(self):

        # mergeAllowed no longer rejects views with children; _delView
        # re-parents children to the merged view's parent automatically.
        async with self.getTestCore() as core:

            mainview = core.view
            mid = core.getView((await mainview.fork())['iden'])
            leaf = core.getView((await mid.fork())['iden'])

            await core.nodes('[ ou:org=* :name=mergeme ]', opts={'view': mid.iden})

            self.true(mid.hasKids())

            await mid.merge()
            self.true(await mid.waitfini(timeout=10))

            self.none(core.getView(mid.iden))
            self.eq(mainview.iden, leaf.parent.iden)
            self.isin(leaf, mainview.children())
            self.len(1, await core.nodes('ou:org:name=mergeme'))
            self.notin(mid.wlyr.iden, [lyr.iden for lyr in leaf.layers])

    async def test_view_default_merge_history(self):

        # Non-quorum merges record a hist:merge entry on the parent view.
        async with self.getTestCore() as core:

            user = await core.auth.getUserByName('root')

            vdef = await core.view.fork()
            view = core.getView(vdef.get('iden'))
            view_iden = view.iden

            await core.nodes('[ ou:org=* :name=acme ]', opts={'view': view_iden})

            mergeinfo = await view.merge(useriden=user.iden)
            self.true(await view.waitfini(timeout=5))
            self.none(core.getView(view_iden))

            merges = [m async for m in core.view.getMerges()]
            self.len(1, merges)
            self.eq(merges[0].get('iden'), mergeinfo.get('iden'))
            self.eq(merges[0].get('creator'), user.iden)

    async def test_view_fork_merge(self):

        async with self.getTestCore() as core:
            await core.nodes('[ test:int=8 +#faz ]')
            await core.nodes('[ test:int=9 test:int=10 ]')
            await core.auth.addUser('visi')
            await core.addTagProp('_score', ('int', {}), {})

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
            await alist(view2.eval('test:int=15 [+#faz:_score=55]'))
            self.len(1, await alist(view2.eval('test:int=15 +#faz:_score=55')))
            self.len(0, await core.nodes('test:int=15 +#faz:_score=55'))

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

            # Layer config remains frozen even with a child fork
            layr = await core.addLayer()
            layriden = layr['iden']
            await self.asyncraises(s_exc.SynErr, view2.addLayer(layriden))
            await view3.core.delView(view3.iden)

            async with core.getLocalProxy(user='visi') as prox:
                with self.raises(s_exc.AuthDeny):
                    await prox.count('test:int=12', opts={'view': view2.iden})

            # The parent count is correct
            self.eq(7, (await core.view.getFormCounts()).get('test:int'))

            # Merge the child back into the parent. The merge runs as a
            # background task and ends by removing the forked view and its
            # top layer.
            view2_iden = view2.iden
            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            self.none(core.getView(view2_iden))

            # The parent counts includes all the nodes that were merged
            self.eq(24, (await core.view.getFormCounts()).get('test:int'))

            # A node added to the child is now present in the parent
            nodes = await core.nodes('test:int=12')
            self.len(1, nodes)

            # A node deleted in the child is now deleted in the parent
            nodes = await core.nodes('test:int=11')
            self.len(0, nodes)

            # Prop that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +:loc=us'))
            self.len(1, await core.nodes('test:int:loc=us'))

            # Tag that was only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +#foo.bar'))
            self.len(1, await core.nodes('test:int#foo.bar'))

            # Tagprop that as only set in child is present in parent
            self.len(1, await core.nodes('test:int=15 +#faz:_score=55'))
            self.len(1, await core.nodes('test:int#faz:_score=55'))

            # Node data that was only set in child is present in parent
            self.len(1, await core.callStorm('test:int=15 return($node.data.list())'))
            self.len(1, await core.nodes('yield $lib.lift.byNodeData(spam)'))

            # Edge that was only set in child present in parent
            self.len(2, await core.nodes('test:int -(refs)> *'))

            await core.view.addLayer(layriden)

            # But not the same layer twice
            await self.asyncraises(s_exc.DupIden, core.view.addLayer(layriden))

            # Nodes with a large number of edge edits may be chunked by iterLayerNodeEdits
            await core.nodes('[ test:str=foo ] for $i in $lib.range(102) {[ test:int=$i ]}')

            vdef2 = await core.view.fork()
            opts = {'view': vdef2['iden']}
            await core.nodes('[ test:str=foo +(refs)> { for $i in $lib.range(102) { test:int=$i } } ]', opts=opts)

            strt = core.nexsroot.nexslog.index()
            forkview = core.getView(opts['view'])
            await core.nodes('$lib.view.get().merge()', opts=opts)
            self.true(await forkview.waitfini(timeout=5))

            self.len(102, await core.nodes('test:str=foo -(refs)> test:int'))

            # The runViewMerge background task chunks edits into multiple
            # nexslog 'edits' entries; locate the buid whose edge edits got
            # split into the expected 100/2 sub-chunks by iterLayerNodeEdits.
            edits = collections.defaultdict(list)
            async for _, item in core.nexsroot.nexslog.iter(strt):
                if item[1] != 'edits':
                    continue
                for nid, _, ne in item[2][0]:
                    edits[nid].append(ne)

            self.len(1, [v for v in edits.values() if len(v) == 2 and len(v[0]) == 100 and len(v[1]) == 2])

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

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            forkopts = {'view': forkiden}

            seen_maxval = (s_time.parse('2010'), s_time.parse('2020') + 1, 315532800000001)
            seen_midval = (s_time.parse('2010'), s_time.parse('2015'), 157766400000000)
            seen_minval = (s_time.parse('2000'), s_time.parse('2015'), 473385600000000)
            seen_exival = (s_time.parse('2000'), s_time.parse('2021'), 662774400000000)

            await core.nodes('[ test:str=maxval :seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=maxval [ :seen=2020 ]', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_maxval)
            nodes = await core.nodes('test:str=maxval', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_maxval)

            await core.nodes('[ test:str=midval :seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=midval [ :seen=2012 ]', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_midval)
            nodes = await core.nodes('test:str=midval', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_midval)

            await core.nodes('[ test:str=minval :seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=minval [ :seen=2000 ]', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_minval)
            nodes = await core.nodes('test:str=minval', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_minval)

            await core.nodes('[ test:str=exival :seen=(2010, 2015) ]')

            nodes = await core.nodes('test:str=exival [ :seen=(2000, 2021) ]', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_exival)
            nodes = await core.nodes('test:str=exival', opts=forkopts)
            self.propeq(nodes[0], 'seen', seen_exival)

            # bad type (run before merging since the merge removes the fork)
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('test:str=maxval [ :seen=newp ]', opts=forkopts))
            await core.nodes('test:str=maxval [ :seen?=newp +#foo ]', opts=forkopts)
            self.len(1, await core.nodes('test:str#foo', opts=forkopts))

            forkview = core.getView(forkiden)
            await core.nodes('$lib.view.get().merge()', opts=forkopts)
            self.true(await forkview.waitfini(timeout=5))
            self.none(core.getView(forkiden))

            nodes = await core.nodes('test:str=maxval')
            self.propeq(nodes[0], 'seen', seen_maxval)

            nodes = await core.nodes('test:str=midval')
            self.propeq(nodes[0], 'seen', seen_midval)

            nodes = await core.nodes('test:str=minval')
            self.propeq(nodes[0], 'seen', seen_minval)

            nodes = await core.nodes('test:str=exival')
            self.propeq(nodes[0], 'seen', seen_exival)

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

            view2_iden = view2.iden
            await view2.merge()
            self.true(await view2.waitfini(timeout=5))
            self.none(core.getView(view2_iden))

            # Trigger runs on merged nodes in main view
            self.len(1, await core.view.nodes('test:str=mainhit'))

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
            self.eq([{'count': 1}, {'count': 1}], cmsgs)

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

            msgs = await core.stormlist('[test:str=virts :seen=2020 :polyarry={[test:str=foo1 test:str=foo3]}]')
            cmsgs = [m[1]['edits'] for m in msgs if m[0] == 'node:edits']
            self.eq(cmsgs[1][0][2][0][1][3], {'type': 'ival', 'min': 1577836800000000, 'max': 1577836800000001, 'duration': 1, 'precision': 30})
            virts = cmsgs[2][0][2][0][1][3]
            self.eq(virts['size'], 2)

            msgs = await core.stormlist('[test:guid=* :server=1.2.3.4:80]')
            cmsgs = [m[1]['edits'] for m in msgs if m[0] == 'node:edits']
            self.eq(cmsgs[1][0][2][0][1][3], {'ip': (4, 16909060), 'port': 80, 'type': 'inet:server'})

    async def test_lib_view_addNodeEdits(self):

        async with self.getTestCore() as core:

            view = await core.callStorm('''
                $layr = $lib.layer.add().iden
                $view = $lib.view.add(($layr,))
                return($view.iden)
            ''')
            layr = core.getView().wlyr

            await core.nodes('trigger.add node:add --form ou:org {[+#foo]}', opts={'view': view})

            nodes = await core.nodes('[ ou:org=* ]')
            self.len(0, await core.nodes('ou:org', opts={'view': view}))

            nodeedits = []
            async for offs, edits, meta in layr.syncNodeEdits(0, wait=False):
                nodeedits.append(edits)

            await core.stormlist('''
                $view = $lib.view.get($viewiden)
                for $edits in $nodeedits {
                    $view.addNodeEdits($edits)
                }
            ''', opts={'vars': {'viewiden': view, 'nodeedits': nodeedits}})

            self.len(1, await core.nodes('ou:org +#foo', opts={'view': view}))

            # test node:del triggers
            await core.nodes('trigger.add node:del --form ou:org {[test:str=foo]}', opts={'view': view})

            nextoffs = core.getView(iden=view).layers[0].getEditIndx() + 1

            await core.nodes('ou:org | delnode')

            nodeedits = []
            async for offs, edits, meta in layr.syncNodeEdits(nextoffs, wait=False):
                nodeedits.append(edits)

            await core.stormlist('''
                $view = $lib.view.get($viewiden)
                for $edits in $nodeedits {
                    $view.addNodeEdits($edits)
                }
            ''', opts={'vars': {'viewiden': view, 'nodeedits': nodeedits}})

            self.len(0, await core.nodes('ou:org +#foo', opts={'view': view}))

            self.len(1, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_storNodeEdits(self):

        async with self.getTestCore() as core:

            view = await core.callStorm('''
                $layr = $lib.layer.add().iden
                $view = $lib.view.add(($layr,))
                return($view.iden)
            ''')

            await core.nodes('trigger.add node:add --form ou:org {[+#foo]}', opts={'view': view})
            await core.nodes('trigger.add node:del --form inet:ip {[test:str=foo]}', opts={'view': view})

            await core.nodes('[ ou:org=* ]')
            self.len(0, await core.nodes('ou:org', opts={'view': view}))

            await core.nodes('[ inet:ip=([4, 0]) ]')
            self.len(0, await core.nodes('inet:ip', opts={'view': view}))

            await core.nodes('inet:ip=([4, 0]) | delnode')

            nodeedits = []
            async for offs, edits, meta in core.getView().wlyr.syncNodeEdits(0, wait=False):
                nodeedits.extend(edits)

            user = await core.auth.addUser('user')
            await user.addRule((True, ('view', 'read')))

            async with core.getLocalProxy(share=f'*/view/{view}', user='user') as prox:
                await self.asyncraises(s_exc.AuthDeny, prox.storNodeEdits(nodeedits, None))

            await user.addRule((True, ('node',)))

            async with core.getLocalProxy(share=f'*/view/{view}', user='user') as prox:
                self.none(await prox.storNodeEdits(nodeedits, None))

            self.len(1, await core.nodes('ou:org#foo', opts={'view': view}))
            self.len(0, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_savenodeedits_telepath(self):

        async with self.getTestCore() as core:

            unfo = await core.getUserDefByName('root')
            root = unfo.get('iden')

            view = await core.callStorm('''
                            $layr = $lib.layer.add().iden
                            $view = $lib.view.add(($layr,))
                            return($view.iden)
                        ''')

            await core.nodes('trigger.add node:add --form test:guid {$lib.log.info(`u={$auto.opts.user}`) [+#foo]}', opts={'view': view})
            await core.nodes('trigger.add node:del --form test:int {$lib.log.info(`u={$auto.opts.user}`) [test:str=foo]}', opts={'view': view})

            await core.nodes('[ test:guid=* ]')
            self.len(0, await core.nodes('test:guid', opts={'view': view}))

            await core.nodes('[ test:int=0 ]')
            self.len(0, await core.nodes('test:int', opts={'view': view}))

            await core.nodes('test:int | delnode')

            nodeedits = []
            async for offs, edits, meta in core.getView().wlyr.syncNodeEdits(0, wait=False):
                nodeedits.append(edits)

            user = await core.auth.addUser('user')
            await user.addRule((True, ('view', 'read')))
            guid = s_common.guid()

            async with core.getLocalProxy(share=f'*/view/{view}', user='user') as prox:
                with self.raises(s_exc.AuthDeny):
                    await prox.saveNodeEdits(nodeedits, {})

                await core.setUserAdmin(user.iden, True)

                with self.raises(s_exc.BadArg) as cm:
                    await prox.saveNodeEdits(nodeedits, {})
                self.eq(cm.exception.get('mesg'), "Meta argument requires user key to be a guid, got user=''")

                with self.getLoggerStream('synapse.storm.log') as stream:
                    for edit in nodeedits:
                        await prox.saveNodeEdits(edit, {'time': s_common.now(), 'user': guid})
                    await stream.expect(f'u={guid}', timeout=6)

            self.len(1, await core.nodes('test:guid#foo', opts={'view': view}))
            self.len(1, await core.nodes('test:str=foo', opts={'view': view}))

    async def test_lib_view_wipeLayer(self):

        async with self.getTestCore() as core:

            layr = core.getLayer()

            opts = {
                'vars': {
                    'arrayguid': s_common.guid('arrayguid'),
                },
            }

            await core.addTagProp('_score', ('int', {}), {})

            await core.nodes('trigger.add node:del { $lib.globals.trig = (true) } --form test:str')

            await core.nodes('[ test:str=foo :hehe=hifoo +#test ]')
            await core.nodes('[ test:arrayprop=$arrayguid :strs=(faz, baz) ]', opts=opts)
            await core.nodes('''
                [ test:str=bar
                    :bar={test:str=foo}
                    :tick=2020
                    :hehe=hibar
                    :seen=2021
                    +#test
                    +#test.foo:_score=100
                    <(refs)+ { test:str=foo }
                    +(refs)> { test:arrayprop=$arrayguid }
                ]
                $node.data.set(bardata, ({"hi": "there"}))
            ''', opts=opts)

            nodecnt = await core.count('.created')

            offs = layr.getEditIndx()

            # must have perms for each edit

            user = await core.addUser('redox')
            useriden = user['iden']
            opts = {'user': useriden}

            await self.asyncraises(s_exc.AuthDeny, core.nodes('$lib.view.get().wipeLayer()', opts=opts))

            await core.addUserRule(useriden, (True, ('node', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'prop', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'tag', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'edge', 'del')), gateiden=layr.iden)
            await core.addUserRule(useriden, (True, ('node', 'data', 'del')), gateiden=layr.iden)

            await core.nodes('$lib.view.get().wipeLayer()', opts=opts)

            ecnt = 0
            async for nexsoffs, edits, meta in layr.syncNodeEdits(offs + 1, wait=False):
                ecnt += 1

            self.eq(nodecnt, ecnt) # one del nodeedit for each node

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

            forkview = core.getView(forkviden)
            await core.nodes('view.merge $forkviden', opts={'vars': {'forkviden': forkviden}})
            self.true(await forkview.waitfini(timeout=5))
            self.none(core.getView(forkviden))

            # can wipe through layer push/pull

            self.len(1, await core.nodes('test:str=chicken'))
            baseoffs = layr.getEditIndx()

            async def waitPushOffs(core_, iden_, offs_):
                while True:
                    if core_.layeroffs.get(iden_, -1) >= offs_:
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
                puller_offs = core2.getLayer(iden=puller_layr).getEditIndx()

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
                pushee_offs = core2.getLayer(iden=pushee_layr).getEditIndx()

                nexsoffs = await core.getNexsIndx()
                await core.nodes('$lib.view.get().wipeLayer()')

                self.len(0, await core.nodes('test:str=chicken'))

                await core.waitNexsOffs(nexsoffs + 2, timeout=5)
                self.len(0, await core2.nodes('test:str=chicken', opts={'view': puller_view}))
                self.len(0, await core2.nodes('test:str=chicken', opts={'view': pushee_view}))

    async def test_lib_view_merge_perms(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_score', ('int', {}), {})

            baselayr = core.getLayer().iden

            user = await core.addUser('redox')
            useriden = user['iden']
            useropts = {'user': useriden}

            await core.addUserRule(useriden, (True, ('view', 'fork')))

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)', opts=useropts)
            viewopts = {**useropts, 'view': forkiden}

            q = '''
            [ test:str=foo
                :seen = now
                +#seen:_score = 5
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

            forkview = core.getView(forkiden)
            await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.true(await forkview.waitfini(timeout=5))
            self.none(core.getView(forkiden))

            msgs = await core.stormlist('test:str=foo $node.data.load(foo)')
            podes = [n[1] for n in msgs if n[0] == 'node']
            self.len(1, podes)
            self.nn(podes[0][1]['props'].get('seen'))
            self.nn(podes[0][1]['tags'].get('seen'))
            self.nn(podes[0][1]['tagprops']['seen']['_score'])
            self.nn(podes[0][1]['nodedata'].get('foo'))

            await core.delUserRule(useriden, (True, ('node', 'tag', 'add')), gateiden=baselayr)

            await core.addUserRule(useriden, (True, ('node', 'tag', 'del', 'seen')), gateiden=baselayr)
            await core.addUserRule(useriden, (True, ('node', 'tag', 'add', 'rep', 'foo')), gateiden=baselayr)

            # re-fork now that the successful merge removed the previous view
            forkiden = await core.callStorm('return($lib.view.get().fork().iden)', opts=useropts)
            viewopts = {**useropts, 'view': forkiden}

            await core.nodes('test:str=foo [ -#seen +#rep.foo ]', opts=viewopts)

            forkview = core.getView(forkiden)
            await core.nodes('$lib.view.get().merge()', opts=viewopts)
            self.true(await forkview.waitfini(timeout=5))
            nodes = await core.nodes('test:str=foo')
            self.nn(nodes[0].get('#rep.foo'))

            await core.nodes('test:str=foo [ -#rep ]')

            # MergeCmd (merge --apply) is independent of View.merge() and
            # remains a synchronous pipeline-driven merge that does not
            # remove the fork.
            forkiden = await core.callStorm('return($lib.view.get().fork().iden)', opts=useropts)
            viewopts = {**useropts, 'view': forkiden}
            await core.nodes('test:str=foo [ -#seen +#rep.foo ]', opts=viewopts)
            await core.nodes('test:str=foo | merge --apply', opts=viewopts)
            nodes = await core.nodes('test:str=foo')
            self.nn(nodes[0].get('#rep.foo'))

            # The user lacks node.tag.add.seen on the base layer, so adding
            # a tagprop under #seen in the fork must fail on merge.
            await core.nodes('test:str=foo [ +#seen:_score=99 ]', opts=viewopts)

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=viewopts)

    async def test_lib_view_merge_perms_del(self):
        # The background runViewMerge ends by deleting the forking view
        # and its top layer with no user context, so mergeAllowed
        # pre-checks view.del and layer.del to surface the AuthDeny
        # synchronously to the caller.
        async with self.getTestCore() as core:

            user = await core.addUser('lurker')
            useriden = user['iden']

            # Root-forked view: 'lurker' has no admin grant on either gate.
            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            forkview = core.getView(forkiden)
            forklayriden = forkview.wlyr.iden

            await core.addUserRule(useriden, (True, ('view', 'read')), gateiden=forkiden)
            await core.addUserRule(useriden, (True, ('node',)))

            useropts = {'user': useriden, 'view': forkiden}

            # Initially missing both view.del and layer.del. view.del is
            # checked first so the synchronous AuthDeny names it.
            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=useropts)
            self.eq('view.del', cm.exception.errinfo['perm'])
            self.false(forkview.wlyr.readonly)

            await core.addUserRule(useriden, (True, ('view', 'del')), gateiden=forkiden)

            # Now layer.del is the blocker.
            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes('$lib.view.get().merge()', opts=useropts)
            self.eq('layer.del', cm.exception.errinfo['perm'])
            self.false(forkview.wlyr.readonly)

            await core.addUserRule(useriden, (True, ('layer', 'del')), gateiden=forklayriden)

            # With both perms the merge proceeds.
            await core.nodes('$lib.view.get().merge()', opts=useropts)
            self.true(await forkview.waitfini(timeout=5))
            self.none(core.getView(forkiden))

    async def test_view_protected_merge_gaps(self):
        # mergeAllowed honors view.info['protected'] for the default merge
        # path, but quorum-driven merges and the setViewInfo flag-flip
        # used to slip past it. Verify each gap is now closed.
        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            whippit = await core.auth.addUser('whippit')

            vertex = await core.auth.addRole('vertex')
            await visi.grant(vertex.iden)
            await whippit.grant(vertex.iden)

            await core.auth.allrole.addRule((True, ('view', 'add')))
            await core.auth.allrole.addRule((True, ('view', 'fork')))
            await core.auth.allrole.addRule((True, ('view', 'read')))
            await core.auth.allrole.addRule((True, ('node',)))

            # Enable quorum on the main view so we can exercise the quorum
            # merge code paths.
            await core.callStorm(
                '$lib.view.get().set(quorum, ({"count": 1, "roles": [$role]}))',
                opts={'vars': {'role': vertex.iden}}
            )

            # 1. setMergeRequest refuses on a fork that already has
            # protected set.
            fork00 = await core.callStorm(
                'return($lib.view.get().fork().iden)',
                opts={'user': visi.iden}
            )
            await core.callStorm(
                '$lib.view.get($iden).set(protected, (true))',
                opts={'vars': {'iden': fork00}}
            )
            with self.raises(s_exc.CantMergeView):
                await core.callStorm(
                    '$lib.view.get($iden).setMergeRequest(({}))',
                    opts={'user': visi.iden, 'vars': {'iden': fork00}}
                )

            # 2. setViewInfo('protected', (true)) refuses when a quorum
            # merge request is already pending. The request must survive
            # the refusal.
            fork01 = await core.callStorm(
                'return($lib.view.get().fork().iden)',
                opts={'user': visi.iden}
            )
            await core.callStorm(
                '$lib.view.get($iden).setMergeRequest(({}))',
                opts={'user': visi.iden, 'vars': {'iden': fork01}}
            )
            with self.raises(s_exc.BadState):
                await core.callStorm(
                    '$lib.view.get($iden).set(protected, (true))',
                    opts={'vars': {'iden': fork01}}
                )
            self.nn(core.getView(fork01).getMergeRequest())

            # Drop the quorum so the next fork can use the default merge
            # path. setViewInfo's quorum=None branch will sweep the
            # outstanding fork01 request.
            await core.callStorm('$lib.view.get().set(quorum, (null))')

            # 3. setViewInfo('protected', (true)) refuses while a
            # default merge is in flight.
            fork02 = await core.callStorm('return($lib.view.get().fork().iden)')
            await core.nodes('[ test:int=1 test:int=2 ]', opts={'view': fork02})
            view02 = core.getView(fork02)

            # Suppress the background runViewMerge so view.merging stays
            # True long enough to attempt the protected set.
            orig_init = view02.initMergeTask
            view02.initMergeTask = lambda: asyncio.sleep(0)
            try:
                mergeinfo = await view02.merge()
                self.true(view02.merging)

                # A second merge() while already merging is a no-op that
                # returns the existing merge request rather than the new one.
                again = await view02.merge()
                self.eq(again['iden'], mergeinfo['iden'])
                self.eq(again, view02.getMergeRequest())

                with self.raises(s_exc.BadState):
                    await core.callStorm(
                        '$lib.view.get($iden).set(protected, (true))',
                        opts={'vars': {'iden': fork02}}
                    )

            finally:
                view02.initMergeTask = orig_init

            await view02.initMergeTask()
            self.true(await view02.waitfini(timeout=5))
            self.none(core.getView(fork02))

    async def test_addNodes(self):
        async with self.getTestCore() as core:

            view = core.getView()

            ndefs = ()
            self.len(0, await alist(view.addNodes(ndefs)))

            ndefs = (
                (('test:str', 'hehe'),
                 {'props': {'.created': 5, 'tick': ('test:time', 3)}, 'tags': {'cool': (1, 2)}}, ),
            )
            result = await alist(view.addNodes(ndefs))
            self.len(1, result)

            node = result[0]
            self.propeq(node, 'tick', 3)
            self.ge(node.get('.created', 0), 5)
            self.eq(node.get('#cool'), (1, 2, 1))

            nodes = await alist(view.nodesByPropValu('test:str', '=', 'hehe'))
            self.len(1, nodes)
            self.eq(nodes[0], node)

            # Make sure that we can still add secondary props even if the node already exists
            node2 = await view.addNode('test:str', 'hehe', props={'hehe': 'neato'})
            self.eq(node2, node)
            self.nn(node2.get('hehe'))

            # addNodes with an invalid edge verb to an existing n2 node (covers edge error logging)
            await view.addNode('inet:fqdn', 'vertex.link')
            ndefs = (
                (('test:str', 'edgetest1'), {'edges': (('_badverb', ('inet:fqdn', 'vertex.link')),)}),
            )
            result = await alist(view.addNodes(ndefs))
            self.len(1, result)

            # addNodes with an invalid edge verb to a non-existent n2 node (covers n2adds error logging)
            ndefs = (
                (('test:str', 'edgetest2'), {'edges': (('_badverb', ('inet:fqdn', 'newp.link')),)}),
            )
            result = await alist(view.addNodes(ndefs))
            self.len(1, result)

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

    async def test_view_nodesByPropArray_non_array(self):
        '''
        nodesByPropArray() called directly against a non-array prop raises a
        clean, typed BadCmprType (a comparator/type mismatch, not a bad
        value). No current Storm grammar path reaches this guard live (every
        caller of nodesByPropArray already checks prop.type.isarray first, or
        goes through the permanently-dead getPivLifts pivot-lift branch), so
        it's exercised directly via the View API instead.
        '''
        async with self.getTestCore() as core:

            view = core.getView()
            await view.addNode('test:str', 'hehe')

            with self.raises(s_exc.BadCmprType) as exc:
                await alist(view.nodesByPropArray('test:str', '=', 'hehe'))
            self.isin('Array syntax is invalid on non array type', exc.exception.get('mesg'))

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

            await view0.core.addTagProp('_score', ('int', {}), {})

            self.len(1, await alist(view1.eval('inet:ip=1.2.3.4 [ +#foo:_score=42 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.4 [ +#foo:_score=42 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.4 [ +#foo:_score=99 ]')))
            self.len(1, await alist(view0.eval('inet:ip=1.2.3.5 [ +#foo:_score=43 ]')))

            nodes = await alist(view1.eval('#foo:_score'))
            self.len(2, await alist(view1.eval('#foo:_score')))

    async def test_clearcache(self):

        async with self.getTestCore() as core:

            view = core.getView()

            original_node0 = await view.addNode('test:str', 'node0')
            self.len(1, view.nodecache)
            self.len(1, view.livenodes)
            self.len(0, core.tagnorms)

            await original_node0.addTag('foo.bar.baz')
            self.len(4, view.nodecache)
            self.len(4, view.livenodes)
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
            self.len(0, core.tagnorms)

            # After clearing the cache and lifting nodes, the new node
            # was lifted directly from the layer.
            new_node0 = await view.getNodeByNdef(('test:str', 'node0'))
            self.ne(id(original_node0), id(new_node0))
            self.notin('foo.bar.baz', new_node0.getTags())

            # getNodeByNdef returns None when the form is not in the model
            self.none(await view.getNodeByNdef(('not:a:real:form', 'node0')))

    async def test_cortex_lift_layers_bad_filter_tagprop(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result, with tagprops
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('_score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view0.nodes('[ test:int=10 +#woot:_score=20 ]'))
            self.len(1, await view1.nodes('#woot:_score=20'))
            self.len(1, await view1.nodes('[ test:int=10 +#woot:_score=40 ]'))

            self.len(0, await view0.nodes('#woot:_score=40'))
            self.len(1, await view1.nodes('#woot:_score=40'))

            self.len(1, await view0.nodes('#woot:_score=20'))
            self.len(0, await view1.nodes('#woot:_score=20'))

    async def test_cortex_lift_layers_dup_tagprop(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('_score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view1.nodes('[ test:int=10 +#woot:_score=20 ]'))
            self.len(1, await view0.nodes('[ test:int=10 +#woot:_score=20 ]'))

            self.len(1, await view1.nodes('#woot:_score=20'))

            self.len(1, await view0.nodes('[ test:int=10 +#woot:_score=40 ]'))

    async def test_cortex_lift_layers_ordering(self):

        async with self._getTestCoreMultiLayer() as (view0, view1):

            await view0.core.addTagProp('_score', ('int', {}), {'doc': 'hi there'})
            with self.raises(s_exc.BadPropDef):
                await view0.core.addTagProp('_bad_data', ('data', {}), {})

            await view0.nodes('[ inet:ip=1.1.1.4 ]')
            await view1.nodes('inet:ip=1.1.1.4 [+#tag]')
            await view0.nodes('inet:ip=1.1.1.4 | delnode')
            nodes = await view1.nodes('#tag | uniq')
            self.len(0, nodes)

            await view0.nodes('[ inet:ip=1.1.1.4 :asn=4 +#woot:_score=4] $node.data.set(woot, 4)')
            await view0.nodes('[ inet:ip=1.1.1.1 :asn=1 +#woot:_score=1] $node.data.set(woot, 1)')
            await view1.nodes('[ inet:ip=1.1.1.2 :asn=2 +#woot:_score=2] $node.data.set(woot, 2)')
            await view0.nodes('[ inet:ip=1.1.1.3 :asn=3 +#woot:_score=3] $node.data.set(woot, 3)')

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
                asn = node.get('asn')[1]
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.get('asn')[1]
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.get('asn')[1]
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ip:asn*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                asn = node.get('asn')[1]
                self.lt(asn, last)
                last = asn

            nodes = await view1.nodes('#woot:_score')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', '_score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:_score>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', '_score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:_score*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', '_score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:_score*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                scor = node.getTagProp('woot', '_score')
                self.lt(scor, last)
                last = scor

            nodes = await view1.nodes('yield $lib.lift.byNodeData(woot)')
            self.len(4, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(2, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(4, nodes)

            # test:data form/prop ordering (tagprop #woot:data removed; data type is mutable)
            await view0.nodes('[ test:data=(123) :data=(123) ]')
            await view1.nodes('[ test:data=foo :data=foo ]')
            await view0.nodes('[ test:data=(0) :data=(0) ]')
            await view0.nodes('[ test:data=bar :data=foo ]')

            nodes = await view1.nodes('test:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data=foo')
            self.len(1, nodes)

            nodes = await view1.nodes('test:data:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data:data=foo')
            self.len(2, nodes)

    async def test_node_editor(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'verbs': ('_pwns', '_foo')}}
            await core.nodes('for $verb in $verbs { $lib.model.ext.addEdge(*, $verb, *, ({})) }', opts=opts)

            await core.nodes('$lib.model.ext.addTagProp(_test, (str, ({})), ({}))')
            await core.nodes('[ test:guid=63381924986159aff183f0c85bd8ebad +(refs)> {[ inet:fqdn=vertex.link ]} ]')
            root = core.auth.rootuser

            async with core.view.getEditor() as editor:
                fqdn = await editor.addNode('inet:fqdn', 'vertex.link')
                news = await editor.addNode('test:guid', '63381924986159aff183f0c85bd8ebad')

                self.nn(fqdn.ndef)

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

                self.false(news.hasTagProp('foo', '_test'))
                await news.setTagProp('foo', '_test', 'bar')
                self.true(news.hasTagProp('foo', '_test'))

            async with core.view.getEditor() as editor:
                news = await editor.addNode('test:guid', '63381924986159aff183f0c85bd8ebad')

                self.true(await news.delEdge('_pwns', fqdn.nid))
                self.false(await news.delEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(1, nodeedits)
                self.len(1, nodeedits[0][2])

                self.true(await news.addEdge('_pwns', fqdn.nid))
                nodeedits = editor.getNodeEdits()
                self.len(0, nodeedits)

                self.true(await news.hasData('foo'))

                self.true(news.hasTagProp('foo', '_test'))

                await news.delTagProp('foo', '_test')
                await news.setTagProp('foo', '_test', 'baz')
                await news.setTagProp('foo', '_test', 'bar')
                self.true(news.hasTagProp('foo', '_test'))

                with self.raises(s_exc.NoSuchProp):
                    await news.pop('newp')

                with self.raises(s_exc.NoSuchTagProp):
                    await news.delTagProp('newp', 'newp')

            self.len(1, await core.nodes('test:guid -(_pwns)> *'))

            # test protonode flushEdits for a new node (node=None path)
            async with core.view.getEditor() as editor:
                newnode = await editor.addNode('test:str', 'flushtest')
                self.none(newnode.node)
                await newnode.set('tick', '2020')
                await newnode.flushEdits()
                self.nn(newnode.node)

            self.len(1, await core.nodes('test:str=flushtest'))

            self.len(1, await core.nodes('[ test:ro=foo :writeable=hehe ]'))
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('[ test:ro=foo :readable=haha ]')

            await core.addTagProp('_score', ('int', {}), {})

            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            view2 = core.getView(viewiden2)
            viewopts2 = {'view': viewiden2}

            addq = '''[
            inet:ip=1.2.3.4
                :asn=4
                +#foo.tag=2024
                +#bar.tag:_score=5
                +(_foo)> {[ it:dev:str=n2 ]}
            ]
            $node.data.set(foodata, bar)
            '''
            await core.nodes(addq)
            nodes = await core.nodes('inet:ip=1.2.3.4 [ +#baz.tag:_score=6 ]', opts=viewopts2)

            n2node = (await core.nodes('it:dev:str=n2'))[0]
            n2nid = n2node.nid

            async with view2.getEditor() as editor:
                node = await editor.getNodeByNdef(nodes[0].ndef)
                self.true(await node.delEdge('_foo', n2nid))
                self.true(await node.addEdge('_foo', n2nid))
                self.true(await node.delEdge('_foo', n2nid))

                self.true(await node.setTagProp('cool.tag', '_score', 7))
                self.isin('_score', node.getTagProps('cool.tag'))
                self.isin(('_score', 0), node.getTagPropsWithLayer('cool.tag'))
                self.eq(7, node.getTagProp('cool.tag', '_score'))
                self.eq((7, 0), node.getTagPropWithLayer('cool.tag', '_score'))

                self.true(await node.delTag('bar.tag'))
                self.true(await node.delTag('baz.tag'))

                self.none(node.getTag('bar.tag'))
                self.none(node.getTagProp('bar.tag', '_score'))
                self.eq((None, None), node.getTagPropWithLayer('bar.tag', '_score'))

                self.true(await node.set('asn', 7))
                self.true(await node.pop('asn'))
                self.none(node.get('asn'))
                self.eq((None, None), node.getWithLayer('asn'))

                self.eq('bar', await node.popData('foodata'))

                await core.nodes('for $verb in $lib.range(1001) { $lib.model.ext.addEdge(*, `_a{$verb}`, *, ({})) }')

                manynode = await editor.addNode('it:dev:str', 'manyedges')
                for x in range(1001):
                    await manynode.addEdge(f'_a{str(x)}', node.nid)

                self.eq((None, None), manynode.getTagPropWithLayer('bar.tag', '_score'))

            self.len(0, await alist(nodes[0].iterEdgeVerbs(n2node.nid)))

            async with view2.getEditor() as editor:
                node = await editor.getNodeByNdef(nodes[0].ndef)
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

    async def test_computed_prop_enforcement(self):

        async with self.getTestCore() as core:

            # computed prop cannot be set via storm during node creation
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('[ test:ro=bar :readable=haha ]')

            # computed prop cannot be set via storm post-creation (first write)
            await core.nodes('[ test:ro=bar ]')
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('test:ro=bar [ :readable=haha ]')

            # computed prop cannot be set via view.addNode props= kwarg
            with self.raises(s_exc.ReadOnlyProp):
                await core.view.addNode('test:ro', 'baz', props={'readable': 'haha'})

            # computed prop cannot be set via view.addNodes nodedef props dict
            view = core.getView()
            nodes = await alist(view.addNodes([
                (('test:ro', 'qux'), {'props': {'readable': 'haha'}}),
            ]))
            self.len(1, nodes)
            self.none(nodes[0].get('readable'))

            # writeable prop on same form still works
            nodes = await core.nodes('[ test:ro=foo :writeable=hehe ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'writeable', 'hehe')

            # computed props on comp forms are derived by ctor and cannot be overwritten
            nodes = await core.nodes('[ test:comp=(10, "ten") ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 10)
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('test:comp=(10, "ten") [ :hehe=99 ]')

            # re-creating the same node does not raise ReadOnlyProp
            nodes = await core.nodes('[ test:comp=(10, "ten") ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 10)

            # computed props cannot be deleted via storm prop-del syntax
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('test:comp=(10, "ten") [ -:hehe ]')

            # copying nodes with computed props to a fork does not raise ReadOnlyProp
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')
            msgs = await core.stormlist(f'test:comp=(10, "ten") | copyto {view2_iden}')
            self.stormHasNoWarnErr(msgs)
            nodes = await core.nodes('test:comp=(10, "ten")', opts={'view': view2_iden})
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 10)

    async def test_subs_depth(self):

        async with self.getTestCore() as core:
            fqdn = '.'.join(['x' for x in range(300)]) + '.foo.com'
            q = f'[ inet:fqdn="{fqdn}"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.propeq(nodes[0], 'zone', 'foo.com')

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
            await view02.nodes('auth.user.mod visi --admin (true) --gate $lib.view.get().iden')
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
            self.sorteq([view01.iden], await core.callStorm(q, opts=opts))

            opts['vars']['iden'] = view01.iden
            self.sorteq([view02.iden, view03.iden], await core.callStorm(q, opts=opts))

            opts['vars']['iden'] = view02.iden
            self.sorteq([], await core.callStorm(q, opts=opts))

    async def test_view_propvaluescmpr(self):

        async with self.getTestCore() as core:

            view00 = core.getView()
            view01 = core.getView((await view00.fork())['iden'])

            await core.nodes('[entity:name=foo entity:name=bar entity:name=baz entity:name=faz]')
            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:name,), valu="ba", cmpr="^=")')
            self.len(2, nodes)

            forkopts = {'view': view01.iden}
            await core.nodes('[entity:name=foo2 entity:name=bar2 entity:name=baz2 entity:name=faz2]', opts=forkopts)
            nodes = await core.nodes('yield $lib.lift.byPropRefs(entity:name, valu="ba", cmpr="^=")', opts=forkopts)
            self.len(4, nodes)

            await core.nodes('''[
                (entity:contact=* :names=(bar, baz))
                (ou:org=* :name="bad ship")
                (ou:org=* :name="baz ship")
            ]''')

            await core.nodes('''[
                (entity:contact=* :name=foo)
                (entity:contact=* :name=bar)
                (entity:contact=* :names=(foo, baz))
                (entity:contact=* :names=(bar, bar2))
                (ou:org=* :name=bar)
                (ou:org=* :name="bad ship")
                (ou:org=* :name="awesome ship")
            ]''', opts=forkopts)

            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:contact:name, ou:org:name), valu="ba", cmpr="^=")', opts=forkopts)
            self.len(5, nodes)
            self.eq(['bad ship', 'bar', 'bar2', 'baz', 'baz ship'], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            long1 = 'bar' * 100 + 'a'
            long2 = 'bar' * 100 + 'b'
            await core.nodes(f'''[
                (entity:contact=* :names=({long1},))
                (ou:org=* :name={long2})
            ]''')

            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:contact:name, ou:org:name), valu="ba", cmpr="^=")', opts=forkopts)
            self.len(7, nodes)
            self.eq(['bad ship', 'bar', 'bar2', long1, long2, 'baz', 'baz ship'], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:contact:name, ou:org:name), valu="az", cmpr="~=")', opts=forkopts)
            self.len(2, nodes)
            self.eq(['baz', 'baz ship'], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:contact:name, ou:org:name), valu="^ba", cmpr="~=")', opts=forkopts)
            self.len(7, nodes)
            self.eq(['bad ship', 'bar', 'bar2', long1, long2, 'baz', 'baz ship'], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            nodes = await core.nodes('yield $lib.lift.byPropRefs(entity:name, valu="^bar", cmpr="~=")', opts=forkopts)
            self.len(4, nodes)
            self.eq(['bar', 'bar2', long1, long2], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            # Rip prop values out of sodes to make them undecodable for coverage
            layr = core.getLayer()
            nodes = await core.nodes(f'entity:contact:names*[={long1}]')
            nid = nodes[0].nid

            sode = layr.getStorNode(nid)
            sode['props'].pop('names')
            layr.dirty[nid] = sode

            nodes = await core.nodes(f'ou:org:name={long2}')
            nid = nodes[0].nid

            sode = layr.getStorNode(nid)
            sode['props'].pop('name')
            layr.dirty[nid] = sode

            nodes = await core.nodes('yield $lib.lift.byPropRefs((entity:contact:name, ou:org:name), valu="^ba", cmpr="~=")', opts=forkopts)
            self.len(5, nodes)
            self.eq(['bad ship', 'bar', 'bar2', 'baz', 'baz ship'], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('entity:name', node.form.name)

            with self.raises(s_exc.BadTypeValu):
                async for item in view00.iterPropValuesWithCmpr('entity:name', 'newp', 'newp', array=True):
                    pass

            with self.raises(s_exc.NoSuchCmpr):
                form = core.model.form('entity:name')
                cmprvals = (('newp', None, form.type.stortype),)
                async for item in view00.wlyr.iterPropValuesWithCmpr('entity:name', None, cmprvals):
                    pass

            async for item in view00.iterPropValuesWithCmpr('test:int', '?=', 'newp'):
                self.nn(None)

            async for item in view00.iterPropValuesWithCmpr('test:int', '=', 5):
                self.nn(None)

            with self.raises(s_exc.BadArg):
                await core.nodes('yield $lib.lift.byPropRefs(entity:goal:desc, valu=newp)')

            with self.raises(s_exc.BadArg):
                await core.nodes('yield $lib.lift.byPropRefs((test:comp:hehe, test:int:type), valu=newp)')

            await core.nodes('for $i in $lib.range(10) { [test:int=$i :type=bar] }')

            nodes = await core.nodes('yield $lib.lift.byPropRefs(test:int, valu=3, cmpr="=")', opts=forkopts)
            self.len(1, nodes)
            self.eq(('test:int', 3), nodes[0].ndef)

            nodes = await core.nodes('yield $lib.lift.byPropRefs(test:int, valu=(3, 5), cmpr="range=")', opts=forkopts)
            self.len(3, nodes)
            self.eq([3, 4, 5], [n.valu() for n in nodes])
            for node in nodes:
                self.eq('test:int', node.form.name)

            nodes = await core.nodes('''[
                (test:str=foo :poly={[ test:str=p1 ]})
                (test:str=bar :poly={[ test:int=3 ]})
                (test:str=baz :poly={[ test:hasiface=p2 ]})
                (test:str=faz :poly={[ test:lowstr=p1 ]})
                (test:str=nop :poly={[ test:int=1 ]})
            ]''')

            nodes = await core.nodes('yield $lib.lift.byPropRefs(test:str:poly, valu=p1)', opts=forkopts)
            self.len(2, nodes)
            self.eq(('test:str', 'p1'), nodes[0].ndef)
            self.eq(('test:lowstr', 'p1'), nodes[1].ndef)

            nodes = await core.nodes('yield $lib.lift.byPropRefs(test:str:poly, valu=p, cmpr="^=")', opts=forkopts)
            self.len(3, nodes)
            self.eq(('test:str', 'p1'), nodes[0].ndef)
            self.eq(('test:lowstr', 'p1'), nodes[1].ndef)
            self.eq(('test:hasiface', 'p2'), nodes[2].ndef)

            nodes = await core.nodes('yield $lib.lift.byPropRefs(test:str:poly, valu=(0, 5), cmpr="range=")', opts=forkopts)
            self.len(2, nodes)
            self.eq(('test:int', 1), nodes[0].ndef)
            self.eq(('test:int', 3), nodes[1].ndef)

    async def test_view_getpropvalues_cmpr(self):

        async def collect(genr):
            return [valu async for (indx, valu) in genr]

        async with self.getTestCore() as core:

            view = core.getView()

            await core.nodes('''[
                (test:str=foo :poly={[ test:str=p1 ]})
                (test:str=bar :poly={[ test:int=3 ]})
                (test:str=baz :poly={[ test:hasiface=p2 ]})
                (test:str=faz :poly={[ test:lowstr=p1 ]})
                (test:str=nop :poly={[ test:int=1 ]})
            ]''')

            # a polymorphic property yields (membertype, value) tuples across every member type
            vals = await collect(view.iterPropValuesWithCmpr('test:str:poly', '^=', 'p'))
            self.eq(sorted([('test:hasiface', 'p2'), ('test:lowstr', 'p1'), ('test:str', 'p1')]),
                    sorted(vals))

            # the member-type filter restricts the (index-native) scan to a single member type
            vals = await collect(view.iterPropValuesWithCmpr('test:str:poly', '^=', 'p', types=('test:str',)))
            self.eq([('test:str', 'p1')], vals)

            vals = await collect(view.iterPropValuesWithCmpr('test:str:poly', '^=', 'p', types=('test:hasiface',)))
            self.eq([('test:hasiface', 'p2')], vals)

            # a member type that does not participate yields nothing
            vals = await collect(view.iterPropValuesWithCmpr('test:str:poly', '^=', 'p', types=('newp:newp',)))
            self.eq([], vals)

            # a member-type filter on a non-polymorphic property is rejected rather than yielding nothing
            with self.raises(s_exc.BadArg):
                await collect(view.iterPropValuesWithCmpr('test:str', '^=', 'ba', types=('test:str',)))

            # the limit is applied to the merged, de-duplicated stream
            vals = await collect(view.iterPropValuesWithCmpr('test:str:poly', '^=', 'p', limit=1))
            self.len(1, vals)

            # comparator-aware counts on a plain (non-poly) property (test:str=p1 is the poly target)
            self.eq(6, await view.getPropCount('test:str'))
            self.eq(2, await view.getPropCount('test:str', valu='ba', cmpr='^='))
            self.eq(1, await view.getPropCount('test:str', valu='foo', cmpr='^='))
            self.eq(0, await view.getPropCount('test:str', valu='zzz', cmpr='^='))
            self.eq(1, await view.getPropCount('test:str', valu='bar'))
            self.eq(1, await view.getPropCount('test:str', valu='bar', cmpr='='))

            # only the = and ^= comparators are allowed
            with self.raises(s_exc.BadArg):
                await view.getPropCount('test:str', valu='ba', cmpr='~=')

            with self.raises(s_exc.BadArg):
                await view.getPropCount('test:str', valu='ba', cmpr='range=')

            # ^= counting works for polymorphic props (summed per string member type); cross-check
            # the count against the equivalent lift
            polycnt = await view.getPropCount('test:str:poly', valu='p', cmpr='^=')
            self.eq(polycnt, len(await core.nodes('test:str:poly^=p')))
            self.true(polycnt > 0)

            # the type filter counts only one poly member type's values (from its index slice); no
            # value, works for non-string member stortypes (int) too
            self.eq(5, await view.getPropCount('test:str:poly'))
            self.eq(2, await view.getPropCount('test:str:poly', type='test:int'))
            self.eq(1, await view.getPropCount('test:str:poly', type='test:str'))
            self.eq(1, await view.getPropCount('test:str:poly', type='test:lowstr'))
            # a valid member type with no stored values counts zero
            self.eq(0, await view.getPropCount('test:str:poly', type='inet:server'))

            # the type filter is only for poly props and cannot be combined with a valu
            with self.raises(s_exc.BadArg):
                await view.getPropCount('test:str', type='test:str')

            with self.raises(s_exc.BadArg):
                await view.getPropCount('test:str:poly', valu='p', cmpr='^=', type='test:str')

            # a plain (non-poly) property ^= count routes through getStorCmprs, so a type with no
            # prefix comparator (int) is rejected at the type level, just like a lift would be
            with self.raises(s_exc.NoSuchCmpr):
                await view.getPropCount('test:int', valu='3', cmpr='^=')

            # a non-poly type that does have a ^= cmpr but a non-string stortype (guid) is rejected
            # by the prefix counter, which only scans string indexes
            with self.raises(s_exc.BadArg):
                await view.getPropCount('test:guid', valu='aa', cmpr='^=')

            # a poly with no string-prefix-capable member (fqdn) has no ^= cmpr to count
            with self.raises(s_exc.NoSuchCmpr):
                await view.getPropCount('inet:dns:a:fqdn', valu='v', cmpr='^=')

            # getPolyPropPrefCount rejects a member stortype that is not a plain-string prefix
            with self.raises(s_exc.BadArg):
                await core.getLayer().getPolyPropPrefCount('test:str', 'poly',
                                                           s_layer.STOR_TYPE_GUID, ('test:str',), 'p')

            # a poly prop with no index yet counts as zero (no such abrv)
            self.eq(0, await core.getLayer().getPolyPropPrefCount('test:str', 'newp',
                                                                  s_layer.STOR_TYPE_UTF8, ('test:str',), 'p'))

            # a numeric-looking string prefix normalises and matches like any other string prefix
            await core.nodes('[ test:str=5nine ]')
            self.eq(1, await view.getPropCount('test:str', valu='5', cmpr='^='))

            # type counts are maintained on poly prop edits (not scanned): a delete decrements the
            # member type's slice
            await core.nodes('test:str=nop [ -:poly ]')
            self.eq(4, await view.getPropCount('test:str:poly'))
            self.eq(1, await view.getPropCount('test:str:poly', type='test:int'))

            # overwriting a member with a different type moves the count between slices
            await core.nodes('test:str=foo [ :poly={[ test:int=99 ]} ]')
            self.eq(4, await view.getPropCount('test:str:poly'))
            self.eq(0, await view.getPropCount('test:str:poly', type='test:str'))
            self.eq(2, await view.getPropCount('test:str:poly', type='test:int'))

            # a poly prop with no index yet counts as zero (no such abrv)
            self.eq(0, core.getLayer().getPolyPropTypeCount('test:str', 'newp',
                                                            s_layer.STOR_TYPE_UTF8, ('test:str',)))

    async def test_view_filter_cmprvals_by_type(self):

        async with self.getTestCore() as core:

            view = core.getView()

            poly = s_layer.STOR_FLAG_POLY | s_layer.STOR_TYPE_UTF8
            cmprvals = (
                # a polymorphic cmprval carries member type names and is narrowed to the requested type
                ('^=', ('p', ('test:str', 'test:lowstr')), poly),
                # a homogeneous (non-poly) cmprval carries no member type and is dropped
                ('^=', 'p', s_layer.STOR_TYPE_UTF8),
            )

            self.eq([('^=', ('p', ('test:str',)), poly)],
                    view._filterCmprValsByType(cmprvals, ('test:str',)))

            # nothing matches the requested member type
            self.eq([], view._filterCmprValsByType(cmprvals, ('newp',)))

    async def test_view_edge_counts(self):

        async with self.getTestCore() as core:

            view = core.getView()

            nodes = await core.nodes('[ test:str=cool +(refs)> {[ test:str=n1edge ]} <(refs)+ {[ test:int=2 ]} ]')
            nid = nodes[0].nid
            self.eq(1, view.getEdgeCount(nid))
            self.eq(1, view.getEdgeCount(nid, n2=True))
            self.eq(1, view.getEdgeCount(nid, verb='refs'))

            fork = await core.callStorm('return($lib.view.get().fork().iden)')
            forkview = core.getView(fork)
            forkopts = {'view': fork}
            q = 'test:str=cool [ +(refs)> {[ test:int=1 ]} <(refs)+ {[ test:int=3 ]} ]'
            nodes = await core.nodes(q, opts=forkopts)

            fork2 = await core.callStorm('return($lib.view.get().fork().iden)', opts=forkopts)
            fork2view = core.getView(fork2)
            fork2opts = {'view': fork2}

            # Tombstoning a node clears n1 edges
            nodes = await core.nodes('test:int=2', opts=fork2opts)
            nid = nodes[0].nid
            self.eq(1, fork2view.getEdgeCount(nid))
            self.eq(1, fork2view.getEdgeCount(nid, verb='refs'))

            await core.nodes('test:int=2 | delnode', opts=forkopts)
            await core.nodes('[ test:int=2 ]', opts=fork2opts)
            self.eq(0, fork2view.getEdgeCount(nid))
            self.eq(0, fork2view.getEdgeCount(nid, verb='refs'))

            # Tombstoning a node does not clear n2 edges
            nodes = await core.nodes('test:int=1', opts=fork2opts)
            nid = nodes[0].nid
            self.eq(1, fork2view.getEdgeCount(nid, n2=True))
            self.eq(1, fork2view.getEdgeCount(nid, verb='refs', n2=True))

            nodes = await core.nodes('test:int=1 | delnode --force', opts=forkopts)
            nodes = await core.nodes('[ test:int=1 ]', opts=fork2opts)
            self.eq(1, fork2view.getEdgeCount(nid, n2=True))
            self.eq(1, fork2view.getEdgeCount(nid, verb='refs', n2=True))

    async def test_lib_view_swapLayer(self):

        async with self.getTestCore() as core:

            # Create a node in the default view
            nodes = await core.nodes('[ inet:fqdn=vertex.link ]')
            self.len(1, nodes)

            oldlayr = core.getLayer()
            oldiden = oldlayr.iden

            # Ensure the node is in the view's livenodes cache
            view = core.getView()
            nid = core.getNidByNdef(('inet:fqdn', 'vertex.link'))
            self.nn(nid)
            self.isin(nid, view.livenodes)

            # Swap the layer
            await view.swapLayer()

            # Verify the layer was replaced
            newlayr = core.getLayer()
            self.ne(oldiden, newlayr.iden)

            # Verify view cache was cleared
            self.notin(nid, view.livenodes)

            # Verify the old node is gone from the new layer
            self.len(0, await core.nodes('inet:fqdn=vertex.link'))

            # Verify creating the same node works without ReadOnlyProp error
            nodes = await core.nodes('[ inet:fqdn=vertex.link ]')
            self.len(1, nodes)
            self.eq('vertex.link', nodes[0].ndef[1])
            self.eq(('inet:fqdn', 'link'), nodes[0].get('domain'))

    async def test_view_runt_bad_cmpr(self):
        async with self.getTestCore() as core:
            prop = core.model.prop('syn:type')
            with self.raises(s_exc.BadTypeValu):
                await alist(core.view.getRuntNodes(prop, cmprvalu=('badcmpr', 'test')))
