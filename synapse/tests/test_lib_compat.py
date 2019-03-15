import os

import synapse.cortex as s_cortex
import synapse.tests.utils as s_tests

class CompatTest(s_tests.SynTest):

    async def cellauth_migration_checks(self, core):
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

    async def test_compat_cellauth(self):

        # This copies a bit of the regression helper code
        with self.getRegrDir('cortexes', 'old-cell-auth') as dirn:
            async with await s_cortex.Cortex.anit(dirn) as core:
                self.true(os.path.isdir(os.path.join(core.dirn, 'auth.old')))

                await self.cellauth_migration_checks(core)

            self.true(core.isfini)
            # Now start the cortex back up and ensure that we can get the auth data we expect.
            async with await s_cortex.Cortex.anit(dirn) as core:
                self.true(os.path.isdir(os.path.join(core.dirn, 'auth.old')))

                await self.cellauth_migration_checks(core)
            self.true(core.isfini)
