import collections

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):
    async def test_view_fork_merge(self):
        async with self.getTestCore() as core:
            await core.nodes('[ test:int=10 ]')
            await core.auth.addUser('visi')

            nodes = await alist(core.eval('test:int=10'))
            self.len(1, nodes)
            self.eq(1, (await core.getFormCounts()).get('test:int'))

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
            self.eq(2, (await core.getFormCounts()).get('test:int'))

            # A node added to the child is not seen by the parent
            nodes = await alist(view2.eval('[ test:int=12 ]'))
            self.len(1, nodes)

            nodes = await core.nodes('test:int=12')
            self.len(0, nodes)
            self.eq(2, (await core.view.getFormCounts()).get('test:int'))

            # Deleting nodes from the child view should not affect the main
            await alist(view2.eval('test:int | delnode'))

            self.eq(2, (await core.view.getFormCounts()).get('test:int'))
            nodes = await alist(view2.eval('test:int=10'))
            self.len(1, nodes)

            self.eq(2, (await core.getFormCounts()).get('test:int'))
            await self.agenlen(0, view2.eval('test:int=12'))

            # Until we get tombstoning, the child view can't delete a node in the lower layer
            await self.agenlen(1, view2.eval('test:int=10'))

            # Add a node back
            await self.agenlen(1, view2.eval('[ test:int=12 ]'))

            # Add a bunch of nodes to require chunking of splices when merging
            for i in range(1000):
                await self.agenlen(1, view2.eval('[test:int=$val]', opts={'vars': {'val': i + 1000}}))

            # Forker and forkee have their layer configuration frozen
            tmpiden = await core.addLayer()
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

            # You can't delete a view or merge it if it has children
            vdef3 = await view2.fork()
            view3_iden = vdef3.get('iden')
            view3 = core.getView(view3_iden)

            await self.asyncraises(s_exc.SynErr, view2.merge())
            await self.asyncraises(s_exc.SynErr, view2.core.delView(view2.iden))
            await view3.core.delView(view3.iden)

            async with core.getLocalProxy(user='visi') as prox:
                with self.raises(s_exc.AuthDeny):
                    await prox.eval('test:int=12', opts={'view': view2.iden}).list()

            # Merge the child back into the parent
            await view2.merge()

            # Now, the node added to the child is seen in the parent
            nodes = await core.nodes('test:int=12')
            self.len(1, nodes)

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
