import unittest.mock as mock

import synapse.tests.utils as s_t_utils

import synapse.tools.cellauth as s_cellauth

class CellAuthTest(s_t_utils.SynTest):

    async def test_cellauth_bad(self):

        async with self.getTestCore() as core:

            coreurl = core.getLocalUrl()

            argv = [coreurl]
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), -1)
            outp.expect('the following arguments are required:')

            outp.clear()
            argv = [coreurl, 'modify', '--adduser', 'foo', '--object', 'foo:bar']
            await s_cellauth.main(argv, outp)
            outp.expect('only valid with --addrule')

            def fakevers(self):
                return (0, 0, 0)

            with mock.patch('synapse.telepath.Proxy._getSynVers', fakevers):
                argv = [coreurl, 'modify', '--adduser', 'foo']
                outp = self.getTestOutp()
                await s_cellauth.main(argv, outp)
                outp.expect('Cell version 0.0.0 is outside of the cellauth supported range')

                argv = [coreurl, 'list']
                outp = self.getTestOutp()
                await s_cellauth.main(argv, outp)
                outp.expect('Cell version 0.0.0 is outside of the cellauth supported range')

    async def test_cellauth_list(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            coreurl = core.getLocalUrl()

            argv = [coreurl, 'list']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)
            outp.expect('getting users and roles')
            outp.expect('users:')
            outp.expect('root')
            outp.expect('roles:')

            argv = [coreurl, '--debug', 'list', 'icanadd']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)

            outp.expect('icanadd')
            outp.expect('admin: False')
            outp.expect('role: creator')
            self.false(outp.expect('allow: node.add', throw=False))

            argv = [coreurl, 'list', 'creator']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)
            outp.expect('creator')
            outp.expect('type: role')

            argv = [coreurl, 'list', '--detail', 'icanadd']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)
            outp.expect('icanadd')
            outp.expect('admin: False')
            outp.expect('role: creator')
            outp.expect('allow: node.add', throw=False)

    async def test_cellauth_user(self):

        async with self.getTestCore() as core:

            coreurl = core.getLocalUrl()

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', 'root']
            await s_cellauth.main(argv, outp)
            outp.expect('type: user')
            outp.expect('admin: True')
            outp.expect('locked: False')
            outp.expect('rules:')
            outp.expect('roles:')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'no such user: foo')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('adding user: foo')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'frole']
            await s_cellauth.main(argv, outp)
            outp.expect('adding role: frole')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--admin', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('admin: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--noadmin', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('admin: False')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--delrole', 'frole']
            await s_cellauth.main(argv, outp)
            outp.expect('deleting role: frole')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--deluser', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('deleting user: foo')

    async def test_cellauth_lock(self):

        async with self.getTestCore() as core:

            coreurl = core.getLocalUrl()

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--lock', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('locking user: foo')
            outp.expect('locked: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--unlock', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('unlocking user: foo')
            outp.expect('locked: False')

    async def test_cellauth_passwd(self):

        async with self.getTestCore() as core:

            coreurl = core.getLocalUrl()

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--passwd', 'mysecret', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('setting passwd for: foo')

    async def test_cellauth_grants(self):

        async with self.getTestCore() as core:

            coreurl = core.getLocalUrl()

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'bar']
            await s_cellauth.main(argv, outp)

            argv = [coreurl, 'modify', '--grant', 'bar', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('granting bar to: foo')
            outp.expect('role: bar')

            argv = [coreurl, 'modify', '--revoke', 'bar', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect('revoking bar from: foo')

    async def test_cellauth_rules(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            coreurl = core.getLocalUrl()

            rule = 'node.add'
            rulerepr = repr((True, ['node', 'add']))
            nrule = '!node.add'
            nrulerepr = repr((False, ['node', 'add']))
            name = 'foo'

            outp = self.getTestOutp()
            argv = ['--debug', coreurl, 'modify', '--adduser', name]
            await s_cellauth.main(argv, outp)

            outp.clear()
            argv = [coreurl, 'modify', '--addrule', rule, name]
            await s_cellauth.main(argv, outp)
            outp.expect(f'adding rule to {name}: {rulerepr}')
            outp.expect(f'0 allow: node.add')

            user = await prox.getUserInfo(name)
            self.eq(user.get('rules'),
                    ((True, ('node', 'add',)),))

            outp.clear()
            argv = [coreurl, 'modify', '--addrule', 'node.del', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'1 allow: node.del')

            outp.clear()
            argv = [coreurl, 'modify', '--addrule', 'service.get', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'2 allow: service.get')

            outp.clear()
            argv = [coreurl, 'list', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'0 allow: node.add')
            outp.expect(f'1 allow: node.del')
            outp.expect(f'2 allow: service.get')

            outp.clear()
            argv = [coreurl, 'modify', '--delrule', '1', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'deleting rule index: 1')
            outp.expect(f'0 allow: node.add')
            outp.expect(f'1 allow: service.get')
            self.false(outp.expect(f'allow: node.del', throw=False))

            user = await prox.getUserInfo(name)
            self.eq(user.get('rules'),
                    ((True, ('node', 'add')), (True, ('service', 'get'))))

            outp.clear()
            argv = [coreurl, 'list', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'0 allow: node.add')
            outp.expect(f'1 allow: service.get')
            self.false(outp.expect(f'allow: node.del', throw=False))

            outp.clear()
            argv = [coreurl, 'modify', '--delrule', '0', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'deleting rule index: 0')
            outp.expect(f'0 allow: service.get')
            self.false(outp.expect(f'allow: node.add', throw=False))

            outp.clear()
            argv = [coreurl, 'modify', '--delrule', '0', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'deleting rule index: 0')
            self.false(outp.expect(f'allow: service.get', throw=False))

            user = await prox.getUserInfo(name)
            self.eq(user.get('rules'), ())

            outp.clear()
            viewiden = core.view.iden
            argv = [coreurl, 'modify', '--addrule', nrule, name, '--object', viewiden]
            await s_cellauth.main(argv, outp)
            outp.expect(f'adding rule to {name}: {nrulerepr}')
            outp.expect(f'0 deny: node.add')

            outp.clear()
            argv = [coreurl, 'modify', '--addrule', 'service.get', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'0 allow: service.get')
            outp.expect(f'1 deny: node.add')

            outp.clear()
            argv = [coreurl, 'modify', '--delrule', '1', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'deleting rule index: 1')
            outp.expect(f'0 allow: service.get')
            self.false(outp.expect(f'deny: node.add', throw=False))

            outp.clear()
            argv = [coreurl, 'modify', '--delrule', '42', 'foo']
            await s_cellauth.main(argv, outp)
            outp.expect(f'deleting rule index: 42')
            outp.expect(f'rule index is out of range')

    async def test_cellauth_gates(self):

        async with self.getTestCore() as core:

            lurl = core.getLocalUrl()

            viewiden = core.view.iden
            layriden = core.view.layers[0].iden

            visi = await core.auth.addUser('visi')
            ninjas = await core.auth.addRole('ninjas')

            outp = self.getTestOutp()
            argv = [lurl, 'modify', '--addrule', 'node.add', '--object', layriden, 'visi']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [lurl, 'modify', '--admin', '--object', layriden, 'visi']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [lurl, 'modify', '--addrule', 'view.read', '--object', viewiden, 'ninjas']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [lurl, 'list', '--detail', 'ninjas']
            await s_cellauth.main(argv, outp)

            outp.expect(f'auth gate: {viewiden}')
            outp.expect('allow: view.read')

            outp = self.getTestOutp()
            argv = [lurl, 'list', '--detail', 'visi']
            await s_cellauth.main(argv, outp)

            outp.expect(f'auth gate: {layriden}')
            outp.expect('allow: node.add')

            outp.expect(f'auth gate: {viewiden}')
            outp.expect('allow: view.read')
