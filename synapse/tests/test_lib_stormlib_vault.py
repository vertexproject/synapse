import textwrap

import regex

import synapse.exc as s_exc

import synapse.lib.cell as s_cell
import synapse.lib.config as s_config

import synapse.tests.utils as s_test

def split(text):
    return textwrap.dedent(text).split('\n')

class StormlibVaultTest(s_test.SynTest):

    async def test_stormlib_vault(self):

        async with self.getTestCore() as core:

            visi1 = await core.auth.addUser('visi1')
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
            opts = {'vars': {'iden': uiden}}
            self.true(await core.callStorm('return($lib.vault.set($iden, foo, bar))', opts=opts))

            # Set and delete data
            opts = {'vars': {'iden': uiden}}
            self.true(await core.callStorm('return($lib.vault.set($iden, foo2, bar2))', opts=opts))
            self.true(await core.callStorm('return($lib.vault.set($iden, foo2, $lib.undef))', opts=opts))

            # Get some data
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('return($lib.vault.getByIden($iden))', opts=opts)
            self.eq(ret.get('name'), 'uvault')
            self.eq(ret.get('iden'), uiden)
            self.eq(ret.get('data'), {'name': 'uvault', 'foo': 'bar'})

            # Open some vaults
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.getByType($vtype))', opts=opts)
            self.nn(vault)
            self.eq(vault.get('name'), 'uvault')
            self.eq(vault.get('data'), {'name': 'uvault', 'foo': 'bar'})

            # Set default and then getByType
            opts = {'vars': {'vtype': vtype}}
            self.true(await core.callStorm('return($lib.vault.setDefault($vtype, global))', opts=opts))

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.getByType($vtype))', opts=opts)
            self.nn(vault)
            self.eq(vault.get('name'), 'gvault')
            self.none(vault.get('data'))

            # List vaults
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(3, vaults)

            # Delete some vaults
            opts = {'vars': {'uiden': uiden}}
            self.true(await core.callStorm('return($lib.vault.del($uiden))', opts=opts))

            opts = {'vars': {'riden': riden}}
            self.true(await core.callStorm('return($lib.vault.del($riden))', opts=opts))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(1, vaults)

            # Set permissions on global vault
            opts = {'vars': {'iden': visi1.iden, 'giden': giden}}
            q = 'return($lib.vault.setPerm($giden, $iden, $lib.auth.easyperm.level.deny))'
            self.true(await core.callStorm(q, opts=opts))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(0, vaults)

    async def test_stormlib_vault_cmds(self):
        async with self.getTestCore() as core:

            visi1 = await core.auth.addUser('visi1')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            vtype = 'synapse-test'

            # vault.add
            opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}}
            msgs = await core.stormlist('vault.add uvault $vtype user $iden ({"apikey": "uvault"})', opts=opts)
            uvault = core.getVaultByName('uvault')
            uiden = uvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {uiden}', msgs)
            self.eq(uvault.get('data'), {'apikey': 'uvault'})

            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            msgs = await core.stormlist('vault.add rvault $vtype role $iden ({"apikey": "rvault"})', opts=opts)
            rvault = core.getVaultByName('rvault')
            riden = rvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {riden}', msgs)
            self.eq(rvault.get('data'), {'apikey': 'rvault'})

            uvault_out = split(f'''
            Vault: uvault
              Type: {vtype}
              Scope: user
              Iden: {uiden}
              Permissions:
                Users:
                  visi1: admin
                Roles: None
            ''')[1:]

            uvault_data = '  Data:\n    apikey: uvault'.split('\n')

            # vault.get
            msgs = await core.stormlist('vault.byname uvault --showdata')
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            for line in uvault_data:
                self.stormIsInPrint(line, msgs)

            # vault.get.byiden
            opts = {'vars': {'iden': uiden}}
            msgs = await core.stormlist('vault.byiden $iden --showdata', opts=opts)
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            for line in uvault_data:
                self.stormIsInPrint(line, msgs)

            # vault.set
            for key, val in (('foo', 'bar'), ('foo', '$lib.undef'), ('apikey', 'uvault1')):
                msgs = await core.stormlist(f'vault.set uvault {key} {val}')
                self.stormIsInPrint(f'Successfully set {key}={val} into vault uvault.', msgs)

            vault = core.getVaultByIden(uiden)
            self.eq(vault.get('data'), {'apikey': 'uvault1'})

            # vault.list
            opts = {'user': visi1.iden}
            msgs = await core.stormlist('vault.list --showdata', opts=opts)
            rvault_out = split(f'''
            Vault: rvault
              Type: {vtype}
              Scope: role
              Iden: {riden}
              Permissions:
                Users: None
                Roles:
                  contributor: read
            ''')[1:]

            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            for line in rvault_out:
                self.stormIsInPrint(line, msgs)

            # vault.bytype
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            msgs = await core.stormlist('vault.bytype $vtype', opts=opts)
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            msgs = await core.stormlist('vault.bytype $vtype --scope role', opts=opts)
            for line in rvault_out:
                self.stormIsInPrint(line, msgs)

            # vault.setperm
            opts = {'vars': {'vtype': vtype}}
            q = 'vault.set.perm rvault $lib.auth.users.byname(visi1).iden $lib.auth.easyperm.level.read'
            msgs = await core.stormlist(q, opts=opts)
            self.stormIsInPrint('Successfully set permissions on vault rvault.', msgs)

            vault = core.getVaultByName('rvault')
            self.true(core._hasEasyPerm(vault, visi1, s_cell.PERM_READ))

            # vault.setdefault
            opts = {'vars': {'vtype': vtype}}
            msgs = await core.stormlist('vault.set.default $vtype role', opts=opts)
            msg = f'Successfully set default scope to role for vault type {vtype}.'
            self.stormIsInPrint(msg, msgs)

            rvault_out = split(f'''
            Vault: rvault
              Type: {vtype}
              Scope: role
              Iden: {riden}
              Permissions:
                Users:
                  visi1: read
                Roles:
                  contributor: read
            ''')[1:]

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            msgs = await core.stormlist('vault.bytype $vtype', opts=opts)
            for line in rvault_out:
                self.stormIsInPrint(line, msgs)

            # vault.del
            msgs = await core.stormlist('vault.del uvault')
            self.stormIsInPrint('Successfully deleted vault uvault.', msgs)

            msgs = await core.stormlist('vault.del rvault')
            self.stormIsInPrint('Successfully deleted vault rvault.', msgs)
