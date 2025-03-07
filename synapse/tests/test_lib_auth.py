import string
import pathlib

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.auth as s_auth
import synapse.lib.cell as s_cell
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_test


class AuthTest(s_test.SynTest):

    async def test_auth(self):

        async with self.getTestCore() as core:

            auth = core.auth

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

            viewiden = core.getView().iden
            with self.raises(s_exc.DupIden):
                await auth.addUser('view', iden=viewiden)

            with self.raises(s_exc.NoSuchUser):
                await auth.delUser(viewiden)
            self.nn(core.auth.getAuthGate(viewiden))

            with self.raises(s_exc.DupIden):
                await auth.addRole('view', iden=viewiden)

            with self.raises(s_exc.NoSuchRole):
                await auth.delRole(viewiden)
            self.nn(core.auth.getAuthGate(viewiden))

            self.none(await auth._addUser(user.iden, 'visi@vertex.link'))
            self.none(await auth._addRole(user.iden, 'ninjas'))

            self.nn(user)

            with self.raises(s_exc.AuthDeny):
                user.reqAdmin()

            with self.raises(s_exc.AuthDeny):
                user.reqAdmin(gateiden='newp')

            self.false(user.info.get('admin'))
            self.len(0, user.info.get('rules'))
            self.len(1, user.info.get('roles'))

            await user.setAdmin(True)
            self.true(user.info.get('admin'))
            self.true(user.allowed(('foo', 'bar')))
            user.reqAdmin()

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
            # second revoke does nothing
            await user.revoke(role.iden)

            await user.grant(role.iden)
            self.true(user.allowed(('baz', 'faz')))
            # second grant does nothing
            await user.grant(role.iden)

            await self.asyncraises(s_exc.NoSuchRole, auth.delRole('accountants'))

            await auth.delRole(role.iden)
            self.false(user.allowed(('baz', 'faz')))

            await self.asyncraises(s_exc.NoSuchUser, auth.delUser('fred@accountancy.com'))

            await auth.delUser(user.iden)
            self.false(user.allowed(('baz', 'faz')))

            self.none(await auth._delUser(user.iden))

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

            with self.raises(s_exc.NoSuchRole):
                await auth.reqRoleByName('newp')

            with self.raises(s_exc.NoSuchAuthGate):
                await auth.delAuthGate('newp')

            with self.raises(s_exc.InconsistentStorage):
                await auth.addAuthGate(core.view.iden, 'newp')

    async def test_hive_tele_auth(self):

        # confirm that the primitives used by higher level APIs
        # work using telepath remotes and property synchronize.

        async with self.getTestCore() as core:

            addr, port = await core.dmon.listen('tcp://127.0.0.1:0')

            auth = core.auth

            user = await auth.addUser('lowuser')
            await user.setPasswd('secret')

            # tryPasswd
            self.true(await user.tryPasswd('secret'))
            self.false(await user.tryPasswd('beep'))
            self.false(await user.tryPasswd(None))

            # passwords must be non-zero length strings
            with self.raises(s_exc.BadArg):
                await user.setPasswd('')
            with self.raises(s_exc.BadArg):
                await user.setPasswd({'key': 'vau'})

            # passwords can be set to none, preventing tryPasswd from working
            await user.setPasswd(None)
            self.false(await user.tryPasswd(None))
            self.false(await user.tryPasswd('beep'))
            self.false(await user.tryPasswd('secret'))

            # Reset the password
            await user.setPasswd('secret')

            turl = f'tcp://127.0.0.1:{port}'

            # User can't access after being locked
            await user.setLocked(True)

            with self.raises(s_exc.AuthDeny):
                await s_telepath.openurl(turl, user='lowuser', passwd='secret')

            await user.setLocked(False)

            # User can't access after being unlocked with wrong password
            with self.raises(s_exc.AuthDeny):
                await s_telepath.openurl(turl, user='lowuser', passwd='newpnewp')

            # User can access with correct password after being unlocked with
            async with await s_telepath.openurl(turl, user='lowuser', passwd='secret') as proxy:
                await proxy.getCellInfo()

    async def test_authgate_perms(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            # We can retrieve the authgate information
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

                friends = await prox.addRole('friends')
                await prox.addRoleRule(friends['iden'], rule, gateiden=layriden)

                friends = await prox.getRoleInfo('friends')
                self.isin(layriden, friends['authgates'])

                wlyr = view2.layers[0]

                await core.delView(view2.iden)
                await core.delLayer(wlyr.iden)

                # Verify that trashing the layer and view deletes the authgate
                self.none(core.auth.getAuthGate(wlyr.iden))
                self.none(core.auth.getAuthGate(view2.iden))

                friends = await prox.getRoleInfo('friends')
                self.notin(layriden, friends['authgates'])

                # Verify that trashing the write layer deletes the remaining rules and backing store
                self.false(pathlib.Path(wlyr.dirn).exists())
                fred = await core.auth.getUserByName('fred')

                self.len(0, fred.getRules(gateiden=wlyr.iden))
                self.len(0, fred.getRules(gateiden=view2.iden))

    async def test_auth_persistence(self):

        with self.getTestDir() as fdir:

            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):

                # Set a bunch of permissions
                fred = await prox.addUser('fred')
                await prox.setUserPasswd(fred['iden'], 'secret')

                vdef2 = await core.view.fork()
                view2_iden = vdef2.get('iden')
                view2 = core.getView(view2_iden)

                await core.nodes('[test:int=10] [test:int=11]')
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

            # restart after user/role removal and test they stayed gone
            async with self.getTestCoreAndProxy(dirn=fdir) as (core, prox):
                self.none(await core.auth.getUserByName('fred'))
                self.none(await core.auth.getRoleByName('friends'))

    async def test_auth_invalid(self):

        async with self.getTestCore() as core:
            with self.raises(s_exc.BadArg):
                await core.auth.setRoleName(core.auth.allrole.iden, 'ninjas')
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setName(1)
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setName('secretroot')
            with self.raises(s_exc.BadArg):
                await core.auth.allrole.setName(1)
            with self.raises(s_exc.BadArg):
                await core.auth.allrole.setName('nobody')
            with self.raises(s_exc.SchemaViolation):
                await core.auth.rootuser.addRule('vi.si')
            with self.raises(s_exc.SchemaViolation):
                await core.auth.rootuser.setRules(None)
            with self.raises(s_exc.SchemaViolation):
                await core.auth.allrole.setRules(None)
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setAdmin('lol')
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setAdmin(False)
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setLocked('lol')
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setLocked(True)
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setArchived('lol')
            with self.raises(s_exc.BadArg):
                await core.auth.rootuser.setArchived(True)
            with self.raises(s_exc.SchemaViolation):
                await core.auth.allrole.addRule((1, ('hehe', 'haha')))
            with self.raises(s_exc.SchemaViolation):
                await core.auth.allrole.setRules([(True, ('hehe', 'haha'), 'newp')])
            with self.raises(s_exc.SchemaViolation):
                await core.auth.allrole.setRules([(True, )])

    async def test_auth_archived_locked_interaction(self):

        # Check that we can't unlock an archived user
        async with self.getTestCore() as core:
            lowuser = await core.addUser('lowuser')
            useriden = lowuser.get('iden')

            await core.setUserArchived(useriden, True)

            udef = await core.getUserDef(useriden)
            self.true(udef.get('archived'))
            self.true(udef.get('locked'))

            # Unlocking an archived user is invalid
            with self.raises(s_exc.BadArg) as exc:
                await core.setUserLocked(useriden, False)
            self.eq(exc.exception.get('mesg'), 'Cannot unlock archived user.')
            self.eq(exc.exception.get('user'), useriden)
            self.eq(exc.exception.get('username'), 'lowuser')

        # Check our cell migration that locks archived users
        async with self.getRegrCore('unlocked-archived-users') as core:
            for ii in range(10):
                user = await core.getUserDefByName(f'lowuser{ii:02d}')
                self.nn(user)
                self.true(user.get('archived'))
                self.true(user.get('locked'))

        # Check behavior of upgraded mirrors and non-upgraded leader
        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:
                path00 = s_common.gendir(dirn, 'cell00')
                path01 = s_common.gendir(dirn, 'cell01')

                with mock.patch('synapse.lib.cell.NEXUS_VERSION', (2, 177)):
                    async with self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=path00) as cell00:
                        lowuser = await cell00.addUser('lowuser')
                        useriden = lowuser.get('iden')
                        await cell00.setUserArchived(useriden, True)

                        with mock.patch('synapse.lib.cell.NEXUS_VERSION', (2, 198)):
                            async with self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=path01, provinfo={'mirror': 'cell'}) as cell01:
                                await cell01.sync()
                                udef = await cell01.getUserDef(useriden)
                                self.true(udef.get('locked'))
                                self.true(udef.get('archived'))

                                # Simulate a call to cell00.setUserLocked(useriden, False) to bypass
                                # the check in cell00.auth.setUserInfo()
                                await cell00.auth._push('user:info', useriden, 'locked', False)
                                await cell01.sync()

                                udef00 = await cell00.getUserDef(useriden)
                                self.true(udef00.get('archived'))
                                self.false(udef00.get('locked'))

                                udef01 = await cell01.getUserDef(useriden)
                                self.true(udef01.get('archived'))
                                self.false(udef01.get('locked'))

        # Check that we don't blowup/schism if an upgraded mirror is behind a leader with a pending
        # user:info event that unlocks an archived user
        async with self.getTestAha() as aha:

            with self.getTestDir() as dirn:
                path00 = s_common.gendir(dirn, 'cell00')
                path01 = s_common.gendir(dirn, 'cell01')

                async with self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=path00) as cell00:
                    lowuser = await cell00.addUser('lowuser')
                    useriden = lowuser.get('iden')
                    await cell00.setUserLocked(useriden, True)

                    async with self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=path01, provinfo={'mirror': 'cell'}) as cell01:
                        await cell01.sync()
                        udef = await cell01.getUserDef(useriden)
                        self.true(udef.get('locked'))
                        self.false(udef.get('archived'))

                    # Set user locked while cell01 is offline so it will get the edit when it comes
                    # back
                    await cell00.setUserLocked(useriden, False)
                    await cell00.sync()

                # Edit the slabs on both cells directly to archive the user
                lmdb00 = s_common.genpath(path00, 'slabs', 'cell.lmdb')
                lmdb01 = s_common.genpath(path01, 'slabs', 'cell.lmdb')

                slab00 = await s_lmdbslab.Slab.anit(lmdb00, map_size=s_cell.SLAB_MAP_SIZE)
                slab01 = await s_lmdbslab.Slab.anit(lmdb01, map_size=s_cell.SLAB_MAP_SIZE)

                # Simulate the cell migration which locks archived users
                for slab in (slab00, slab01):
                    authkv = slab.getSafeKeyVal('auth')
                    userkv = authkv.getSubKeyVal('user:info:')

                    info = userkv.get(useriden)
                    info['archived'] = True
                    info['locked'] = True
                    userkv.set(useriden, info)

                await slab00.fini()
                await slab01.fini()

                # Spin the cells back up and wait for the edit to sync to cell01
                async with self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=path00) as cell00:
                    udef = await cell00.getUserDef(useriden)
                    self.true(udef.get('archived'))
                    self.true(udef.get('locked'))

                    async with self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=path01, provinfo={'mirror': 'cell'}) as cell01:
                        await cell01.sync()
                        udef = await cell01.getUserDef(useriden)
                        self.true(udef.get('archived'))
                        self.true(udef.get('locked'))

                        self.ge(cell00.nexsvers, (2, 198))
                        self.ge(cell01.nexsvers, (2, 198))

    async def test_auth_password_policy(self):
        policy = {
            'complexity': {
                'length': 12,
                'sequences': 3,
                'upper:count': 2,
                'lower:count': 2,
                'lower:valid': string.ascii_lowercase + 'αβγ',
                'special:count': 2,
                'number:count': 2,
            },
            'attempts': 3,
            'previous': 2,
        }

        pass1 = 'jhf9_gaf-xaw-QBX4dqp'
        pass2 = 'rek@hjv6VBV2rwe2qwd!'
        pass3 = 'ZXN-pyv7ber-kzq2kgh'

        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:

            user = await core.auth.addUser('blackout@vertex.link')

            self.none(user.info.get('policy:previous'))
            await user.setPasswd(pass1, nexs=False)
            await user.setPasswd(pass2, nexs=False)
            await user.setPasswd(pass3, nexs=False)
            self.len(2, user.info.get('policy:previous'))

            await user.tryPasswd('newp')
            self.eq(1, user.info.get('policy:attempts'))
            await user.setLocked(False, logged=False)
            self.eq(0, user.info.get('policy:attempts'))

        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            self.nn(auth.policy)

            user = await auth.addUser('blackout@vertex.link')

            # Compliant passwords
            await core.setUserPasswd(user.iden, pass1)
            await core.setUserPasswd(user.iden, pass2)
            await core.setUserPasswd(user.iden, pass3)

            # Test password attempt reset
            await core.tryUserPasswd(user.name, 'foo')
            self.eq(user.info.get('policy:attempts'), 1)

            await core.tryUserPasswd(user.name, pass3)
            self.eq(user.info.get('policy:attempts'), 0)

            # Test lockout from too many invalid attempts
            self.false(await core.tryUserPasswd(user.name, 'foo'))
            self.false(await core.tryUserPasswd(user.name, 'foo'))
            self.false(await core.tryUserPasswd(user.name, 'foo'))
            self.eq(user.info.get('policy:attempts'), 3)
            self.true(user.info.get('locked'))

            await user.setLocked(False)
            self.eq(user.info.get('policy:attempts'), 0)

            # Test reusing previous password
            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, pass2)
            self.eq(exc.exception.get('failures'), [
                'Password cannot be the same as previous 2 password(s).'
            ])

            await core.setUserPasswd(user.iden, pass1)

            # Test password that doesn't meet complexity requirements
            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, 'Ff1!')
            self.eq(exc.exception.get('failures'), [
                'Password must be at least 12 characters.',
                'Password must contain at least 2 uppercase characters, 1 found.',
                'Password must contain at least 2 lowercase characters, 1 found.',
                'Password must contain at least 2 special characters, 1 found.',
                'Password must contain at least 2 digit characters, 1 found.'
            ])

            # Check sequences
            seqmsg = 'Password must not contain forward/reverse sequences longer than 3 characters.'
            passwords = [
                # letters
                'abcA', 'dcbA', 'Abcd', 'Acba',

                # numbers
                '123A', '432A', 'A234', 'A321',

                # greek alphabet (unicode test)
                'αβγA', 'Aαβγ', 'γβαA', 'Aγβα',

            ]

            for password in passwords:
                with self.raises(s_exc.BadArg) as exc:
                    await core.setUserPasswd(user.iden, password)
                self.isin(seqmsg, exc.exception.get('failures'))

            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, 'AAAA')
            self.eq(exc.exception.get('failures'), [
                'Password must be at least 12 characters.',
                'Password must contain at least 2 lowercase characters, 0 found.',
                'Password must contain at least 2 special characters, 0 found.',
                'Password must contain at least 2 digit characters, 0 found.'
            ])

            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, 'aaaa')
            self.eq(exc.exception.get('failures'), [
                'Password must be at least 12 characters.',
                'Password must contain at least 2 uppercase characters, 0 found.',
                'Password must contain at least 2 special characters, 0 found.',
                'Password must contain at least 2 digit characters, 0 found.'
            ])

            # Setting password to None should work also
            await core.setUserPasswd(user.iden, None)

            # Attempting to add a user with a bad passwd will add the user and fail to set the password
            with self.raises(s_exc.BadArg):
                await core.addUser('bob.grey', email='bob.grey@vertex.link', passwd='noncompliant')
            user = await core.auth.getUserByName('bob.grey')
            self.eq('bob.grey@vertex.link', user.info.get('email'))
            self.len(1, user.info.get('roles'))  # User has the default all role
            # Password was not set
            self.false(await user.tryPasswd('noncompliant'))

        policy = {
            'complexity': {
                'length': None,
            },
        }

        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth

            user = await auth.addUser('blackout@vertex.link')

            await core.setUserPasswd(user.iden, None)

            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, 'αβγA')
            self.isin(
                "Password contains invalid characters: ['α', 'β', 'γ']",
                exc.exception.get('failures')
            )

        policy = {
            'complexity': None,
            'previous': 3,
        }

        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth

            user = await auth.addUser('blackout@vertex.link')
            await core.setUserPasswd(user.iden, pass1)
            await core.setUserPasswd(user.iden, pass2)
            await core.setUserPasswd(user.iden, pass3)

            # Setting password to None should work also
            await core.setUserPasswd(user.iden, None)

            with self.raises(s_exc.BadArg) as exc:
                await core.setUserPasswd(user.iden, pass1)
            self.eq(exc.exception.get('failures'), [
                'Password cannot be the same as previous 3 password(s).'
            ])

        # Single complexity rule, uses default character lists
        policy = {'complexity': {'length': 3}}
        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            user = await auth.addUser('blackout@vertex.link')
            with self.raises(s_exc.BadArg):
                await core.setUserPasswd(user.iden, 'no')
            await core.setUserPasswd(user.iden, 'hehe')
            await core.setUserPasswd(user.iden, 'heh')
            with self.raises(s_exc.BadArg) as cm:
                await core.setUserPasswd(user.iden, 'hehαβγ')
            self.isin('Password contains invalid characters', cm.exception.get('mesg'))

        # Complexity disables the *:valid groups so they will not be checked
        policy = {'complexity': {'length': 3,
                                 'upper:valid': None,
                                 'upper:count': 20,
                                 'lower:valid': None,
                                 'lower:count': 20,
                                 'special:valid': None,
                                 'special:count': 20,
                                 'number:valid': None,
                                 'number:count': 20,
                                 }}
        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            user = await auth.addUser('blackout@vertex.link')
            with self.raises(s_exc.BadArg):
                await core.setUserPasswd(user.iden, 'no')
            await core.setUserPasswd(user.iden, 'heh')
            await core.setUserPasswd(user.iden, 'hehαβγ1234!!@!@!')

        # Policy only allows lowercase and specials...
        policy = {'complexity': {'length': 2,
                                 'upper:valid': None,
                                 'number:valid': None,
                                 'lower:count': 1,
                                 'special:count': 1,
                                 }}
        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            user = await auth.addUser('blackout@vertex.link')
            with self.raises(s_exc.BadArg):
                await core.setUserPasswd(user.iden, 'No')
            with self.raises(s_exc.BadArg):
                await core.setUserPasswd(user.iden, '1o')
            await core.setUserPasswd(user.iden, 'y#s')

        # Policy enforces character sets but doesn't care about minimum entries
        policy = {'complexity': {'length': 3,
                                 'upper:count': None,
                                 'lower:count': None,
                                 'special:count': None,
                                 'number:count': None,
                                 }}
        conf = {'auth:passwd:policy': policy}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            user = await auth.addUser('blackout@vertex.link')
            await core.setUserPasswd(user.iden, 'yup')
            await core.setUserPasswd(user.iden, 'Y!0')
            with self.raises(s_exc.BadArg) as cm:
                await core.setUserPasswd(user.iden, 'sadαβγ')
            self.isin('Password contains invalid characters', cm.exception.get('mesg'))

        # No complexity rules
        policy = {'attempts': 1}
        conf = {'auth:passwd:policy': policy, 'auth:passwd': 'secret'}
        async with self.getTestCore(conf=conf) as core:
            auth = core.auth
            user = await auth.addUser('blackout@vertex.link')
            await core.setUserPasswd(user.iden, 'hehe')
            self.true(await user.tryPasswd('hehe'))
            self.false(await user.tryPasswd('newp'))
            self.true(user.isLocked())
            # Root user may track policy lockouts but will not be locked out by failures.
            root = auth.rootuser
            self.false(await root.tryPasswd('newp'))
            self.false(await root.tryPasswd('newpx'))
            self.eq(root.info.get('policy:attempts'), 2)
            self.false(root.isLocked())
            # valid passwod auth resets root atttempt counter.
            self.true(await root.tryPasswd('secret'))
            self.eq(root.info.get('policy:attempts'), 0)

        # auth:passwd does not interact with auth:passwd:policy
        with self.getTestDir() as dirn:
            policy = {'complexity': {'length': 5}}
            conf = {'auth:passwd': 'newp', 'auth:passwd:policy': policy}
            async with self.getTestCore(conf=conf, dirn=dirn) as core:
                user = core.auth.rootuser
                self.false(await user.tryPasswd('hehe'))
                self.true(await user.tryPasswd('newp'))

            conf = {'auth:passwd': 'yupp!!', 'auth:passwd:policy': policy}
            async with self.getTestCore(conf=conf, dirn=dirn) as core:
                user = core.auth.rootuser
                self.false(await user.tryPasswd('newp'))
                self.true(await user.tryPasswd('yupp!!'))

    async def test_hive_auth_deepdeny(self):
        async with self.getTestCore() as core:

            # Create an authgate we can later test against
            fork = await core.callStorm('return( $lib.view.get().fork().iden )')
            await core.callStorm('auth.user.add lowuser')
            await core.callStorm('auth.user.addrule lowuser "!hehe.haha.specific"')
            await core.callStorm('auth.user.addrule lowuser "hehe.something.else"')
            await core.callStorm('auth.user.addrule lowuser "hehe.haha"')
            await core.callStorm('auth.user.addrule lowuser "some.perm"')
            await core.callStorm('auth.role.add ninjas')
            await core.callStorm('auth.role.add clowns')
            await core.callStorm('auth.user.grant --index 0 lowuser ninjas')
            await core.callStorm('auth.user.grant --index 1 lowuser clowns')
            await core.callStorm('auth.role.addrule ninjas some.rule')
            await core.callStorm('auth.role.addrule ninjas --gate $gate another.rule',
                                 opts={'vars': {'gate': fork}})

            user = await core.auth.getUserByName('lowuser')  # type: s_auth.User
            self.false(user.allowed(('hehe',)))
            self.false(user.allowed(('hehe',), deepdeny=True))
            self.true(user.allowed(('hehe', 'haha')))
            self.false(user.allowed(('hehe', 'haha'), deepdeny=True))
            self.true(user.allowed(('hehe', 'haha', 'wow')))
            self.true(user.allowed(('hehe', 'haha', 'wow'), deepdeny=True))
            self.true(user.allowed(('some', 'perm')))
            self.true(user.allowed(('some', 'perm'), deepdeny=True))
            self.true(user.allowed(('some', 'perm', 'here')))
            self.true(user.allowed(('some', 'perm', 'here'), deepdeny=True))

            await core.callStorm('auth.user.delrule lowuser hehe.haha')
            await core.callStorm('auth.user.addrule lowuser hehe')
            self.true(user.allowed(('hehe',)))
            self.false(user.allowed(('hehe',), deepdeny=True))
            self.true(user.allowed(('hehe', 'haha')))
            self.false(user.allowed(('hehe', 'haha'), deepdeny=True))
            self.true(user.allowed(('hehe', 'haha', 'wow')))
            self.true(user.allowed(('hehe', 'haha', 'wow'), deepdeny=True))
            self.false(user.allowed(('weee',)))
            self.false(user.allowed(('weee',), deepdeny=True))
            await core.callStorm('auth.user.delrule lowuser hehe')

            await core.callStorm('auth.role.addrule all "!hehe.something.else.very.specific"')
            self.false(user.allowed(('hehe',)))
            self.false(user.allowed(('hehe',), deepdeny=True))

            self.false(user.allowed(('hehe', 'something')))
            self.true(user.allowed(('hehe', 'something', 'else')))
            self.true(user.allowed(('hehe', 'something', 'else', 'very')))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific')))

            self.false(user.allowed(('hehe', 'something')))
            self.false(user.allowed(('hehe', 'something', 'else'), deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else', 'very'), deepdeny=True))

            # There is NOT a deeper permission here, even though there is a deny rule on the role.
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific', 'more')))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific', 'more'), deepdeny=True))
            await core.callStorm('auth.role.delrule all "!hehe.something.else.very.specific"')

            await core.callStorm('auth.role.addrule --gate $gate all "beep.boop"',
                                 opts={'vars': {'gate': fork}})
            await core.callStorm('auth.role.addrule --gate $gate all "!hehe.something.else.very.specific"',
                                 opts={'vars': {'gate': fork}})
            self.false(user.allowed(('hehe',), gateiden=fork))
            self.false(user.allowed(('hehe', 'something'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork))
            self.false(user.allowed(('hehe',), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something'), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else'), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork, deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork, deepdeny=True))
            await core.callStorm('auth.role.delrule --gate $gate all "!hehe.something.else.very.specific"',
                                 opts={'vars': {'gate': fork}})
            await core.callStorm('auth.role.delrule --gate $gate all "beep.boop"',
                                 opts={'vars': {'gate': fork}})

            await core.callStorm('auth.user.addrule --gate $gate lowuser "beep.boop"',
                                 opts={'vars': {'gate': fork}})
            await core.callStorm('auth.user.addrule --gate $gate lowuser "!hehe.something.else.very.specific"',
                                 opts={'vars': {'gate': fork}})
            self.false(user.allowed(('hehe',), gateiden=fork))
            self.false(user.allowed(('hehe', 'something'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork))
            self.false(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork))
            self.false(user.allowed(('hehe',), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something'), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else'), gateiden=fork, deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork, deepdeny=True))
            # This differs from earlier check as the dd is false; but the user authgate deny is earlier in precedence
            # than the user specific allow
            self.false(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork, deepdeny=True))

            await core.callStorm('auth.user.delrule --gate $gate lowuser "!hehe.something.else.very.specific"',
                                 opts={'vars': {'gate': fork}})
            await core.callStorm('auth.user.delrule --gate $gate lowuser "beep.boop"',
                                 opts={'vars': {'gate': fork}})

            await core.callStorm('auth.user.mod --admin (true) lowuser --gate $gate', opts={'vars': {'gate': fork}})
            self.true(user.allowed(('hehe',), gateiden=fork))
            self.true(user.allowed(('hehe', 'something'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork))

            self.true(user.allowed(('hehe',), gateiden=fork, deepdeny=True))
            self.true(user.allowed(('hehe', 'something'), gateiden=fork, deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else'), gateiden=fork, deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very'), gateiden=fork, deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), gateiden=fork, deepdeny=True))

            await core.callStorm('auth.user.mod --admin (false) lowuser --gate $gate', opts={'vars': {'gate': fork}})

            await core.callStorm('auth.user.mod --admin (true) lowuser')
            self.true(user.allowed(('hehe',)))
            self.true(user.allowed(('hehe', 'something')))
            self.true(user.allowed(('hehe', 'something', 'else')))
            self.true(user.allowed(('hehe', 'something', 'else', 'very')))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific')))
            self.true(user.allowed(('hehe',), deepdeny=True))
            self.true(user.allowed(('hehe', 'something')))
            self.true(user.allowed(('hehe', 'something', 'else'), deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very'), deepdeny=True))
            self.true(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), deepdeny=True))
            await core.callStorm('auth.user.mod --admin (false) lowuser')

            await core.callStorm('auth.user.mod --locked (true) lowuser')
            self.false(user.allowed(('hehe',), deepdeny=True))
            self.false(user.allowed(('hehe', 'something'), deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else'), deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else', 'very'), deepdeny=True))
            self.false(user.allowed(('hehe', 'something', 'else', 'very', 'specific'), deepdeny=True))
