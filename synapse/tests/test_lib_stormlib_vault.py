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
            uiden = await core.callStorm('return($lib.vault.add($vtype, $iden, ({})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, uiden))

            vault = core.getVault(uiden)
            self.nn(vault)

            # Create role vault
            opts = {'vars': {'vtype': vtype, 'iden': contributor.iden}}
            riden = await core.callStorm('return($lib.vault.add($vtype, $iden, ({})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, riden))

            vault = core.getVault(uiden)
            self.nn(vault)

            # Create global vault
            opts = {'vars': {'vtype': vtype, 'iden': None}}
            giden = await core.callStorm('return($lib.vault.add($vtype, $iden, ({})))', opts=opts)
            self.nn(regex.match(s_config.re_iden, giden))

            vault = core.getVault(uiden)
            self.nn(vault)

            # Set some data
            data = {'foo': 'bar'}
            opts = {'vars': {'iden': uiden, 'data': data}}
            self.true(await core.callStorm('return($lib.vault.set($iden, $data))', opts=opts))

            # Get some data
            opts = {'vars': {'iden': uiden}}
            ret = await core.callStorm('return($lib.vault.get($iden))', opts=opts)
            self.eq(ret, data)

            # Open some vaults
            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            iden = await core.callStorm('return($lib.vault.open($vtype))', opts=opts)
            self.eq(iden, uiden)

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            iden = await core.callStorm('return($lib.vault.open($vtype, role))', opts=opts)
            self.eq(iden, riden)

            # Set default and then open
            opts = {'vars': {'vtype': vtype}}
            self.true(await core.callStorm('return($lib.vault.setDefault($vtype, global))', opts=opts))

            opts = {'vars': {'vtype': vtype}, 'user': visi1.iden}
            iden = await core.callStorm('return($lib.vault.open($vtype))', opts=opts)
            self.eq(iden, giden)

            # List vaults
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(3, vaults)

            # Delete some vaults
            opts = {'vars': {'iden': uiden}}
            self.true(await core.callStorm('return($lib.vault.del($iden))', opts=opts))

            opts = {'vars': {'iden': riden}}
            self.true(await core.callStorm('return($lib.vault.del($iden))', opts=opts))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(1, vaults)

            # Set permissions on global vault
            opts = {'vars': {'viden': giden, 'iden': visi1.iden}}
            q = 'return($lib.vault.setPerm($viden, $iden, $lib.auth.easyperm.level.deny))'
            self.true(await core.callStorm(q, opts=opts))

            # List vaults again
            opts = {'user': visi1.iden}
            ret = await core.callStorm('return($lib.vault.list())', opts=opts)
            vaults = [k async for k in ret]
            self.len(0, vaults)
