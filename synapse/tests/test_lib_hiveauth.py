import pathlib

import synapse.exc as s_exc

import synapse.tests.utils as s_test
from synapse.tests.utils import alist

import synapse.lib.hive as s_hive
import synapse.lib.hiveauth as s_hiveauth

class AuthTest(s_test.SynTest):

    async def test_hive_auth(self):

        async with self.getTestTeleHive() as hive:

            node = await hive.open(('hive', 'auth'))

            async with await s_hiveauth.Auth.anit(node) as auth:

                user = await auth.addUser('visi@vertex.link')
                role = await auth.addRole('ninjas')

                self.eq(user, auth.user(user.iden))
                self.eq(user, await auth.getUserByName('visi@vertex.link'))

                self.eq(role, auth.role(role.iden))
                self.eq(role, await auth.getRoleByName('ninjas'))

                with self.raises(s_exc.DupUserName):
                    await auth.addUser('visi@vertex.link')

                with self.raises(s_exc.DupRoleName):
                    await auth.addRole('ninjas')

                self.nn(user)

                self.false(user.info.get('admin'))
                self.len(0, user.info.get('rules'))
                self.len(1, user.info.get('roles'))

                await user.setAdmin(True)
                self.true(user.info.get('admin'))

                self.true(user.allowed(('foo', 'bar')))

                await user.addRule((True, ('foo',)))

                self.true(user.allowed(('foo', 'bar')))

                self.len(1, user.permcache)

                await user.delRule((True, ('foo',)))

                self.len(0, user.permcache)

                await user.addRule((True, ('foo',)))

                await user.grant(role.iden)

                self.len(0, user.permcache)

                self.true(user.allowed(('baz', 'faz')))

                self.len(1, user.permcache)

                await role.addRule((True, ('baz', 'faz')))

                self.len(0, user.permcache)

                self.true(user.allowed(('baz', 'faz')))

                self.len(1, user.permcache)

                await user.setLocked(True)

                self.false(user.allowed(('baz', 'faz')))

                await user.setAdmin(False)
                await user.setLocked(False)

                self.true(user.allowed(('baz', 'faz')))
                self.true(user.allowed(('foo', 'bar')))

                # Add a DENY to the beginning of the rule list
                await role.addRule((False, ('baz', 'faz')), indx=0)
                self.false(user.allowed(('baz', 'faz')))

                # Delete the DENY
                await role.delRule((False, ('baz', 'faz')))

                # After deleting, former ALLOW rule applies
                self.true(user.allowed(('baz', 'faz')))

                # non-existent rule returns default
                self.none(user.allowed(('boo', 'foo')))
                self.eq('yolo', user.allowed(('boo', 'foo'), default='yolo'))

                await self.asyncraises(s_exc.NoSuchRole, user.revoke('newp'))

                await user.revoke(role.iden)
                self.none(user.allowed(('baz', 'faz')))

                await user.grant(role.iden)
                self.true(user.allowed(('baz', 'faz')))

                await self.asyncraises(s_exc.NoSuchRole, auth.delRole('accountants'))

                await auth.delRole(role.iden)
                self.false(user.allowed(('baz', 'faz')))

                await self.asyncraises(s_exc.NoSuchUser, auth.delUser('fred@accountancy.com'))

                await auth.delUser(user.iden)
                self.false(user.allowed(('baz', 'faz')))

                role = await auth.addRole('lolusers')
                role2 = await auth.addRole('lolusers2')

                self.none(await role.setName('lolusers'))

                with self.raises(s_exc.DupRoleName):
                    await role2.setName('lolusers')

                await role.setName('roflusers')

                self.nn(await auth.getRoleByName('roflusers'))
                self.none(await auth.getRoleByName('lolusers'))

                user = await auth.addUser('user1')
                user2 = await auth.addUser('user')

                # No problem if the user sets her own name to herself
                self.none(await user.setName('user1'))

                with self.raises(s_exc.DupUserName):
                    await user2.setName('user1')

                await user.setName('user2')

                self.nn(await auth.getUserByName('user2'))
                self.none(await auth.getUserByName('user1'))

    async def test_hive_tele_auth(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestHiveDmon() as dmon:

            hive = dmon.shared.get('hive')

            hive.conf['auth:en'] = True

            auth = await hive.getHiveAuth()

            user = await auth.getUserByName('root')
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

    async def test_hive_authgate_perms(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            # We can retrieve the hivegate information
            gate = await prox.getAuthGate(core.view.iden)
            self.eq(gate['users'][0], {
                'iden': core.auth.rootuser.iden,
                'admin': True,
                'rules': (),
            })

            gates = await prox.getAuthGates()
            self.isin(core.view.iden, [g['iden'] for g in gates])

            fred = await prox.addUser('fred')
            bobo = await prox.addUser('bobo')
            await prox.setUserPasswd(fred['iden'], 'secret')
            await prox.setUserPasswd(bobo['iden'], 'secret')

            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')

            view2 = core.getView(view2_iden)

            await core.nodes('[test:int=10]')
            await view2.nodes('[test:int=11]')

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
                await self.asyncraises(s_exc.NoSuchAuthGate, prox.addUserRule(fred['iden'], rule, gateiden=badiden))

                # Rando can access forked view with explicit perms
                await prox.addUserRule(fred['iden'], rule, gateiden=viewiden)
                self.eq(2, await fredcore.count('test:int', opts=viewopts))

                friends = await prox.addRole('friends')

                # But still can't write to layer
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                # fred can write to forked view's write layer with explicit perm through role

                rule = (True, ('node', 'prop', 'set',))
                await prox.addRoleRule(friends['iden'], rule, gateiden=layriden)

                # Before granting, still fails
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))

                # After granting, succeeds
                await prox.addUserRole(fred['iden'], friends['iden'])
                self.eq(1, await fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

                # But adding a node still fails
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=12]', opts=viewopts))

                # After removing rule from friends, fails again
                await prox.delRoleRule(friends['iden'], rule, gateiden=layriden)
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                rule = (True, ('node', 'add',))
                await prox.addUserRule(fred['iden'], rule, gateiden=layriden)
                self.eq(1, await fredcore.count('[test:int=12]', opts=viewopts))

                # Add an explicit DENY for adding test:int nodes
                rule = (False, ('node', 'add', 'test:int'))
                await prox.addUserRule(fred['iden'], rule, indx=0, gateiden=layriden)
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('[test:int=13]', opts=viewopts))

                # Adding test:str is allowed though
                self.eq(1, await fredcore.count('[test:str=foo]', opts=viewopts))

                # An non-default world readable view works without explicit permission
                view2.worldreadable = True
                self.eq(3, await fredcore.count('test:int', opts=viewopts))

                # Deleting a user that has a role with an Authgate-specific rule
                rule = (True, ('node', 'prop', 'set',))
                await prox.addRoleRule(friends['iden'], rule, gateiden=layriden)
                self.eq(1, await fredcore.count('test:int=11 [:loc=sp]', opts=viewopts))
                await prox.addUserRole(bobo['iden'], friends['iden'])
                await prox.delAuthUser(bobo['iden'])
                self.eq(1, await fredcore.count('test:int=11 [:loc=us]', opts=viewopts))

                # Deleting a role removes all the authgate-specific role rules
                await prox.delRole(friends['iden'])
                await self.asyncraises(s_exc.AuthDeny, fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

                wlyr = view2.layers[0]

                await core.delView(view2.iden)
                await core.delLayer(wlyr.iden)

                # Verify that trashing the layer and view deletes the authgate from the hive
                self.none(core.auth.getAuthGate(wlyr.iden))
                self.none(core.auth.getAuthGate(view2.iden))

                # Verify that trashing the write layer deletes the remaining rules and backing store
                self.false(pathlib.Path(wlyr.dirn).exists())
                fred = await core.auth.getUserByName('fred')

                self.len(0, fred.getRules(gateiden=wlyr.iden))
                self.len(0, fred.getRules(gateiden=view2.iden))

    async def test_hive_auth_persistence(self):

        with self.getTestDir() as fdir:

            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):

                # Set a bunch of permissions
                fred = await prox.addUser('fred')
                await prox.setUserPasswd(fred['iden'], 'secret')

                vdef2 = await core.view.fork()
                view2_iden = vdef2.get('iden')
                view2 = core.getView(view2_iden)

                await alist(core.eval('[test:int=10] [test:int=11]'))
                viewiden = view2.iden
                layriden = view2.layers[0].iden
                rule = (True, ('view', 'read',))
                await prox.addUserRule(fred['iden'], rule, gateiden=viewiden)
                friends = await prox.addAuthRole('friends')
                rule = (True, ('node', 'prop', 'set',))
                await prox.addRoleRule(friends['iden'], rule, gateiden=layriden)
                await prox.addUserRole(fred['iden'], friends['iden'])

            # Restart the core/auth and make sure perms work

            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):
                async with core.getLocalProxy(user='fred') as fredcore:
                    viewopts = {'view': view2.iden}
                    self.eq(2, await fredcore.count('test:int', opts=viewopts))
                    self.eq(1, await fredcore.count('test:int=11 [:loc=ru]', opts=viewopts))

                await core.auth.delUser(fred['iden'])
                await core.auth.delRole(friends['iden'])

                self.none(await core.auth.getUserByName('fred'))
                self.none(await core.auth.getRoleByName('friends'))

            #restart after user/role removal and test they stayed gone
            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):
                self.none(await core.auth.getUserByName('fred'))
                self.none(await core.auth.getRoleByName('friends'))
