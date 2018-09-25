import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.cellauth as s_cellauth
import synapse.tools.deploy as s_deploy

class CellAuthTest(s_t_utils.SynTest):
    def test_cellauth_list(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            with self.getTestProxy(dmon, 'core', user='root', passwd='root') as core:
                self.addCreatorDeleterRoles(core)
                core.addUserRole('root', 'creator')

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            argv = [coreurl, 'list']
            outp = self.getTestOutp()
            self.eq(s_cellauth.main(argv, outp), 0)
            outp.expect('getting users and roles')
            outp.expect('users:')
            outp.expect('root')
            outp.expect('roles:')

            argv = [coreurl, 'list', 'root']
            outp = self.getTestOutp()
            self.eq(s_cellauth.main(argv, outp), 0)
            outp.expect('root')
            outp.expect('admin: True')
            outp.expect('role: creator')

            argv = [coreurl, 'list', 'creator']
            outp = self.getTestOutp()
            self.eq(s_cellauth.main(argv, outp), 0)
            outp.expect('creator')
            outp.expect('type: role')

    def test_cellauth_user(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', 'root']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('type: user')
            outp.expect('admin: True')
            outp.expect('locked: False')
            outp.expect('rules:')
            outp.expect('roles:')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', 'foo']
            s_cellauth.main(argv, outp)
            outp.expect(f'no such user: foo')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('adding user: foo')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'frole']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('adding role: frole')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--admin', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('admin: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--noadmin', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('admin: False')

    def test_cellauth_lock(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--lock', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('locking user: foo')
            outp.expect('locked: True')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--unlock', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('unlocking user: foo')
            outp.expect('locked: False')

    def test_cellauth_passwd(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--passwd', 'mysecret', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('setting passwd for: foo')

    def test_cellauth_grants(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--adduser', 'foo']
            s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrole', 'bar']
            s_cellauth.main(argv, outp)

            argv = [coreurl, 'modify', '--grant', 'bar', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('granting bar to: foo')
            outp.expect('role: bar')

            argv = [coreurl, 'modify', '--revoke', 'bar', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect('revoking bar from: foo')

    def test_cellauth_rules(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'
            rule = 'node:add'
            nrule = '!node:add'
            name = 'foo'

            outp = self.getTestOutp()
            argv = ['--debug', coreurl, 'modify', '--adduser', name]
            s_cellauth.main(argv, outp)

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrule', rule, name]
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'adding rule to {name}: (True, [{rule!r}])')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--delrule', '0', 'foo']
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'deleting rule index: 0')

            outp = self.getTestOutp()
            argv = [coreurl, 'modify', '--addrule', nrule, name]
            s_cellauth.main(argv, outp)
            # print(str(outp))
            outp.expect(f'adding rule to {name}: (False, [{rule!r}])')
