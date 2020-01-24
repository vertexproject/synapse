import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):
    async def test_view_fork_merge(self):
        async with self.getTestCore() as core:
            await core.nodes('[ test:int=10 ]')
            nodes = await alist(core.eval('test:int=10'))
            self.len(1, nodes)
            self.eq(1, core.counts.get('test:int'))

            # Fork the main view
            view2 = await core.view.fork()

            # The new view has the same nodes as the old view
            nodes = await alist(view2.eval('test:int=10'))
            self.len(1, nodes)

            await core.nodes('[ test:int=11 ]')

            # A node added to the parent after the fork is still seen by the child
            nodes = await alist(view2.eval('test:int=11'))
            self.len(1, nodes)
            self.eq(2, core.counts.get('test:int'))

            # A node added to the child is not seen by the parent
            nodes = await alist(view2.eval('[ test:int=12 ]'))
            self.len(1, nodes)

            nodes = await core.nodes('test:int=12')
            self.len(0, nodes)
            self.eq(2, core.counts.get('test:int'))

            # Deleting nodes from the child view should not affect the main
            await alist(view2.eval('test:int | delnode'))
            self.eq(2, core.counts.get('test:int'))
            await self.agenlen(0, view2.eval('test:int=12'))

            # Until we get tombstoning, the child view can't delete a node in the lower layer
            await self.agenlen(1, view2.eval('test:int=10'))

            # Add a node back
            await self.agenlen(1, view2.eval('[ test:int=12 ]'))

            # Add a bunch of nodes to require chunking of splices when merging
            for i in range(1000):
                await self.agenlen(1, view2.eval('[test:int=$val]', opts={'vars': {'val': i + 1000}}))

            # Forker and forkee have their layer configuration frozen
            tmplayr = await core.addLayer()
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.addLayer(tmplayr))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.addLayer(tmplayr))
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.setLayers([tmplayr]))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.setLayers([tmplayr]))

            # You can't merge a non-forked view
            await self.asyncraises(s_exc.SynErr, view2.core.view.merge())

            # You can't merge if the parent's write layer is readonly
            view2.parent.layers[0].readonly = True
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.merge())
            view2.parent.layers[0].readonly = False

            # You can't delete a view or merge it if it has children
            view3 = await view2.fork()
            await self.asyncraises(s_exc.SynErr, view2.merge())
            await self.asyncraises(s_exc.SynErr, view2.core.delView(view2.iden))
            await view3.core.delView(view3.iden)

            # Merge the child back into the parent
            await view2.merge()

            # Now, the node added to the child is seen in the parent
            nodes = await core.nodes('test:int=12')
            self.len(1, nodes)

    async def test_view_trigger(self):
        async with self.getTestCore() as core:
            # Fork the main view
            view2 = await core.view.fork()

            # A trigger inherited from the main view fires on the forked view when the condition matches
            await core.addTrigger('node:add', '[ test:str=mainhit ]', info={'form': 'test:int'})
            nodes = await alist(core.eval('[ test:int=11 ]', opts={'view': view2.iden}))
            self.len(1, nodes)

            nodes = await alist(view2.eval('test:str'))
            self.len(1, nodes)

            nodes = await alist(core.view.eval('test:str'))
            self.len(0, nodes)

            # A trigger on the child view fires on the child view but not the main view
            await view2.addTrigger('node:add', '[ test:str=forkhit ]', info={'form': 'test:int'})
            nodes = await alist(view2.eval('[ test:int=12 ]'))

            nodes = await view2.nodes('test:str=forkhit')
            self.len(1, nodes)

            nodes = await alist(core.view.eval('test:str=forkhit'))
            self.len(0, nodes)

            # listTriggers should show view and inherited triggers
            trigs = await view2.listTriggers()
            self.len(2, trigs)

            await view2.fini()
            await view2.trash()
