import os

import synapse.tests.utils as s_tests

class CompatTest(s_tests.SynTest):

    async def test_lib_compat_cellauth(self):

        async with self.getRegrCore('old-cell-auth') as core:

            # check the .old dir exists after migration
            self.true(os.path.isdir(os.path.join(core.dirn, 'auth.old')))

            self.nn(core.auth.getRoleByName('analysts'))

            lyst = core.auth.getRoleByName('analysts')

            visi = core.auth.getUserByName('visi')

            self.true(visi.tryPasswd('secret'))

            # check role inherited rules
            self.true(visi.allowed(('node:add', 'inet:fqdn')))
            self.false(visi.allowed(('node:del', 'inet:fqdn')))

            self.isin(lyst, visi.getRoles())

            # check direct user rules with order
            fred = core.auth.getUserByName('fred')
            self.true(fred.allowed(('tag:add', 'hehe', 'haha')))
            self.false(fred.allowed(('tag:add', 'newp')))
