import synapse.exc as s_exc

import synapse.lib.cell as s_cell
import synapse.lib.layer as s_layer

import synapse.tests.utils as s_test

class StormlibEasyPermTest(s_test.SynTest):

    async def test_stormlib_easyperm_basics(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            someuser = await core.auth.addUser('someuser')
            alliden = (await core.getRoleDefByName('all'))['iden']

            opts = {'user': visi.iden}
            exp = {'permissions': {'users': {visi.iden: s_cell.PERM_ADMIN}, 'roles': {}, 'default': s_cell.PERM_READ}}

            retn = await core.callStorm('return($lib.auth.easyperm.init())', opts=opts)
            self.eq(retn, exp)

            exp['foo'] = 'bar'
            retn = await core.callStorm('return($lib.auth.easyperm.init(({"foo": "bar"})))', opts=opts)
            self.eq(retn, exp)

            opts['vars'] = {'edef': retn, 'user': someuser.iden}
            exp['permissions']['users'][someuser.iden] = s_cell.PERM_EDIT

            q = 'return($lib.auth.easyperm.set($edef, users, $user, $lib.auth.easyperm.level.edit))'
            retn = await core.callStorm(q, opts=opts)
            self.eq(retn, exp)

            opts = {'user': someuser.iden, 'vars': {'edef': retn}}
            q = 'return($lib.auth.easyperm.allowed($edef, $lib.auth.easyperm.level.edit))'
            self.true(await core.callStorm(q, opts=opts))

            q = 'return($lib.auth.easyperm.allowed($edef, $lib.auth.easyperm.level.admin))'
            self.false(await core.callStorm(q, opts=opts))

            q = 'return($lib.auth.easyperm.allowed($edef, $lib.auth.easyperm.level.admin))'
            self.true(await core.callStorm(q, opts={'vars': {'edef': retn}}))

            q = '$lib.auth.easyperm.confirm($edef, $lib.auth.easyperm.level.admin)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(q, opts=opts))

            opts = {'user': visi.iden, 'vars': {'edef': retn, 'role': alliden}}
            exp['permissions']['roles'][alliden] = s_cell.PERM_DENY

            q = 'return($lib.auth.easyperm.set($edef, roles, $role, $lib.auth.easyperm.level.deny))'
            retn = await core.callStorm(q, opts=opts)
            self.eq(retn, exp)

            exp['permissions']['roles'].pop(alliden)

            q = 'return($lib.auth.easyperm.set($edef, roles, $role, $lib.null))'
            retn = await core.callStorm(q, opts=opts)
            self.eq(retn, exp)

            q = '$lib.auth.easyperm.init(foo)'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q))

            q = '$lib.auth.easyperm.set(foo, roles, bar, $lib.auth.easyperm.level.deny)'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q))

            q = '$lib.auth.easyperm.allowed(foo, $lib.auth.easyperm.level.admin)'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q))

            q = '$lib.auth.easyperm.confirm(foo, $lib.auth.easyperm.level.admin)'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q))

            q = 'return($lib.auth.easyperm.init(({})))'
            obj = await core.callStorm(q)
            self.eq(obj['permissions'].get('default'), s_cell.PERM_READ)

            opts = {'vars': {'obj': obj}, 'user': visi.iden}
            q = 'return($lib.auth.easyperm.allowed($obj, $lib.auth.easyperm.level.read))'
            self.true(await core.callStorm(q, opts=opts))

            q = 'return($lib.auth.easyperm.init(({}), default=$lib.auth.easyperm.level.deny))'
            obj = await core.callStorm(q)
            self.eq(obj['permissions'].get('default'), s_cell.PERM_DENY)

            opts = {'vars': {'obj': obj}, 'user': visi.iden}
            q = 'return($lib.auth.easyperm.allowed($obj, $lib.auth.easyperm.level.read))'
            self.false(await core.callStorm(q, opts=opts))

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.auth.easyperm.init(({}), default=(-1))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.auth.easyperm.init(({}), default=(6))')
