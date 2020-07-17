import collections

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):

    async def test_view_fork_merge(self):

        async with self.getTestCore() as core:
            await core.nodes('[ test:int=8 +#faz ]')
            await core.nodes('[ test:int=9 test:int=10 ]')
            await core.auth.addUser('visi')
            await core.addTagProp('score', ('int', {}), {})

            self.len(1, await alist(core.eval('test:int=8 +#faz')))
            self.len(2, await alist(core.eval('test:int=9 test:int=10')))
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

            # Add a bunch of nodes to require chunking of splices when merging
            for i in range(1000):
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
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.setLayers([tmpiden]))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.setLayers([tmpiden]))

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
                    await prox.eval('test:int=12', opts={'view': view2.iden}).list()

            # The parent count is correct
            self.eq(4, (await core.view.getFormCounts()).get('test:int'))

            # Merge the child back into the parent
            await view2.merge()

            # The parent counts includes all the nodes that were merged
            self.eq(1005, (await core.view.getFormCounts()).get('test:int'))

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
            self.eq(1005, (await view2.getFormCounts()).get('test:int'))

            # The child can see nodes that got merged
            nodes = await view2.nodes('test:int=12')
            self.len(1, nodes)
            nodes = await view2.nodes('test:int=1000')
            self.len(1, nodes)

            await core.delView(view2.iden)
            await core.view.addLayer(layriden)

            # But not the same layer twice
            await self.asyncraises(s_exc.DupIden, core.view.addLayer(layriden))

    async def test_view_trigger(self):
        async with self.getTestCore() as core:

            # Fork the main view
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')
            view2 = core.getView(view2_iden)

            # A trigger inherited from the main view fires on the forked view when the condition matches
            await core.view.addTrigger({
                'cond': 'node:add',
                'form': 'test:int',
                'storm': '[ test:str=mainhit ]'
            })

            nodes = await alist(core.eval('[ test:int=11 ]', opts={'view': view2.iden}))
            self.len(1, nodes)

            nodes = await alist(view2.eval('test:str'))
            self.len(1, nodes)

            nodes = await alist(core.view.eval('test:str'))
            self.len(0, nodes)

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

            # listTriggers should show view and inherited triggers
            trigs = await view2.listTriggers()
            self.len(2, trigs)

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

            mesgs = await core.stormlist('[test:str=foo2 :hehe=bar]', opts={'editformat': 'splices'})
            count = collections.Counter(m[0] for m in mesgs)
            self.eq(1, count['init'])
            self.eq(1, count['node:add'])
            self.eq(2, count['prop:set'])  # .created and .hehe
            self.eq(0, count['node:edits'])
            self.eq(1, count['node'])
            self.eq(1, count['fini'])

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
