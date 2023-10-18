import textwrap

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_test

def split(text):
    return textwrap.dedent(text).split('\n')

class StormlibVaultTest(s_test.SynTest):

    async def test_stormlib_vault(self):

        async with self.getTestCore() as core:

            visi1 = await core.auth.addUser('visi1')
            visi2 = await core.auth.addUser('visi2')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            vtype = 'synapse-test'

            # Create user vault
            opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}}
            uiden = await core.callStorm('return($lib.vault.add(uvault, $vtype, user, $iden, ({"name": "uvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, uiden))

            vault = core.getVault(uiden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(uvault))')
            self.eq(ret.get('iden'), uiden)

            # Create role vault
            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            riden = await core.callStorm('return($lib.vault.add(rvault, $vtype, role, $iden, ({"name": "rvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, riden))

            vault = core.getVault(riden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(rvault))')
            self.eq(ret.get('iden'), riden)

            # Create global vault
            opts = {'vars': {'vtype': vtype, 'iden': None}}
            giden = await core.callStorm('return($lib.vault.add(gvault, $vtype, global, $iden, ({"name": "gvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, giden))

            vault = core.getVault(giden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(gvault))')
            self.eq(ret.get('iden'), giden)

            # Set some data
            opts = {'vars': {'iden': uiden}}
            await core.stormlist('$vault = $lib.vault.get($iden) $vault.data.foo = bar', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('data').get('foo'), 'bar')

            opts = {'vars': {'iden': uiden}, 'user': visi2.iden}
            msgs = await core.stormlist('$vault = $lib.vault.get($iden)', opts=opts)
            self.stormIsInErr(f'Insufficient permissions for user visi2 to vault {uiden}.', msgs)

            # Set and delete data
            opts = {'vars': {'iden': uiden}}
            await core.callStorm('$vault = $lib.vault.get($iden) $vault.data.foo2 = bar2', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('data').get('foo2'), 'bar2')

            await core.callStorm('$vault = $lib.vault.get($iden) $vault.data.foo2 = $lib.undef', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('data').get('foo2', s_common.novalu), s_common.novalu)

            # Get some data
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('return($lib.vault.get($iden))', opts=opts)
            self.eq(ret.get('name'), 'uvault')
            self.eq(ret.get('iden'), uiden)
            self.eq(ret.get('data'), {'name': 'uvault', 'foo': 'bar'})

            ret = await core.callStorm('return($lib.vault.get($iden).data.foo)', opts=opts)
            self.eq(ret, 'bar')

            self.none(await core.callStorm('return($lib.vault.get($iden).data.newp)', opts=opts))

            msgs = await core.stormlist('for ($key, $val) in $lib.vault.get($iden).data { $lib.print(`{$key} = {$val}`) }', opts=opts)
            self.stormIsInPrint('name = uvault', msgs)
            self.stormIsInPrint('foo = bar', msgs)

            # Open some vaults
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.bytype($vtype))', opts=opts)
            self.nn(vault)
            self.eq(vault.get('name'), 'uvault')
            self.eq(vault.get('data'), {'name': 'uvault', 'foo': 'bar'})

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.bytype($vtype, scope=global))', opts=opts)
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
            await core.callStorm('$vault = $lib.vault.get($uiden) return($vault.delete())', opts=opts)
            self.none(core.getVault(uiden))

            opts = {'vars': {'riden': riden}}
            await core.callStorm('$vault = $lib.vault.get($riden) return($vault.delete())', opts=opts)
            self.none(core.getVault(riden))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(1, vaults)

            # Rename vault
            opts = {'vars': {'giden': giden}}
            q = '$lib.vault.get($giden).name = foobar'
            await core.callStorm(q, opts=opts)
            vault = core.getVault(giden)
            self.eq(vault.get('name'), 'foobar')

            # Get data without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.vault.get($giden).data)'
            self.none(await core.callStorm(q, opts=opts))

            # Set name without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            with self.raises(s_exc.AuthDeny):
                q = '$lib.vault.get($giden).name = foo'
                await core.callStorm(q, opts=opts)

            # repr check
            msgs = await core.stormlist('$lib.print($lib.vault.get($giden))', opts=opts)
            self.stormIsInPrint(f'vault: {giden}', msgs)

            msgs = await core.stormlist('$foo = ({"foo": $lib.vault.get($giden)}) $lib.print($foo)', opts=opts)
            self.stormIsInPrint(r"{'foo': vault: " + f'{giden}}}', msgs)

            # Set permissions on global vault
            opts = {'vars': {'iden': visi1.iden, 'giden': giden}}
            q = '$vault = $lib.vault.get($giden) return($vault.setPerm($iden, $lib.auth.easyperm.level.deny))'
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
            opts = {'vars': {'vtype': vtype}}
            msgs = await core.stormlist('vault.add uvault $vtype ({"apikey": "uvault"}) --user visi1', opts=opts)
            uvault = core.getVaultByName('uvault')
            uiden = uvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {uiden}', msgs)
            self.eq(uvault.get('data'), {'apikey': 'uvault'})

            opts = {'vars': {'vtype': vtype}}
            msgs = await core.stormlist('vault.add rvault $vtype ({"apikey": "rvault"}) --role contributor', opts=opts)
            rvault = core.getVaultByName('rvault')
            riden = rvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {riden}', msgs)
            self.eq(rvault.get('data'), {'apikey': 'rvault'})

            uvault_out = split(f'''
            Vault: {uiden}
              Name: uvault
              Type: {vtype}
              Scope: user
              Permissions:
                Users:
                  visi1: admin
                Roles: None
            ''')[1:]

            uvault_data = '  Data:\n    apikey: uvault'.split('\n')

            # vault.byname
            msgs = await core.stormlist('vault.list --name uvault --showdata')
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            for line in uvault_data:
                self.stormIsInPrint(line, msgs)

            # vault.set
            for key, val in (('foo', 'bar'), ('apikey', 'uvault1')):
                msgs = await core.stormlist(f'vault.set uvault {key} --value {val}')
                self.stormIsInPrint(f'Set {key}={val} into vault uvault.', msgs)

            msgs = await core.stormlist('vault.set uvault foo --delete')
            self.stormIsInPrint('Removed foo from vault uvault', msgs)

            vault = core.getVault(uiden)
            self.eq(vault.get('data'), {'apikey': 'uvault1'})

            # vault.list
            opts = {'user': visi1.iden}
            msgs = await core.stormlist('vault.list --showdata', opts=opts)
            rvault_out = split(f'''
            Vault: {riden}
              Name: rvault
              Type: {vtype}
              Scope: role
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
            msgs = await core.stormlist('vault.list --type $vtype', opts=opts)
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            msgs = await core.stormlist('vault.list --type $vtype', opts=opts)
            for line in rvault_out:
                self.stormIsInPrint(line, msgs)

            # vault.set.perm
            opts = {'vars': {'vtype': vtype}}
            q = 'vault.set.perm rvault --level read --user visi1'
            msgs = await core.stormlist(q, opts=opts)
            self.stormIsInPrint('Successfully set permissions on vault rvault.', msgs)

            vault = core.getVaultByName('rvault')
            self.true(core._hasEasyPerm(vault, visi1, s_cell.PERM_READ))

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
            msgs = await core.stormlist('vault.list --type $vtype', opts=opts)
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            # vault.del
            msgs = await core.stormlist('vault.del uvault')
            self.stormIsInPrint('Successfully deleted vault uvault.', msgs)

            msgs = await core.stormlist('vault.del rvault')
            self.stormIsInPrint('Successfully deleted vault rvault.', msgs)
