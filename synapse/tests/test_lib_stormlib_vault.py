import textwrap

import regex

import synapse.exc as s_exc

import synapse.lib.cell as s_cell
import synapse.lib.config as s_config

import synapse.tests.utils as s_test

class StormlibVaultTest(s_test.SynTest):

    async def test_stormlib_vault(self):

        async with self.getTestCore() as core:

            root = core.auth.rootuser
            visi1 = await core.auth.addUser('visi1')
            visi2 = await core.auth.addUser('visi2')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            vtype = 'synapse-test'

            # Create user vault
            opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}}
            uiden = await core.callStorm('return($lib.vault.add(uvault, $vtype, user, $iden, ({"name": "uvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, uiden))

            vault = core.getVaultByIden(uiden)
            self.nn(vault)

            ret = await core.callStorm('return($lib.vault.getByName(uvault))')
            self.eq(ret, vault)

            opts = {'vars': {'uiden': uiden}}
            ret = await core.callStorm('return($lib.vault.openByIden($uiden))', opts=opts)
            self.eq(ret, vault.get('data'))

            # Create role vault
            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            riden = await core.callStorm('return($lib.vault.add(rvault, $vtype, role, $iden, ({"name": "rvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, riden))

            vault = core.getVaultByIden(uiden)
            self.nn(vault)

            # Create global vault
            opts = {'vars': {'vtype': vtype, 'iden': None}}
            giden = await core.callStorm('return($lib.vault.add(gvault, $vtype, global, $iden, ({"name": "gvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, giden))

            vault = core.getVaultByIden(uiden)
            self.nn(vault)

            # Set some data
            self.true(await core.callStorm('return($lib.vault.set(uvault, foo, bar))'))

            # Get some data
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('return($lib.vault.getByIden($iden))', opts=opts)
            self.eq(ret.get('name'), 'uvault')
            self.eq(ret.get('iden'), uiden)
            self.eq(ret.get('data'), {'name': 'uvault', 'foo': 'bar'})

            # Open some vaults
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('return($lib.vault.openByType($vtype))', opts=opts)
            self.eq(data, {'name': 'uvault', 'foo': 'bar'})

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('return($lib.vault.openByType($vtype, role))', opts=opts)
            self.eq(data, {'name': 'rvault'})

            # Set default and then open
            opts = {'vars': {'vtype': vtype}}
            self.true(await core.callStorm('return($lib.vault.setDefault($vtype, global))', opts=opts))

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('return($lib.vault.openByType($vtype))', opts=opts)
            self.eq(data, {'name': 'gvault'})

            # List vaults
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(3, vaults)

            # Delete some vaults
            self.true(await core.callStorm('return($lib.vault.del(uvault))'))

            self.true(await core.callStorm('return($lib.vault.del(rvault))'))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(1, vaults)

            # Set permissions on global vault
            opts = {'vars': {'iden': visi1.iden}}
            q = 'return($lib.vault.setPerm(gvault, $iden, $lib.auth.easyperm.level.deny))'
            self.true(await core.callStorm(q, opts=opts))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(0, vaults)

    async def test_stormlib_vault_cmds(self):
        async with self.getTestCore() as core:

            visi1 = await core.auth.addUser('visi1')
            visi2 = await core.auth.addUser('visi2')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            vtype = 'synapse-test'

            # vault.add
            opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}}
            uiden = await core.callStorm('vault.add uvault $vtype user $iden ({"apikey": "uvault"})', opts=opts)
            self.nn(regex.match(s_config.re_iden, uiden))

            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            riden = await core.callStorm('vault.add rvault $vtype role $iden ({"apikey": "rvault"})', opts=opts)
            self.nn(regex.match(s_config.re_iden, riden))

            uvault = core.getVaultByIden(uiden)
            self.nn(uvault)
            self.eq(uvault.get('data'), {'apikey': 'uvault'})

            rvault = core.getVaultByIden(riden)
            self.nn(rvault)
            self.eq(rvault.get('data'), {'apikey': 'rvault'})

            # vault.get
            ret = await core.callStorm('vault.get uvault')
            self.eq(ret, uvault)

            # vault.get.byiden
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('vault.get.byiden $iden', opts=opts)
            self.eq(ret, uvault)

            # vault.set
            self.true(await core.callStorm('vault.set uvault apikey uvault1'))
            vault = core.getVaultByIden(uiden)
            self.eq(vault.get('data'), {'apikey': 'uvault1'})

            # vault.list
            opts = {'user': visi1.iden}
            msgs = await core.stormlist('vault.list', opts=opts)
            output = f'''
            Available Vaults
            ----------------
            Vault: uvault
              Type: {vtype}
              Scope: user
              Iden: {uiden}
              Permissions:
                Users:
                  visi1: admin
                Roles: None

            Vault: rvault
              Type: {vtype}
              Scope: role
              Iden: {riden}
              Permissions:
                Users:
                  root: admin
                Roles:
                  contributor: edit
            '''
            for line in textwrap.dedent(output[1:]).split('\n'):
                self.stormIsInPrint(line, msgs)

            # vault.open
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('vault.open $vtype', opts=opts)
            self.eq(data, {'apikey': 'uvault1'})

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('vault.open $vtype --scope role', opts=opts)
            self.eq(data, {'apikey': 'rvault'})

            # vault.open.byname
            opts = {'user': visi1.iden}
            data = await core.callStorm('vault.open.byname uvault', opts=opts)
            self.eq(data, {'apikey': 'uvault1'})

            # vault.open.byiden
            opts = {'vars': {'iden': uiden}, 'user': visi1.iden}
            data = await core.callStorm('vault.open.byiden $iden', opts=opts)
            self.eq(data, {'apikey': 'uvault1'})

            # vault.setperm
            opts = {'vars': {'vtype': vtype}}
            q = 'vault.setperm rvault $lib.auth.users.byname(visi1).iden $lib.auth.easyperm.level.read'
            self.true(await core.callStorm(q, opts=opts))

            vault = core.getVaultByName('rvault')
            self.true(core._hasEasyPerm(vault, visi1, s_cell.PERM_READ))

            # vault.setdefault
            opts = {'vars': {'vtype': vtype}}
            self.true(await core.callStorm('vault.setdefault $vtype role', opts=opts))

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            data = await core.callStorm('vault.open $vtype', opts=opts)
            self.eq(data, {'apikey': 'rvault'})

            # vault.del
            self.true(await core.callStorm('vault.del uvault'))
            self.true(await core.callStorm('vault.del rvault'))
