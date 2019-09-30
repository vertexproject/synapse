import pathlib

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ViewTest(s_t_utils.SynTest):
    async def test_view_fork(self):
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
            nodes = await alist(view2.eval('test:int=10'))
            self.len(1, nodes)

            # Forker and forkee have their layer configuration frozen
            tmplayr = await core.addLayer()
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.addLayer(tmplayr))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.addLayer(tmplayr))
            await self.asyncraises(s_exc.ReadOnlyLayer, core.view.setLayers([tmplayr]))
            await self.asyncraises(s_exc.ReadOnlyLayer, view2.setLayers([tmplayr]))

            await core.delView(view2.iden)

    async def test_view_perms(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            await prox.addAuthUser('fred')
            await prox.setUserPasswd('fred', 'secret')
            view2 = await core.view.fork()
            await alist(core.eval('[test:int=10]'))
            await alist(view2.eval('[test:int=11]'))

            async with core.getLocalProxy(user='fred') as fredcore:
                viewopts = {'view': view2.iden}

                # Rando can access main view but not a fork
                self.eq(1, await fredcore.count('test:int'))

                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int', opts=viewopts))

                viewtupl = ('View', view2.iden)
                layrtupl = ('LmdbLayer', view2.layers[0].iden)

                # Rando can access forked view with explicit perms
                rule = {'allow': True, 'path': ('read', ), 'entitupl': viewtupl}
                await prox.addAuthRule('fred', rule)
                self.eq(2, await fredcore.count('test:int', opts=viewopts))

                # But still can't write to layer
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                # Rando can write to forked view's write layer with explicit perm
                rule = {'allow': True, 'path': ('prop:set', ), 'entitupl': layrtupl}
                await prox.addAuthRule('fred', rule)

                self.eq(1, await fredcore.count('test:int=11 [:loc=us]', opts=viewopts))
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))

                rule = {'allow': True, 'path': ('node:add', ), 'entitupl': layrtupl}
                await prox.addAuthRule('fred', rule)
                self.eq(1, await fredcore.count('[test:int=12]', opts=viewopts))

                # Add an explicit DENY for adding test:int nodes
                rule = {'allow': False, 'path': ('node:add', 'test:int'), 'entitupl': layrtupl}
                await prox.addAuthRule('fred', rule, indx=0)
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=13]', opts=viewopts))

                # Adding test:str is allowed though
                self.eq(1, await fredcore.count('[test:str=foo]', opts=viewopts))

                # An non-default world readable view works without explicit permission
                view2.worldreadable = True
                self.eq(3, await fredcore.count('test:int', opts=viewopts))

                await view2.fini()

                await view2.trash(core.auth)

                self.false(pathlib.Path(view2.layers[0].dirn).exists())

                # All of fred's rules are related to the new view, so there should be none left after trashing
                rules = core.auth.getUserByName('fred').rules
                self.len(0, rules)

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
            trigs = view2.listTriggers()
            self.len(2, trigs)
