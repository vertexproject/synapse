from synapse.tests.common import *

import synapse.cortex as s_cortex
import synapse.lib.userauth as s_userauth

class UserAuthTest(SynTest):

    def test_userauth_base(self):
        core = s_cortex.openurl('ram:///')
        auth = s_userauth.UserAuth(core)

        auth.addUser('visi')
        auth.addRole('root')

        self.raises(DupUser, auth.addUser, 'visi')
        self.raises(DupRole, auth.addRole, 'root')

        auth.addUserRule('visi', 'foo.*')
        auth.addRoleRule('root', 'baz.*')

        self.raises(NoSuchUser, auth.addUserRule, 'newp', 'haha.*')
        self.raises(NoSuchRole, auth.addRoleRule, 'newp', 'haha.*')

        self.true(auth.isUserAllowed('visi', 'foo.bar'))
        self.false(auth.isUserAllowed('visi', 'baz.faz'))

        auth.addUserRole('visi', 'root')

        self.eq(auth.getUserRoles('visi')[0], 'root')

        self.true(auth.isUserAllowed('visi', 'foo.bar'))
        self.true(auth.isUserAllowed('visi', 'baz.faz'))

        auth.delUserRole('visi', 'root')

        self.true(auth.isUserAllowed('visi', 'foo.bar'))
        self.false(auth.isUserAllowed('visi', 'baz.faz'))

        # put the userrole back so we can delete the role...
        auth.addUserRole('visi', 'root')

        self.true(auth.isUserAllowed('visi', 'foo.bar'))
        self.true(auth.isUserAllowed('visi', 'baz.faz'))

        auth.delRole('root')

        self.true(auth.isUserAllowed('visi', 'foo.bar'))
        self.false(auth.isUserAllowed('visi', 'baz.faz'))

        core.fini()
        auth.fini()

    def test_userauth_rules(self):
        core = s_cortex.openurl('ram:///')
        auth = s_userauth.UserAuth(core)

        auth.addUser('visi')
        auth.addUserRule('visi', 'foo.*')

        rules = s_userauth.Rules(auth, 'visi')

        self.true(rules.allow('foo.bar'))
        self.false(rules.allow('baz.faz'))

        auth.addUserRule('visi', 'baz.*')

        self.true(rules.allow('foo.bar'))
        self.true(rules.allow('baz.faz'))

        auth.delUserRule('visi', 'foo.*')

        self.false(rules.allow('foo.bar'))
        self.true(rules.allow('baz.faz'))

        auth.fini()
        core.fini()

    def test_userauth_scope(self):
        core = s_cortex.openurl('ram:///')
        auth = s_userauth.UserAuth(core)

        auth.addUser('visi')
        auth.addUserRule('visi', 'foo:*')

        self.eq(s_userauth.getSynUser(), None)
        self.eq(s_userauth.getSynAuth(), None)

        self.false(s_userauth.amIAllowed('foo:bar'))
        self.true(s_userauth.amIAllowed('foo:bar', onnone=True))

        with s_userauth.asSynUser('visi', auth=auth):

            self.eq(s_userauth.getSynUser(), 'visi')
            self.nn(s_userauth.getSynAuth())

            self.true(s_userauth.amIAllowed('foo:bar'))
            self.false(s_userauth.amIAllowed('derp:bar'))

        self.eq(s_userauth.getSynUser(), None)
        self.eq(s_userauth.getSynAuth(), None)

        with s_userauth.asSynUser('newp', auth=auth):

            self.eq(s_userauth.getSynUser(), 'newp')
            self.nn(s_userauth.getSynAuth())
            self.raises(NoSuchUser, s_userauth.amIAllowed, 'foo:bar')

        self.eq(s_userauth.getSynUser(), None)
        self.eq(s_userauth.getSynAuth(), None)
