import asyncio
import pathlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test
from synapse.tests.utils import alist

import synapse.lib.hive as s_hive

tree0 = {
    'kids': {
        'hehe': {'value': 'haha'},
        'hoho': {'value': 'huhu', 'kids': {
            'foo': {'value': 99},
        }},
    }
}

tree1 = {
    'kids': {
        'hoho': {'value': 'huhu', 'kids': {
            'foo': {'value': 99},
        }}
    }
}

class HiveTest(s_test.SynTest):

    async def test_hive_slab(self):

        with self.getTestDir() as dirn:

            async with self.getTestHiveFromDirn(dirn) as hive:

                path = ('foo', 'bar')

                async with await hive.dict(path) as hivedict:

                    self.none(await hivedict.set('hehe', 200))
                    self.none(await hivedict.set('haha', 'hoho'))

                    valus = list(hivedict.values())
                    self.len(2, valus)
                    self.eq(set(valus), {200, 'hoho'})

                    data = {}

                    async def onSetHehe(valu):
                        data['hehe'] = valu

                    self.eq(200, hivedict.get('hehe', onedit=onSetHehe))

                    self.eq(200, await hivedict.set('hehe', 300))

                    self.eq(300, hivedict.get('hehe'))

                    self.eq(300, await hive.get(('foo', 'bar', 'hehe')))
                    self.eq(300, await hive.set(('foo', 'bar', 'hehe'), 400))

                    hivedict.setdefault('lulz', 31337)

                    self.eq(31337, hivedict.get('lulz'))
                    await hivedict.set('lulz', 'boo')
                    items = list(hivedict.items())
                    self.eq([('hehe', 400), ('haha', 'hoho'), ('lulz', 'boo')], items)
                    self.eq('boo', await hivedict.pop('lulz'))
                    self.eq(31337, await hivedict.pop('lulz'))

                    self.eq(None, hivedict.get('nope'))

                    self.eq(s_common.novalu, hivedict.get('nope', default=s_common.novalu))
                    self.eq(s_common.novalu, await hivedict.pop('nope', default=s_common.novalu))

            async with self.getTestHiveFromDirn(dirn) as hive:

                self.eq(400, await hive.get(('foo', 'bar', 'hehe')))
                self.eq('hoho', await hive.get(('foo', 'bar', 'haha')))

                self.none(await hive.get(('foo', 'bar', 'lulz')))

                oneditcount = 0

                def onedit(valu):
                    nonlocal oneditcount
                    oneditcount += 1

                hive.onedit(('baz', 'faz'), onedit)

                await hive.set(('baz',), 400)
                self.eq(0, oneditcount)
                await hive.set(('baz', 'faz'), 401)
                self.eq(1, oneditcount)

    async def test_hive_telepath(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestHiveDmon() as dmon:

            turl = self.getTestUrl(dmon, 'hive')

            async with await s_hive.openurl(turl) as hive0:

                path = ('foo', 'bar')

                evnt = asyncio.Event()

                def onedit(mesg):
                    evnt.set()

                node0 = await hive0.open(path)
                node0.on('hive:set', onedit)

                async with await s_hive.openurl(turl) as hive1:

                    node1 = await hive1.open(path)
                    await node1.set(200)

                    await evnt.wait()

                    self.eq(200, node0.valu)

                    self.eq(201, await node0.add(1))
                    self.eq(202, await node1.add(1))
                    self.eq(203, await node0.add(1))

    async def test_hive_auth(self):

        async with self.getTestTeleHive() as hive:

            node = await hive.open(('hive', 'auth'))

            async with await s_hive.HiveAuth.anit(node) as auth:

                user = await auth.addUser('visi@vertex.link')
                role = await auth.addRole('ninjas')

                self.eq(user, auth.user(user.iden))
                self.eq(user, auth.getUserByName('visi@vertex.link'))

                self.eq(role, auth.role(role.iden))
                self.eq(role, auth.getRoleByName('ninjas'))

                with self.raises(s_exc.DupUserName):
                    await auth.addUser('visi@vertex.link')

                with self.raises(s_exc.DupRoleName):
                    await auth.addRole('ninjas')

                self.nn(user)

                self.false(user.admin)
                self.len(0, user.rules)
                self.len(0, user.roles)

                await user.info.set('admin', True)

                self.true(user.admin)

                self.true(user.allowed(('foo', 'bar')))
                self.false(user.allowed(('foo', 'bar'), elev=False))

                await user.addRule((True, ('foo',)))

                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.len(1, user.permcache)

                await user.delRule((True, ('foo',)))

                self.len(0, user.permcache)
                self.false(user.allowed(('foo', 'bar'), elev=False))

                await user.addRule((True, ('foo',)))

                await user.grant('ninjas')

                self.len(0, user.permcache)

                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.true(user.allowed(('baz', 'faz')))
                self.false(user.allowed(('baz', 'faz'), elev=False))

                self.len(2, user.permcache)

                await role.addRule((True, ('baz', 'faz')))

                self.true(user.allowed(('baz', 'faz'), elev=False))
                self.true(user.allowed(('foo', 'bar'), elev=False))

                self.len(2, user.permcache)

                await user.setLocked(True)

                self.false(user.allowed(('baz', 'faz'), elev=True))
                self.false(user.allowed(('baz', 'faz'), elev=False))

                await user.setLocked(False)

                self.true(user.allowed(('baz', 'faz'), elev=False))
                self.true(user.allowed(('foo', 'bar'), elev=False))

                # Add a DENY to the beginning of the rule list
                await role.addRule((False, ('baz', 'faz')), indx=0)
                self.false(user.allowed(('baz', 'faz'), elev=False))

                # Delete the DENY
                await role.delRuleIndx(0)

                # After deleting, former ALLOW rule applies
                self.true(user.allowed(('baz', 'faz'), elev=False, default='yolo'))

                # non-existent rule returns default
                self.none(user.allowed(('boo', 'foo'), elev=False))
                self.eq('yolo', user.allowed(('boo', 'foo'), elev=False, default='yolo'))

                await self.asyncraises(s_exc.NoSuchRole, user.revoke('accountants'))

                await user.revoke('ninjas')
                self.none(user.allowed(('baz', 'faz'), elev=False))

                await user.grant('ninjas')
                self.true(user.allowed(('baz', 'faz'), elev=False))

                await self.asyncraises(s_exc.NoSuchRole, auth.delRole('accountants'))

                await auth.delRole('ninjas')
                self.false(user.allowed(('baz', 'faz'), elev=False))

                await self.asyncraises(s_exc.NoSuchUser, auth.delUser('fred@accountancy.com'))

                await auth.delUser('visi@vertex.link')
                self.false(user.allowed(('baz', 'faz'), elev=False))

    async def test_hive_dir(self):

        async with self.getTestHive() as hive:

            await hive.open(('foo', 'bar'))
            await hive.open(('foo', 'baz'))
            await hive.open(('foo', 'faz'))

            self.none(hive.dir(('nosuchdir',)))

            self.eq([('foo', None, 3)], list(hive.dir(())))

            await hive.open(('foo',))

            kids = list(hive.dir(('foo',)))

            self.len(3, kids)

            names = list(sorted([name for (name, node, size) in kids]))

            self.eq(names, ('bar', 'baz', 'faz'))

    async def test_hive_pop(self):

        async with self.getTestHive() as hive:

            node = await hive.open(('foo', 'bar'))

            await node.set(20)

            self.none(await hive.pop(('newp',)))

            self.eq(20, await hive.pop(('foo', 'bar')))

            self.none(await hive.get(('foo', 'bar')))

            # Test recursive delete
            node = await hive.open(('foo', 'bar'))
            await node.set(20)

            self.eq(None, await hive.pop(('foo',)))
            self.none(await hive.get(('foo', 'bar')))

    async def test_hive_tele_auth(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestHiveDmon() as dmon:

            hive = dmon.shared.get('hive')

            hive.conf['auth:en'] = True

            auth = await hive.getHiveAuth()

            user = auth.getUserByName('root')
            await user.setPasswd('secret')

            # hive passwords must be non-zero length strings
            with self.raises(s_exc.BadArg):
                await user.setPasswd('')
            with self.raises(s_exc.BadArg):
                await user.setPasswd({'key': 'vau'})

            turl = self.getTestUrl(dmon, 'hive')

            # User can't access after being locked
            await user.setLocked(True)

            with self.raises(s_exc.AuthDeny):
                await s_hive.openurl(turl, user='root', passwd='secret')

            await user.setLocked(False)

            # User can't access after being unlocked with wrong password
            with self.raises(s_exc.AuthDeny):
                await s_hive.openurl(turl, user='root', passwd='newpnewp')

            # User can access with correct password after being unlocked with
            async with await s_hive.openurl(turl, user='root', passwd='secret'):
                await hive.open(('foo', 'bar'))

    async def test_hive_saveload(self):

        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            self.eq('haha', await hive.get(('hehe',)))
            self.eq('huhu', await hive.get(('hoho',)))
            self.eq(99, await hive.get(('hoho', 'foo')))

            await hive.loadHiveTree(tree1, trim=True)
            self.none(await hive.get(('hehe',)))
            self.eq('huhu', await hive.get(('hoho',)))
            self.eq(99, await hive.get(('hoho', 'foo')))

        async with self.getTestHive() as hive:

            node = await hive.open(('hehe', 'haha'))
            await node.set(99)

            tree = await hive.saveHiveTree()

            self.nn(tree['kids']['hehe'])
            self.nn(tree['kids']['hehe']['kids']['haha'])

            self.eq(99, tree['kids']['hehe']['kids']['haha']['value'])

    async def test_hive_authgate_perms(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            await prox.addAuthUser('fred')
            await prox.addAuthUser('bobo')
            await prox.setUserPasswd('fred', 'secret')
            await prox.setUserPasswd('bobo', 'secret')
            view2 = await core.view.fork()
            await alist(core.eval('[test:int=10]'))
            await alist(view2.eval('[test:int=11]'))

            async with core.getLocalProxy(user='fred') as fredcore:
                viewopts = {'view': view2.iden}

                # Rando can access main view but not a fork
                self.eq(1, await fredcore.count('test:int'))

                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int', opts=viewopts))

                viewiden = view2.iden
                layriden = view2.layers[0].iden

                # Add to a non-existent authgate
                rule = (True, ('view', 'read'))
                badiden = 'XXX'
                await self.asyncraises(s_exc.NoSuchAuthGate, prox.addAuthRule('fred', rule, iden=badiden))

                # Rando can access forked view with explicit perms
                await prox.addAuthRule('fred', rule, iden=viewiden)
                self.eq(2, await fredcore.count('test:int', opts=viewopts))

                await prox.addAuthRole('friends')

                # But still can't write to layer
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                # fred can write to forked view's write layer with explicit perm through role

                rule = (True, ('prop:set',))
                await prox.addAuthRule('friends', rule, iden=layriden)

                # Before granting, still fails
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))

                # After granting, succeeds
                await prox.addUserRole('fred', 'friends')
                self.eq(1, await fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

                # But adding a node still fails
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))

                # After removing rule from friends, fails again
                await prox.delAuthRule('friends', rule, iden=layriden)
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                rule = (True, ('node:add',))
                await prox.addAuthRule('fred', rule, iden=layriden)
                self.eq(1, await fredcore.count('[test:int=12]', opts=viewopts))

                # Add an explicit DENY for adding test:int nodes
                rule = (False, ('node:add', 'test:int'))
                await prox.addAuthRule('fred', rule, indx=0, iden=layriden)
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=13]', opts=viewopts))

                # Adding test:str is allowed though
                self.eq(1, await fredcore.count('[test:str=foo]', opts=viewopts))

                # An non-default world readable view works without explicit permission
                view2.worldreadable = True
                self.eq(3, await fredcore.count('test:int', opts=viewopts))

                # Deleting a user that has a role with an Authgate-specific rule
                rule = (True, ('prop:set',))
                await prox.addAuthRule('friends', rule, iden=layriden)
                self.eq(1, await fredcore.count('test:int=11 [:loc=sp]', opts=viewopts))
                await prox.addUserRole('bobo', 'friends')
                await prox.delAuthUser('bobo')
                self.eq(1, await fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                # Deleting a role removes all the authgate-specific role rules
                await prox.delAuthRole('friends')
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

                await view2.fini()
                await view2.trash()

                # Verify that trashing the view deletes the authgate from the hive
                self.none(core.auth.getAuthGate(viewiden))

                # Verify that trashing the write layer deletes the remaining rules and backing store
                wlyr = view2.layers[0]
                await wlyr.fini()
                await wlyr.trash()
                self.false(pathlib.Path(wlyr.dirn).exists())
                rules = core.auth.getUserByName('fred').rules
                self.len(0, rules)

    async def test_hive_auth_persistence(self):
        with self.getTestDir() as fdir:
            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):
                # Set a bunch of permissions
                await prox.addAuthUser('fred')
                await prox.setUserPasswd('fred', 'secret')
                view2 = await core.view.fork()
                await alist(core.eval('[test:int=10] [test:int=11]'))
                viewiden = view2.iden
                layriden = view2.layers[0].iden
                rule = (True, ('view', 'read',))
                await prox.addAuthRule('fred', rule, iden=viewiden)
                await prox.addAuthRole('friends')
                rule = (True, ('prop:set',))
                await prox.addAuthRule('friends', rule, iden=layriden)
                await prox.addUserRole('fred', 'friends')

            # Restart the core/auth and make sure perms work

            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):
                async with core.getLocalProxy(user='fred') as fredcore:
                    viewopts = {'view': view2.iden}
                    self.eq(2, await fredcore.count('test:int', opts=viewopts))
                    self.eq(1, await fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

    async def test_hive_exists(self):
        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            self.true(await hive.exists(('hoho', 'foo')))
            self.false(await hive.exists(('hoho', 'food')))
            self.false(await hive.exists(('newp',)))

    async def test_hive_rename(self):
        async with self.getTestHive() as hive:
            await hive.loadHiveTree(tree0)
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('hehe',), ('hoho',)))
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('newp',), ('newp2',)))
            await self.asyncraises(s_exc.BadHivePath, hive.rename(('hehe',), ('hehe', 'foo')))

            await hive.rename(('hehe',), ('lolo',))
            self.eq('haha', await hive.get(('lolo',)))
            self.false(await hive.exists(('hehe',)))

            await hive.rename(('hoho',), ('jojo',))
            self.false(await hive.exists(('hoho',)))
            jojo = await hive.open(('jojo',))
            self.len(1, jojo.kids)
            self.eq('huhu', jojo.valu)
            self.eq(99, await hive.get(('jojo', 'foo')))
