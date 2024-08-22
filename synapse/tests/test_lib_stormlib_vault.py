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
            with self.raises(s_exc.AuthDeny) as exc:
                opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}, 'user': visi1.iden}
                await core.callStorm('return($lib.vault.add(uvault, $vtype, global, $iden, ({"name": "uvault"}), ({"server": "uvault"})))', opts=opts)
            self.eq('User visi1 cannot create global vaults.', exc.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny) as exc:
                opts = {'vars': {'vtype': vtype, 'iden': visi2.iden}, 'user': visi1.iden}
                await core.callStorm('return($lib.vault.add(uvault, $vtype, user, $iden, ({"name": "uvault"}), ({"server": "uvault"})))', opts=opts)
            self.eq(f'User visi1 cannot create vaults for user {visi2.iden}.', exc.exception.get('mesg'))

            opts = {'vars': {'vtype': vtype, 'iden': visi1.iden}}
            uiden = await core.callStorm('return($lib.vault.add(uvault, $vtype, user, $iden, ({"name": "uvault"}), ({"server": "uvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, uiden))

            vault = core.getVault(uiden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(uvault))')
            self.eq(ret.get('iden'), uiden)

            # Create role vault
            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            riden = await core.callStorm('return($lib.vault.add(rvault, $vtype, role, $iden, ({"name": "rvault"}), ({"server": "rvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, riden))

            vault = core.getVault(riden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(rvault))')
            self.eq(ret.get('iden'), riden)

            # Create global vault
            opts = {'vars': {'vtype': vtype, 'iden': None}}
            giden = await core.callStorm('return($lib.vault.add(gvault, $vtype, global, $iden, ({"name": "gvault"}), ({"server": "gvault"})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, giden))

            vault = core.getVault(giden)
            self.nn(vault)
            ret = await core.callStorm('return($lib.vault.byname(gvault))')
            self.eq(ret.get('iden'), giden)

            # Set some data
            opts = {'vars': {'iden': uiden}}
            await core.stormlist('$vault = $lib.vault.get($iden) $vault.secrets.foo = bar $vault.configs.p = np', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('secrets').get('foo'), 'bar')
            self.eq(vault.get('configs').get('p'), 'np')

            opts = {'vars': {'iden': uiden}, 'user': visi2.iden}
            msgs = await core.stormlist('$vault = $lib.vault.get($iden)', opts=opts)
            self.stormIsInErr(f'User requires read permission on vault: {uiden}.', msgs)

            # Set and delete data
            opts = {'vars': {'iden': uiden}}
            await core.callStorm('$vault = $lib.vault.get($iden) $vault.secrets.foo2 = bar2 $vault.configs.p2 = np2', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('secrets').get('foo2'), 'bar2')
            self.eq(vault.get('configs').get('p2'), 'np2')

            await core.callStorm('$vault = $lib.vault.get($iden) $vault.secrets.foo2 = $lib.undef $vault.configs.p2 = $lib.undef', opts=opts)
            vault = core.getVault(uiden)
            self.eq(vault.get('secrets').get('foo2', s_common.novalu), s_common.novalu)
            self.eq(vault.get('configs').get('p2', s_common.novalu), s_common.novalu)

            # Get some data
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('return($lib.vault.get($iden))', opts=opts)
            self.eq(ret.get('name'), 'uvault')
            self.eq(ret.get('iden'), uiden)
            self.eq(ret.get('secrets'), {'name': 'uvault', 'foo': 'bar'})
            self.eq(ret.get('configs'), {'server': 'uvault', 'p': 'np'})

            ret = await core.callStorm('return($lib.vault.get($iden).secrets.foo)', opts=opts)
            self.eq(ret, 'bar')

            ret = await core.callStorm('return($lib.vault.get($iden).configs.p)', opts=opts)
            self.eq(ret, 'np')

            msgs = await core.stormlist('$lib.print($lib.vault.get($iden).secrets)', opts=opts)
            self.stormIsInPrint("{'name': 'uvault', 'foo': 'bar'}", msgs)

            msgs = await core.stormlist('$lib.print($lib.vault.get($iden).configs)', opts=opts)
            self.stormIsInPrint("{'server': 'uvault', 'p': 'np'}", msgs)

            self.none(await core.callStorm('return($lib.vault.get($iden).secrets.newp)', opts=opts))
            self.none(await core.callStorm('return($lib.vault.get($iden).configs.newp)', opts=opts))

            msgs = await core.stormlist('for ($key, $val) in $lib.vault.get($iden).secrets { $lib.print(`{$key} = {$val}`) }', opts=opts)
            self.stormIsInPrint('name = uvault', msgs)
            self.stormIsInPrint('foo = bar', msgs)

            msgs = await core.stormlist('for ($key, $val) in $lib.vault.get($iden).configs { $lib.print(`{$key} = {$val}`) }', opts=opts)
            self.stormIsInPrint('server = uvault', msgs)
            self.stormIsInPrint('p = np', msgs)

            # Open some vaults
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.bytype($vtype))', opts=opts)
            self.nn(vault)
            self.eq(vault.get('name'), 'uvault')
            self.eq(vault.get('secrets'), {'name': 'uvault', 'foo': 'bar'})
            self.eq(vault.get('configs'), {'server': 'uvault', 'p': 'np'})

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.bytype($vtype, scope=global))', opts=opts)
            self.nn(vault)
            self.eq(vault.get('name'), 'gvault')
            self.none(vault.get('secrets'))
            self.eq(vault.get('configs'), {'server': 'gvault'})

            opts = {'user': visi1.iden}
            vault = await core.callStorm('return($lib.vault.bytype(newp, scope=global))', opts=opts)
            self.none(vault)

            # List vaults
            opts = {'user': visi1.iden}
            self.eq(3, await core.callStorm('return($lib.len($lib.vault.list()))', opts=opts))

            # Delete some vaults
            opts = {'vars': {'uiden': uiden}}
            await core.callStorm('$vault = $lib.vault.get($uiden) return($vault.delete())', opts=opts)
            self.none(core.getVault(uiden))

            opts = {'vars': {'riden': riden}}
            await core.callStorm('$vault = $lib.vault.get($riden) return($vault.delete())', opts=opts)
            self.none(core.getVault(riden))

            # List vaults again
            opts = {'user': visi1.iden}
            self.eq(1, await core.callStorm('return($lib.len($lib.vault.list()))', opts=opts))

            # Rename vault
            opts = {'vars': {'giden': giden}}
            self.eq('gvault', await core.callStorm('return($lib.vault.get($giden).name)', opts=opts))
            q = '$lib.vault.get($giden).name = foobar'
            await core.callStorm(q, opts=opts)
            vault = core.getVault(giden)
            self.eq(vault.get('name'), 'foobar')
            self.nn(await core.callStorm('return($lib.vault.byname(foobar))'))
            await self.asyncraises(s_exc.NoSuchName, core.callStorm('return($lib.vault.byname(gvault))'))

            # Get secrets without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.vault.get($giden).secrets)'
            self.none(await core.callStorm(q, opts=opts))

            # replace secrets
            opts = {'vars': {'giden': giden}}
            q = '$lib.vault.get($giden).secrets = ({"apikey": "foobar"}) return($lib.vault.get($giden).secrets)'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'apikey': 'foobar'})

            # replace secrets without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = '$lib.vault.get($giden).secrets = ({"apikey": "foobar2"})'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=opts)

            # Get configs without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.vault.get($giden).configs)'
            self.eq(await core.callStorm(q, opts=opts), {'server': 'gvault'})

            # Set config item without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = '$configs=$lib.vault.get($giden).configs $configs.foo=bar return($configs)'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=opts)

            # replace configs
            opts = {'vars': {'giden': giden}}
            q = '$lib.vault.get($giden).configs = ({"server": "foobar"}) return($lib.vault.get($giden).configs)'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'server': 'foobar'})

            # replace configs without EDIT perms
            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = '$lib.vault.get($giden).configs = ({"server": "foobar2"})'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=opts)

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

            opts = {'user': visi1.iden}
            self.eq(0, await core.callStorm('return($lib.len($lib.vault.list()))', opts=opts))

            # Remove permission on global vault
            opts = {'vars': {'iden': visi1.iden, 'giden': giden}}
            q = '$vault = $lib.vault.get($giden) return($vault.setPerm($iden, $lib.null))'
            self.true(await core.callStorm(q, opts=opts))

            opts = {'user': visi1.iden}
            self.eq(1, await core.callStorm('return($lib.len($lib.vault.list()))', opts=opts))

            # Runtime asroot

            await core.addStormPkg({
                'name': 'vpkg',
                'version': '0.0.1',
                'modules': [
                    {
                        'name': 'vmod',
                        'asroot': True,
                        'storm': '''
                            function setSecret(iden, key, valu) {
                                $secrets = $lib.vault.get($iden).secrets
                                $secrets.$key = $valu
                                return($secrets)
                            }

                            function smashSecrets(iden, dict) {
                                $vault = $lib.vault.get($iden)
                                $vault.secrets = $dict
                                return($vault.secrets)
                            }

                            function setConfig(iden, key, valu) {
                                $configs = $lib.vault.get($iden).configs
                                $configs.$key = $valu
                                return($configs)
                            }

                            function smashConfigs(iden, dict) {
                                $vault = $lib.vault.get($iden)
                                $vault.configs = $dict
                                return($vault.configs)
                            }
                        '''
                    },
                ],
            })

            await core.nodes('auth.user.addrule visi1 storm.asroot.mod.vmod')

            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.import(vmod).setSecret($giden, foo, bar))'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'apikey': 'foobar', 'foo': 'bar'})

            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.import(vmod).smashSecrets($giden, ({"apikey": "new"})))'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'apikey': 'new'})

            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.import(vmod).setConfig($giden, foo, bar))'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'server': 'foobar', 'foo': 'bar'})

            opts = {'vars': {'giden': giden}, 'user': visi1.iden}
            q = 'return($lib.import(vmod).smashConfigs($giden, ({"server": "new"})))'
            ret = await core.callStorm(q, opts=opts)
            self.eq(ret, {'server': 'new'})

    async def test_stormlib_vault_cmds(self):
        async with self.getTestCore() as core:

            visi1 = await core.auth.addUser('visi1')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            vtype = 'synapse-test'

            # vault.add
            opts = {'vars': {'vtype': vtype}}
            msgs = await core.stormlist('vault.add uvault $vtype ({"apikey": "uvault"}) ({"server": "uvault"}) --user visi1', opts=opts)
            uvault = core.getVaultByName('uvault')
            uiden = uvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {uiden}', msgs)
            self.eq(uvault.get('secrets'), {'apikey': 'uvault'})
            self.eq(uvault.get('configs'), {'server': 'uvault'})

            opts = {'vars': {'vtype': vtype}}
            msgs = await core.stormlist('vault.add rvault $vtype ({"apikey": "rvault"}) ({"server": "rvault"}) --role contributor', opts=opts)
            rvault = core.getVaultByName('rvault')
            riden = rvault.get('iden')
            self.stormIsInPrint(f'Vault created with iden: {riden}', msgs)
            self.eq(rvault.get('secrets'), {'apikey': 'rvault'})
            self.eq(rvault.get('configs'), {'server': 'rvault'})

            uvault_out = split(f'''
            Vault: {uiden}
              Name: uvault
              Type: {vtype}
              Scope: user
              Permissions:
                Users:
                  visi1: admin
                Roles: None
              Configs:
                server: uvault
            ''')[1:]

            uvault_secrets = '  Secrets:\n    apikey: uvault'.split('\n')

            # vault.byname
            msgs = await core.stormlist('vault.list --name uvault --showsecrets')
            for line in uvault_out:
                self.stormIsInPrint(line, msgs)

            for line in uvault_secrets:
                self.stormIsInPrint(line, msgs)

            # vault.set
            for key, val in (('foo', 'bar'), ('apikey', 'uvault1')):
                msgs = await core.stormlist(f'vault.set.secrets uvault {key} --value {val}')
                self.stormIsInPrint(f'Set {key}={val} into vault secrets: uvault.', msgs)

            for key, val in (('color', 'orange'), ('server', 'uvault1')):
                msgs = await core.stormlist(f'vault.set.configs uvault {key} --value {val}')
                self.stormIsInPrint(f'Set {key}={val} into vault configs: uvault.', msgs)

            msgs = await core.stormlist('vault.set.secrets uvault foo --delete')
            self.stormIsInPrint('Removed foo from vault secrets: uvault.', msgs)

            msgs = await core.stormlist('vault.set.configs uvault color --delete')
            self.stormIsInPrint('Removed color from vault configs: uvault.', msgs)

            vault = core.getVault(uiden)
            self.eq(vault.get('secrets'), {'apikey': 'uvault1'})
            self.eq(vault.get('configs'), {'server': 'uvault1'})

            # vault.list
            opts = {'user': visi1.iden}
            msgs = await core.stormlist('vault.list --showsecrets', opts=opts)
            rvault_out = split(f'''
            Vault: {riden}
              Name: rvault
              Type: {vtype}
              Scope: role
              Permissions:
                Users: None
                Roles:
                  contributor: read
              Configs:
                server: rvault
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
            Vault: {riden}
              Name: rvault
              Type: {vtype}
              Scope: role
              Permissions:
                Users:
                  visi1: read
                Roles:
                  contributor: read
              Configs:
                server: rvault
            ''')[1:]

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            msgs = await core.stormlist('vault.list --type $vtype', opts=opts)
            for line in rvault_out:
                self.stormIsInPrint(line, msgs)

            msgs = await core.stormlist('vault.set.perm rvault --level admin --role contributor')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Successfully set permissions on vault rvault.', msgs)

            msgs = await core.stormlist('vault.list --type $vtype', opts=opts)
            self.stormIsInPrint('contributor: admin', msgs)

            # vault.del
            msgs = await core.stormlist('vault.del uvault')
            self.stormIsInPrint('Successfully deleted vault uvault.', msgs)

            msgs = await core.stormlist('vault.del rvault')
            self.stormIsInPrint('Successfully deleted vault rvault.', msgs)
