import synapse.tests.utils as s_t_utils

import synapse.tools.cellauth as s_cellauth

class CellAuthTest(s_t_utils.SynTest):

    async def test_cellauth_bad(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon, \
                await self.agetTestProxy(dmon, 'core', user='root', passwd='root'):
            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'
            argv = [coreurl]
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), -1)
            outp.expect('the following arguments are required:')

    async def test_cellauth_list(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon, \
                await self.agetTestProxy(dmon, 'core', user='root', passwd='root') as core:
            await self.addCreatorDeleterRoles(core)
            await core.addUserRole('root', 'creator')

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            argv = [coreurl, 'list']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)
            outp.expect('getting users and roles')
            outp.expect('users:')
            outp.expect('root')
            outp.expect('roles:')

            argv = [coreurl, '--debug', 'list', 'root']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)

            outp.expect('root')
            outp.expect('admin: True')
            outp.expect('role: creator')

            argv = [coreurl, 'list', 'creator']
            outp = self.getTestOutp()
            self.eq(await s_cellauth.main(argv, outp), 0)
            outp.expect('creator')
            outp.expect('type: role')

    async def test_cellauth_user(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', 'root']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
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
            # print(str(outp))
            outp.expect('adding user: foo')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'frole']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('adding role: frole')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--admin', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('admin: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--noadmin', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('admin: False')

    async def test_cellauth_lock(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--lock', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('locking user: foo')
            outp.expect('locked: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--unlock', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('unlocking user: foo')
            outp.expect('locked: False')

    async def test_cellauth_passwd(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--passwd', 'mysecret', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('setting passwd for: foo')

    async def test_cellauth_grants(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'bar']
            await s_cellauth.main(argv, outp)

            argv = [coreurl, 'modify', '--grant', 'bar', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('granting bar to: foo')
            outp.expect('role: bar')

            argv = [coreurl, 'modify', '--revoke', 'bar', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('revoking bar from: foo')

    async def test_cellauth_rules(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'
            rule = 'node:add'
            nrule = '!node:add'
            name = 'foo'

            outp = self.getTestOutp()
            argv = ['--debug', coreurl, 'modify', '--adduser', name]
            await s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrule', rule, name]
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'adding rule to {name}: (True, [{rule!r}])')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--delrule', '0', 'foo']
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'deleting rule index: 0')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrule', nrule, name]
            await s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'adding rule to {name}: (False, [{rule!r}])')
