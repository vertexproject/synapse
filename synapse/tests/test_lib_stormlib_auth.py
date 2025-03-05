import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json

import synapse.tests.utils as s_test

visishow = '''
User: visi (8d19302a671c3d5c8eeaccde305413a0)

  Locked: false
  Admin: false
  Email: visi@vertex.link
  Rules:
    [0  ] - !baz.faz
    [1  ] - foo.bar

  Roles:
    67b0c61b6a5307851c893a1bd84ce19d - indxrole
    878e79f585e74258d2a33ccdf817a47f - all
    1284e1976e8a4ad139a976482adb1588 - ninjas

  Gates:
    14aaa84884773c7791a388e48ca93029 - (layer)
      Admin: false
      [0  ] - node
'''.strip()

ninjashow = '''
Role: ninjas (3c5318903adb4bbd67e100331d37961d)

  Rules:
    [0  ] - !baz.faz
    [1  ] - foo.bar

  Gates:
    734245de81ccb4284f0a169be9b81aa8 - (layer)
      [0  ] - node
'''.strip()

gateshow = '''
Gate Type: layer

Auth Gate Users:
  b1d8d5b4c946399113a25ebed44f490b - root
    Admin: true
    Rules:
  59f9e2c6d6f7cfae6dabe313a1f55396 - visi
    Admin: false
    Rules:
     [0  ] - node

Auth Gate Roles:
  ecc3af3226446018d86ed673cba73abc - all
    Rules:
      [0  ] - layer.read
  9e9ad4a26a7ccfef6416d142f276b357 - ninjas
    Rules:
      [0  ] - node
'''.strip()

coolshow = '''
User: cool (8d19302a671c3d5c8eeaccde305413a0)

  Locked: false
  Admin: true
  Email: foo@bar.com
  Rules:

  Roles:
    67b0c61b6a5307851c893a1bd84ce19d - indxrole
    878e79f585e74258d2a33ccdf817a47f - all
    1284e1976e8a4ad139a976482adb1588 - ninjas

  Gates:
    14aaa84884773c7791a388e48ca93029 - (layer)
      Admin: false
      [0  ] - node
'''.strip()

userlist = '''
Users:
  root

Locked Users:
  cool
'''.strip()

rolelist = '''
Roles:
  all
  indxrole
  ninjas
'''.strip()

class StormLibAuthTest(s_test.SynTest):

    async def test_stormlib_auth(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('auth.user.delrule visi foo.bar')
            self.stormIsInWarn('User (visi) not found!', msgs)

            msgs = await core.stormlist('auth.role.delrule ninjas foo.bar')
            self.stormIsInWarn('Role (ninjas) not found!', msgs)

            msgs = await core.stormlist('auth.user.add --email visi@vertex.link visi')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('User (visi) added with iden: ', msgs)

            msgs = await core.stormlist('auth.role.add ninjas')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Role (ninjas) added with iden: ', msgs)

            msgs = await core.stormlist('auth.role.add test')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Role (test) added with iden: ', msgs)

            msgs = await core.stormlist('auth.role.add indxrole')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Role (indxrole) added with iden: ', msgs)

            msgs = await core.stormlist('auth.user.grant visi ninjas')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Granting role ninjas to user visi.', msgs)

            msgs = await core.stormlist('auth.user.grant visi test')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Granting role test to user visi.', msgs)

            msgs = await core.stormlist('auth.user.grant visi indxrole --index 0')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Granting role indxrole to user visi.', msgs)

            msgs = await core.stormlist('auth.user.revoke visi test')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Revoking role test from user visi.', msgs)

            msgs = await core.stormlist('auth.user.addrule visi foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule foo.bar to user visi.', msgs)
            msgs = await core.stormlist('auth.user.addrule visi --index 0 "!baz.faz"')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule !baz.faz to user visi.', msgs)

            msgs = await core.stormlist('auth.user.allowed visi baz.faz')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('allowed: false - Matched user rule (!baz.faz).', msgs, deguid=True)

            msgs = await core.stormlist('auth.role.addrule ninjas foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule foo.bar to role ninjas.', msgs)
            msgs = await core.stormlist('auth.role.addrule ninjas --index 0 "!baz.faz"')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule !baz.faz to role ninjas.', msgs)

            msgs = await core.stormlist('auth.user.revoke visi test')
            self.stormIsInWarn('User visi does not have role test', msgs)

            msgs = await core.stormlist('auth.user.delrule visi --index 10')
            self.stormIsInErr('only has 2 rules', msgs)

            msgs = await core.stormlist('auth.role.delrule ninjas --index 10')
            self.stormIsInErr('only has 2 rules', msgs)

            msgs = await core.stormlist('auth.user.addrule visi node --gate $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('auth.user.allowed visi node.tag.del')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('allowed: false - No matching rule found.', msgs, deguid=True)

            msgs = await core.stormlist('auth.user.allowed root node.tag.del')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('allowed: true - The user is a global admin.', msgs, deguid=True)

            msgs = await core.stormlist('auth.user.allowed visi node.tag.del --gate $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('allowed: true - Matched user rule (node) on gate 741529fa80e3fb42f63c5320e4bf348f.',
                msgs, deguid=True)

            msgs = await core.stormlist('auth.user.mod visi --gate $lib.view.get().layers.0.iden')
            self.stormIsInWarn('Granting/revoking admin status on an auth gate, requires the use of `--admin <true|false>` also.', msgs)

            msgs = await core.stormlist('auth.user.mod visi --admin $lib.true --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('User (visi) admin status set to true for auth gate 741529fa80e3fb42f63c5320e4bf348f.',
                                msgs, deguid=True)
            msgs = await core.stormlist('auth.user.allowed visi node.tag.del --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('allowed: true - The user is an admin of auth gate 741529fa80e3fb42f63c5320e4bf348f',
                                msgs, deguid=True)
            msgs = await core.stormlist('auth.user.mod visi --admin $lib.false --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('User (visi) admin status set to false for auth gate 741529fa80e3fb42f63c5320e4bf348f.',
                                msgs, deguid=True)
            msgs = await core.stormlist('auth.user.allowed visi node.tag.del --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('allowed: true - Matched user rule (node) on gate 741529fa80e3fb42f63c5320e4bf348f',
                                msgs, deguid=True)

            await core.nodes('auth.role.addrule ninjas beep.sys --gate $lib.view.get().layers.0.iden')
            msgs = await core.stormlist('auth.user.allowed visi beep.sys --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('Matched role rule (beep.sys) for role ninjas on gate 741529fa80e3fb42f63c5320e4bf348f',
                                msgs, deguid=True)
            await core.nodes('auth.role.addrule ninjas beep.sys')
            msgs = await core.stormlist('auth.user.allowed visi beep.sys')
            self.stormIsInPrint('Matched role rule (beep.sys) for role ninjas', msgs)

            # Cleanup ninjas
            await core.nodes('auth.role.delrule ninjas beep.sys')
            await core.nodes('auth.role.delrule ninjas beep.sys --gate $lib.view.get().layers.0.iden')

            msgs = await core.stormlist('auth.role.addrule ninjas node --gate $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)

            self.eq([(True, ('node',))], await core.callStorm('''
                return($lib.auth.users.byname(visi).getRules(gateiden=$lib.view.get().layers.0.iden))'''))
            self.eq([(True, ('node',))], await core.callStorm('''
                return($lib.auth.roles.byname(ninjas).getRules(gateiden=$lib.view.get().layers.0.iden))'''))

            self.ge(len(await core.callStorm('return($lib.auth.gates.list())')), 1)

            gates = await core.callStorm('return($lib.auth.users.byname(visi).gates())')
            self.eq(gates[0]['type'], 'layer')
            gates = await core.callStorm('return($lib.auth.roles.byname(ninjas).gates())')
            self.eq(gates[0]['type'], 'layer')

            msgs = await core.stormlist('auth.user.show newp')
            self.stormIsInWarn('No user named: newp', msgs)

            msgs = await core.stormlist('auth.role.show newp')
            self.stormIsInWarn('No role named: newp', msgs)

            msgs = await core.stormlist('auth.gate.show newp')
            self.stormIsInWarn('No auth gate found for iden: newp.', msgs)

            msgs = await core.stormlist('auth.user.show visi')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint(visishow, msgs, deguid=True)

            msgs = await core.stormlist('auth.role.show ninjas')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint(ninjashow, msgs, deguid=True)

            msgs = await core.stormlist('auth.gate.show $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint(gateshow, msgs, deguid=True)

            msgs = await core.stormlist('auth.user.delrule visi foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Removed rule foo.bar from user visi.', msgs)
            msgs = await core.stormlist('auth.user.delrule visi --index 0')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Removed rule !baz.faz from user visi.', msgs)

            msgs = await core.stormlist('auth.role.delrule ninjas foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Removed rule foo.bar from role ninjas.', msgs)
            msgs = await core.stormlist('auth.role.delrule ninjas --index 0')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Removed rule !baz.faz from role ninjas.', msgs)

            self.nn(await core.callStorm('return($lib.auth.getPermDef((node,)))'))
            self.none(await core.callStorm('return($lib.auth.getPermDef((foo, bar)))'))

            defs = await core.callStorm('return($lib.auth.getPermDefs())')
            self.ge(len(defs), 10)
            self.nn(defs[0].get('perm'))
            self.nn(defs[0].get('desc'))
            # make sure lib perms are getting added
            perms = [d['perm'] for d in defs]
            self.isin(('globals', 'get'), perms)

            msgs = await core.stormlist('auth.user.mod visi --name cool --locked $lib.true')
            self.stormIsInPrint('User (visi) renamed to cool.', msgs)
            self.stormIsInPrint('User (visi) locked status set to true.', msgs)

            msgs = await core.stormlist('auth.user.allowed cool woot')
            self.stormIsInPrint('allowed: false - The user is locked.', msgs)

            msgs = await core.stormlist('auth.user.list')
            self.stormIsInPrint(userlist, msgs)

            opts = {'vars': {'pass': 'bar'}}
            q = '''
            auth.user.mod cool
                --email "foo@bar.com"
                --locked $lib.false
                --passwd $pass
                --admin $lib.true
            '''
            msgs = await core.stormlist(q, opts=opts)
            self.stormIsInPrint('User (cool) email address set to foo@bar.com.', msgs)
            self.stormIsInPrint('User (cool) password updated.', msgs)
            self.stormIsInPrint('User (cool) locked status set to false.', msgs)
            self.stormIsInPrint('User (cool) admin status set to true.', msgs)

            self.nn(await core.tryUserPasswd('cool', 'bar'))

            msgs = await core.stormlist('auth.user.show cool')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint(coolshow, msgs, deguid=True)

            msgs = await core.stormlist('auth.role.list')
            self.stormIsInPrint(rolelist, msgs)

            msgs = await core.stormlist('auth.role.mod ninjas --name admins')
            self.stormIsInPrint('Role (ninjas) renamed to admins.', msgs)

            msgs = await core.stormlist('auth.role.mod ninjas --name admins')
            self.stormIsInWarn('Role (ninjas) not found!', msgs)

            msgs = await core.stormlist('auth.role.del admins')
            self.stormIsInPrint('Role (admins) deleted.', msgs)

            msgs = await core.stormlist('auth.role.del admins')
            self.stormIsInWarn('Role (admins) not found!', msgs)

            msgs = await core.stormlist('auth.perms.list')
            self.stormIsInPrint('node.add.<form>', msgs)
            self.stormIsInPrint('Controls access to add a new view including forks.', msgs)
            self.stormIsInPrint('default: false', msgs)

            msgs = await core.stormlist('auth.perms.list --find macro.')
            self.stormIsInPrint('storm.macro.add', msgs)
            self.stormIsInPrint('storm.macro.admin', msgs)
            self.stormIsInPrint('storm.macro.edit', msgs)
            self.stormNotInPrint('node.add.<form>', msgs)

            msgs = await core.stormlist('auth.perms.list --find url')
            self.stormIsInPrint('storm.lib.telepath.open.<scheme>', msgs)
            self.stormIsInPrint('Controls the ability to open a telepath URL with a specific URI scheme.', msgs)
            self.stormNotInPrint('node.add.<form>', msgs)

    async def test_stormlib_auth_default_allow(self):
        async with self.getTestCore() as core:

            stormpkg = {
                'name': 'authtest',
                'version': '0.0.1',
                'perms': (
                    {'perm': ('authtest', 'perm'), 'desc': 'Default deny', 'gate': 'cortex'},
                    {'perm': ('authtest', 'perm2'), 'desc': 'Default allow', 'gate': 'cortex', 'default': True},
                ),
                'modules': (
                    {
                     'name': 'authtest.mod',
                     'asroot:perms': (
                        ('authtest', 'perm'),
                     ),
                     'storm': 'function func() { [ ps:person=* ] return($node) }',
                    },
                    {
                     'name': 'authtest.mod2',
                     'asroot:perms': (
                        ('authtest', 'perm2'),
                     ),
                     'storm': 'function func() { [ ps:person=* ] return($node) }',
                    },
                ),
                'commands': (
                    {'name': 'authtest.cmd',
                    #  'asroot': True,
                     'perms': [
                        ('authtest', 'perm')
                     ],
                     'storm': '$lib.print(woot)',
                    },
                    {'name': 'authtest.cmd2',
                     'perms': [
                         ('authtest', 'perm2')
                     ],
                    #  'asroot': True,
                     'storm': '$lib.print(woot2)',
                    },
                ),
            }

            await core.stormlist('auth.user.add user')
            await core.stormlist('auth.user.add user2')

            await core.addStormPkg(stormpkg)

            msgs = await core.stormlist('pkg.perms.list authtest')
            self.stormIsInPrint('Package (authtest) defines the following permissions:', msgs)
            self.stormIsInPrint('authtest.perm                    : Default deny ( default: false )', msgs)
            self.stormIsInPrint('authtest.perm2                   : Default allow ( default: true )', msgs)

            user = await core.auth.getUserByName('user')
            asuser = {'user': user.iden}

            user2 = await core.auth.getUserByName('user2')
            asuser2 = {'user': user2.iden}

            await core.stormlist('auth.user.addrule user authtest.perm')
            await core.stormlist('auth.user.addrule user2 "!authtest.perm2"')

            # At this point, user should be able to access everything and user2
            # should not be able to access anything

            msgs = await core.stormlist('authtest.cmd', opts=asuser)
            self.stormIsInPrint('woot', msgs)

            msgs = await core.stormlist('authtest.cmd2', opts=asuser)
            self.stormIsInPrint('woot2', msgs)

            with self.raises(s_exc.AuthDeny) as exc:
                await core.callStorm('authtest.cmd', opts=asuser2)
            self.eq('Command (authtest.cmd) requires permission: authtest.perm', exc.exception.get('mesg'))

            with self.raises(s_exc.AuthDeny) as exc:
                await core.callStorm('authtest.cmd2', opts=asuser2)
            self.eq('Command (authtest.cmd2) requires permission: authtest.perm2', exc.exception.get('mesg'))

            self.len(1, await core.nodes('yield $lib.import(authtest.mod).func()', opts=asuser))
            self.len(1, await core.nodes('yield $lib.import(authtest.mod2).func()', opts=asuser))

            with self.raises(s_exc.AuthDeny):
                await core.nodes('yield $lib.import(authtest.mod).func()', opts=asuser2)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('yield $lib.import(authtest.mod2).func()', opts=asuser2)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm(
                    'for $item in $lib.auth.users.byname(root).json.iter() { $lib.print($item) }',
                    opts=asuser
                )

    async def test_stormlib_auth_userjson(self):

        async with self.getTestCore() as core:
            self.none(await core.callStorm('return($lib.user.json.get(foo))'))
            self.none(await core.callStorm('return($lib.user.json.get(foo, prop=bar))'))
            self.true(await core.callStorm('return($lib.user.json.set(hi, ({"foo": "bar", "baz": "faz"})))'))
            self.true(await core.callStorm('return($lib.user.json.set(bye/bye, ({"zip": "zop", "bip": "bop"})))'))
            self.eq('bar', await core.callStorm('return($lib.user.json.get(hi, prop=foo))'))
            self.eq({'foo': 'bar', 'baz': 'faz'}, await core.callStorm('return($lib.user.json.get(hi))'))

            await core.callStorm('$lib.user.json.set(hi, hehe, prop=foo)')
            items = await core.callStorm('''
            $list = ()
            for $item in $lib.user.json.iter() { $list.append($item) }
            return($list)
            ''')
            self.eq(items, (
                (('bye', 'bye'), {'zip': 'zop', 'bip': 'bop'}),
                (('hi',), {'baz': 'faz', 'foo': 'hehe'}),
            ))

            items = await core.callStorm('''
            $list = ()
            for $item in $lib.user.json.iter(path=bye) { $list.append($item) }
            return($list)
            ''')
            self.eq(items, (
                (('bye',), {'zip': 'zop', 'bip': 'bop'}),
            ))

            self.eq('zop', await core.callStorm('return($lib.auth.users.byname(root).json.get(bye/bye, prop=zip))'))

            visi = await core.auth.addUser('visi')

            asvisi = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.auth.users.byname(root).json.get(bye/bye, prop=zip))', opts=asvisi)

            self.none(await core.callStorm('return($lib.user.json.get(hi))', opts=asvisi))
            await core.callStorm('if (not $lib.user.json.has(hehe)) { $lib.user.json.set(hehe, ({})) }', opts=asvisi)

            self.true(await core.callStorm('return($lib.user.json.set(hehe, haha, prop=foo))', opts=asvisi))
            self.true(await core.callStorm('return($lib.user.json.set(hehe, haha, prop=foo))', opts=asvisi))
            self.eq('haha', await core.callStorm('return($lib.user.json.get(hehe, prop=foo))', opts=asvisi))

            self.eq('haha', await core.callStorm('return($lib.auth.users.byname(visi).json.get(hehe, prop=foo))'))
            self.true(await core.callStorm('return($lib.auth.users.byname(visi).json.set(hehe, lolz, prop=foo))'))
            self.eq('lolz', await core.callStorm('return($lib.auth.users.byname(visi).json.get(hehe, prop=foo))'))
            self.true(await core.callStorm('return($lib.auth.users.byname(visi).json.del(hehe, prop=foo))'))
            self.none(await core.callStorm('return($lib.auth.users.byname(visi).json.get(hehe, prop=foo))'))
            self.true(await core.callStorm('return($lib.auth.users.byname(visi).json.del(hehe))'))
            self.none(await core.callStorm('return($lib.auth.users.byname(visi).json.get(hehe))'))
            self.false(await core.callStorm('return($lib.auth.users.byname(visi).json.has(hehe))'))

    async def test_stormlib_auth_uservars(self):

        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            othr = await core.auth.addUser('othr')
            asothr = {'user': othr.iden}

            await core.callStorm('$lib.user.vars.set(foo, foovalu)', opts=asvisi)

            msgs = await core.stormlist('for $valu in $lib.user.vars { $lib.print($valu) }', opts=asvisi)
            self.stormIsInPrint("('foo', 'foovalu')", msgs)

            q = 'return($lib.auth.users.byname(visi).vars.foo)'
            self.eq('foovalu', await core.callStorm(q, opts=asvisi))

            await self.asyncraises(s_exc.AuthDeny, core.callStorm(q, opts=asothr))

            await core.callStorm('$lib.auth.users.byname(visi).vars.foo=barvalu')

            q = 'for $valu in $lib.auth.users.byname(visi).vars { $lib.print($valu) }'
            msgs = await core.stormlist(q)
            self.stormIsInPrint("('foo', 'barvalu')", msgs)

            await core.callStorm('$lib.auth.users.byname(visi).vars.foo=$lib.undef')
            self.none(await core.callStorm('return($lib.auth.users.byname(visi).vars.foo)'))

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$lib.user.vars.set((1), newp)')

            await core.callStorm('$lib.user.profile.set(bar, foovalu)', opts=asvisi)

            self.eq('foovalu', await core.callStorm('return($lib.user.profile.get(bar))', opts=asvisi))

            self.eq((('bar', 'foovalu'),), await core.callStorm('return($lib.user.profile.list())', opts=asvisi))

            msgs = await core.stormlist('for $valu in $lib.user.profile { $lib.print($valu) }', opts=asvisi)
            self.stormIsInPrint("('bar', 'foovalu')", msgs)

            await core.callStorm('$lib.user.profile.pop(bar)', opts=asvisi)
            self.none(await core.callStorm('return($lib.user.profile.get(bar))', opts=asvisi))

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$lib.user.profile.set((1), newp)')

    async def test_stormlib_auth_base(self):

        async with self.getTestCore() as core:

            async with core.getLocalProxy() as proxy:
                self.ge(len(await proxy.getPermDefs()), 10)

            stormpkg = {
                'name': 'authtest',
                'version': '0.0.1',
                'perms': (
                    {'perm': ('wootwoot',), 'desc': 'lol lol', 'gate': 'cortex'},
                    {'perm': ('wootwoot.wow',), 'desc': 'a new permission', 'gate': 'cortex', 'default': True},
                ),
                'modules': (
                    {
                     'name': 'authtest.privsep',
                     'asroot:perms': (
                        ('wootwoot',),
                     ),
                     'storm': 'function x() { [ ps:person=* ] return($node) }',
                    },
                ),
                'commands': (
                    {'name': 'authtest.asuser',
                     'perms': (('wootwoot',), ),
                     'storm': '$lib.print(hithere)',
                    },
                ),
            }

            msgs = await core.stormlist('pkg.perms.list asdfjahsdlfkj')
            self.stormIsInWarn('Package (asdfjahsdlfkj) not found!', msgs)

            msgs = await core.stormlist('auth.user.add visi')
            self.stormIsInPrint('User (visi) added with iden: ', msgs)

            msgs = await core.stormlist('auth.role.add ninjas')
            self.stormIsInPrint('Role (ninjas) added with iden: ', msgs)

            with self.raises(s_exc.DupUserName):
                await core.nodes('auth.user.add visi')

            with self.raises(s_exc.DupRoleName):
                await core.nodes('auth.role.add ninjas')

            await core.addStormPkg(stormpkg)

            msgs = await core.stormlist('pkg.perms.list authtest')
            self.stormIsInPrint('Package (authtest) defines the following permissions:', msgs)
            self.stormIsInPrint('wootwoot                         : lol lol ( default: false )', msgs)
            self.stormIsInPrint('wootwoot.wow                     : a new permission ( default: true )', msgs)

            async with core.getLocalProxy() as proxy:
                for permdef in stormpkg.get('perms'):
                    pdef = await proxy.getPermDef(permdef.get('perm'))
                    self.eq(permdef.get('perm'), pdef.get('perm'))
                    self.eq(permdef.get('desc'), pdef.get('desc'))
                    self.eq(permdef.get('gate'), pdef.get('gate'))
                    self.eq(permdef.get('default'), pdef.get('default'))

            visi = await core.auth.getUserByName('visi')
            asvisi = {'user': visi.iden}

            with self.raises(s_exc.AuthDeny):
                await core.nodes('authtest.asuser', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.import(authtest.privsep)', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('[ ps:person=* ]', opts=asvisi)

            msgs = await core.stormlist('auth.user.addrule hehe haha')
            self.stormIsInWarn('User (hehe) not found!', msgs)

            msgs = await core.stormlist('auth.role.addrule hehe haha')
            self.stormIsInWarn('Role (hehe) not found!', msgs)

            msgs = await core.stormlist('auth.user.addrule visi wootwoot')
            self.stormIsInPrint('Added rule wootwoot to user visi.', msgs)
            msgs = await core.stormlist('auth.role.addrule ninjas wootwoot')
            self.stormIsInPrint('Added rule wootwoot to role ninjas.', msgs)

            msgs = await core.stormlist('authtest.asuser', opts=asvisi)
            self.stormIsInPrint('hithere', msgs)

            self.len(1, await core.nodes('yield $lib.import(authtest.privsep).x()', opts=asvisi))

            udef = await core.callStorm('return($lib.auth.users.get($iden))', opts={'vars': {'iden': visi.iden}})
            self.nn(udef)
            self.nn(await core.callStorm('return($lib.auth.users.byname(visi))'))
            pdef = await core.callStorm('$info=$lib.auth.users.byname(visi).pack() $info.key=valu return($info)')
            self.eq('valu', pdef.pop('key', None))
            self.eq(udef, pdef)

            self.eq(await core.callStorm('return($lib.auth.roles.byname(all).name)'), 'all')
            rdef = await core.callStorm('return($lib.auth.roles.byname(all))')
            self.eq(rdef.get('name'), 'all')
            pdef = await core.callStorm('$info=$lib.auth.roles.byname(all).pack() $info.key=valu return($info)')
            self.eq('valu', pdef.pop('key', None))
            self.eq(rdef, pdef)

            self.none(await core.callStorm('return($lib.auth.users.get($iden))', opts={'vars': {'iden': 'newp'}}))
            self.none(await core.callStorm('return($lib.auth.roles.get($iden))', opts={'vars': {'iden': 'newp'}}))
            self.none(await core.callStorm('return($lib.auth.users.byname(newp))'))
            self.none(await core.callStorm('return($lib.auth.roles.byname(newp))'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$user = $lib.auth.users.byname(visi) $lib.auth.users.del($user.iden)',
                                     opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$user = $lib.auth.users.add(newp)', opts=asvisi)

            udef = await core.callStorm('return($lib.auth.users.add(hehe, passwd=haha, email=visi@vertex.link))')

            self.eq('hehe', udef['name'])
            self.eq(False, udef['locked'])
            self.eq('visi@vertex.link', udef['email'])

            hehe = await core.callStorm('''
                $hehe = $lib.auth.users.byname(hehe)
                $hehe.setLocked($lib.true)
                return($hehe)
            ''')
            self.eq(True, hehe['locked'])

            self.none(await core.tryUserPasswd('hehe', 'haha'))

            await core.callStorm('$lib.auth.users.byname(hehe).setLocked($lib.false)')

            self.nn(await core.tryUserPasswd('hehe', 'haha'))

            hehe = await core.callStorm('''
                            $hehe = $lib.auth.users.byname(hehe)
                            $hehe.setArchived($lib.true)
                            return($hehe)
                        ''')
            self.eq(True, hehe['archived'])
            self.eq(True, hehe['locked'])

            self.none(await core.tryUserPasswd('hehe', 'haha'))

            hehe = await core.callStorm('''
                            $hehe = $lib.auth.users.byname(hehe)
                            $hehe.setArchived($lib.false)
                            return($hehe)
                        ''')
            self.eq(True, hehe['locked'])
            self.eq(False, hehe['archived'])
            self.none(await core.tryUserPasswd('hehe', 'haha'))

            await core.callStorm('$lib.auth.users.byname(hehe).setLocked($lib.false)')
            self.nn(await core.tryUserPasswd('hehe', 'haha'))

            self.nn(await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                if $( $visi.name = "visi" ) {
                    for $role in $visi.roles() {
                        if $("all" = $role.name) {
                            return($role)
                        }
                    }
                }
            '''))

            self.eq((True, ('foo', 'bar')), await core.callStorm('return($lib.auth.ruleFromText(foo.bar))'))
            self.eq((False, ('foo', 'bar')), await core.callStorm('return($lib.auth.ruleFromText("!foo.bar"))'))
            self.eq('foo.bar', await core.callStorm('return($lib.auth.textFromRule(($lib.true, (foo, bar))))'))
            self.eq('!foo.bar', await core.callStorm('return($lib.auth.textFromRule(($lib.false, (foo, bar))))'))

            rdef = await core.callStorm('return($lib.auth.roles.add(admins))')
            opts = {'vars': {'roleiden': rdef.get('iden')}}

            self.nn(rdef['iden'])
            self.eq('admins', rdef['name'])

            await core.callStorm('''
                $role = $lib.auth.roles.byname(admins)
                $role.addRule($lib.auth.ruleFromText(foo.bar))
            ''')

            await core.callStorm('$lib.auth.users.byname(visi).setPasswd(haha)')

            await core.callStorm('''
                $lib.auth.users.byname(visi).setPasswd(hehe)
            ''', opts=asvisi)

            self.false(await core.callStorm('''
                return($lib.auth.users.byname(visi).allowed(foo.bar))
            '''))

            self.true(await core.callStorm('''
                return($lib.auth.users.byname(visi).allowed(foo.bar, default=$lib.true))
            '''))

            await core.callStorm('''
                $role = $lib.auth.roles.byname(admins)
                $lib.auth.users.byname(visi).grant($role.iden)
            ''', opts=opts)

            self.true(await core.callStorm('''
                return($lib.auth.users.byname(visi).allowed(foo.bar))
            '''))

            await core.callStorm('''
                $role = $lib.auth.roles.byname(admins)
                $lib.auth.users.byname(visi).revoke($role.iden)
            ''')

            self.false(await core.callStorm('''
                return($lib.auth.users.byname(visi).allowed(foo.bar))
            '''))

            # user roles can be set in bulk
            roles = await core.callStorm('''$roles=()
            $role=$lib.auth.roles.byname(admins) $roles.append($role.iden)
            $role=$lib.auth.roles.byname(all) $roles.append($role.iden)
            $lib.auth.users.byname(visi).setRoles($roles)
            return ($lib.auth.users.byname(visi).roles())
            ''')
            self.len(2, roles)
            self.eq(roles[0].get('name'), 'admins')
            self.eq(roles[1].get('name'), 'all')

            q = 'for $user in $lib.auth.users.list() { if $($user.get(email) = "visi@vertex.link") { return($user) } }'
            self.nn(await core.callStorm(q))
            q = 'for $role in $lib.auth.roles.list() { if $( $role.name = "all") { return($role) } }'
            self.nn(await core.callStorm(q))
            self.nn(await core.callStorm('return($lib.auth.roles.byname(all))'))

            self.nn(await core.callStorm(f'return($lib.auth.roles.get({core.auth.allrole.iden}))'))
            self.nn(await core.callStorm(f'return($lib.auth.users.get({core.auth.rootuser.iden}))'))
            self.len(3, await core.callStorm(f'return($lib.auth.users.list())'))

            msgs = await core.stormlist(f'$lib.print($lib.auth.roles.get({core.auth.allrole.iden}))')
            self.stormIsInPrint('auth:role', msgs)

            visi = await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                $visi.setEmail(hehe@haha.com)
                return($visi)
            ''')

            self.eq('hehe@haha.com', visi['email'])

            visi = await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                $visi.setEmail(giggles@clowntown.net)
                return($visi)
            ''', asvisi)

            self.eq('giggles@clowntown.net', visi['email'])

            # test user rules APIs

            visi = await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                $visi.setRules(())
                return($visi)
            ''')

            self.eq((), visi['rules'])

            visi = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(hehe.haha)
                $visi = $lib.auth.users.byname(visi)
                $visi.setRules(($rule,))
                return($visi)
            ''')
            self.eq(((True, ('hehe', 'haha')),), visi['rules'])

            visi = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(hehe.haha)
                $visi = $lib.auth.users.byname(visi)
                $visi.setRules(([$rule]))
                return($visi)
            ''')
            self.eq(((True, ('hehe', 'haha')),), visi['rules'])

            visi = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(foo.bar)
                $visi = $lib.auth.users.byname(visi)
                $visi.addRule($rule)
                return($visi)
            ''')
            self.eq(((True, ('hehe', 'haha')), (True, ('foo', 'bar'))), visi['rules'])

            visi = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(foo.bar)
                $visi = $lib.auth.users.byname(visi)
                $visi.delRule($rule)
                return($visi)
            ''')
            self.eq(((True, ('hehe', 'haha')),), visi['rules'])

            self.nn(await core.callStorm('return($lib.auth.roles.byname(all).get(rules))'))

            # test role rules APIs
            ninjas = await core.callStorm('''
                $ninjas = $lib.auth.roles.byname(ninjas)
                $ninjas.setRules(())
                return($ninjas)
            ''')

            self.eq((), ninjas['rules'])

            ninjas = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(hehe.haha)
                $ninjas = $lib.auth.roles.byname(ninjas)
                $ninjas.setRules(($rule,))
                return($ninjas)
            ''')
            self.eq(((True, ('hehe', 'haha')),), ninjas['rules'])

            ninjas = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(hehe.haha)
                $ninjas = $lib.auth.roles.byname(ninjas)
                $ninjas.setRules(([$rule]))
                return($ninjas)
            ''')
            self.eq(((True, ('hehe', 'haha')),), ninjas['rules'])

            ninjas = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(foo.bar)
                $ninjas = $lib.auth.roles.byname(ninjas)
                $ninjas.addRule($rule)
                return($ninjas)
            ''')
            self.eq(((True, ('hehe', 'haha')), (True, ('foo', 'bar'))), ninjas['rules'])

            ninjas = await core.callStorm('''
                $rule = $lib.auth.ruleFromText(foo.bar)
                $ninjas = $lib.auth.roles.byname(ninjas)
                $ninjas.delRule($rule)
                return($ninjas)
            ''')
            self.eq(((True, ('hehe', 'haha')),), ninjas['rules'])

            # test admin API
            self.false(await core.callStorm('''
                return($lib.auth.users.byname(visi).get(admin))
            '''))

            self.true(await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                $visi.setAdmin(true)
                return($visi)
            '''))

            # test deleting users / roles
            await core.callStorm('''
                $visi = $lib.auth.users.byname(visi)
                $lib.auth.users.del($visi.iden)
            ''')
            self.none(await core.auth.getUserByName('visi'))

            await core.callStorm('''
                $role = $lib.auth.roles.byname(ninjas)
                $lib.auth.roles.del($role.iden)
            ''')
            self.none(await core.auth.getRoleByName('ninjas'))

            # Use arbitrary idens when creating users.
            iden = s_common.guid(('foo', 101))
            udef = await core.callStorm('$u=$lib.auth.users.add(foo, iden=$iden) return ( $u )',
                                        opts={'vars': {'iden': iden}})
            self.eq(udef.get('iden'), iden)

            with self.raises(s_exc.DupIden):
                await core.callStorm('$u=$lib.auth.users.add(bar, iden=$iden) return ( $u )',
                                     opts={'vars': {'iden': iden}})
            with self.raises(s_exc.BadArg):
                iden = 'beep'
                await core.callStorm('$u=$lib.auth.users.add(bar, iden=$iden) return ( $u )',
                                     opts={'vars': {'iden': iden}})

            with self.raises(s_exc.BadArg):
                iden = 12345
                await core.callStorm('$u=$lib.auth.users.add(bar, iden=$iden) return ( $u )',
                                     opts={'vars': {'iden': iden}})

            # test out renaming a user
            iden = await core.callStorm('return($lib.auth.users.add(new0).iden)')
            await core.callStorm('$lib.auth.users.byname(new0).name = new1', opts={'user': iden})
            self.none(await core.callStorm('return($lib.auth.users.byname(new0))'))
            self.nn(await core.callStorm('return($lib.auth.users.byname(new1))'))

            await core.callStorm('$lib.auth.users.byname(new1).name = new2')
            self.none(await core.callStorm('return($lib.auth.users.byname(new1))'))
            self.nn(await core.callStorm('return($lib.auth.users.byname(new2))'))
            await core.callStorm('$lib.auth.users.byname(new2).email = "visi@vertex.link"')
            self.eq('visi@vertex.link', await core.callStorm('return($lib.auth.users.byname(new2).email)'))

            # test renaming a role
            await core.callStorm('$lib.auth.roles.add(new0)')
            await core.callStorm('$lib.auth.roles.byname(new0).name = new1')
            self.none(await core.callStorm('return($lib.auth.roles.byname(new0))'))
            self.nn(await core.callStorm('return($lib.auth.roles.byname(new1))'))

            # Objects are dynamic
            q = """
            $user = $lib.auth.users.add(bar)
            $lib.print("old name={u}", u= $user.name)
            $user.name=sally
            $lib.print("new name={u}", u=$user.name)"""
            msgs = await core.stormlist(q)

            self.stormIsInPrint('old name=bar', msgs)
            self.stormIsInPrint('new name=sally', msgs)

            # User profile data is exposed
            await core.callStorm('$lib.auth.users.add(puser)')
            q = '$u=$lib.auth.users.byname(puser) $u.profile.hehe=haha return ($u.profile)'
            self.eq({'hehe': 'haha'}, await core.callStorm(q))
            q = '$u=$lib.auth.users.byname(puser) $r=$u.profile.hehe return ($r)'
            self.eq('haha', await core.callStorm(q))
            q = '$u=$lib.auth.users.byname(puser) $r=$u.profile.newp return ($r)'
            self.none(await core.callStorm(q))
            q = '$u=$lib.auth.users.byname(puser) $u.profile.hehe=$lib.undef return ($u.profile)'
            self.eq({}, await core.callStorm(q))

            # Mutability of the values we deref doesn't affect future derefs.
            q = '''$u=$lib.auth.users.byname(puser) $profile=$u.profile
            $d=({'foo': 'bar'})
            $profile.hehe=haha $profile.d=$d
            $p1 = $lib.json.save($profile)
            // Retrieve the dictionary, modify it, and then serialize it again.
            $d2=$profile.d $d2.wow=giggle
            $p2 = $lib.json.save($profile)
            return ( ($p1, $p2) )
            '''
            retn = await core.callStorm(q)
            self.eq(retn[0], retn[1])
            self.eq(s_json.loads(retn[0]), {'hehe': 'haha', 'd': {'foo': 'bar'}})

            q = '''$u=$lib.auth.users.byname(puser) $profile=$u.profile
            for $valu in $profile {
                $lib.print($valu)
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("('hehe', 'haha')", msgs)
            self.stormIsInPrint("('d', {'foo': 'bar'})", msgs)

            # lowuser can perform auth auctions with the correct permissions
            lowuser = await core.addUser('lowuser')
            aslowuser = {'user': lowuser.get('iden')}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.auth.users.add(hehe) )', opts=aslowuser)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.auth.users.del(puser) )', opts=aslowuser)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.auth.roles.add(yes) )', opts=aslowuser)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.auth.roles.del(ninjas) )', opts=aslowuser)

            await core.addUserRule(lowuser.get('iden'), (True, ('storm', 'lib', 'auth', 'users', 'add')))
            await core.addUserRule(lowuser.get('iden'), (True, ('storm', 'lib', 'auth', 'users', 'del')))
            await core.addUserRule(lowuser.get('iden'), (True, ('storm', 'lib', 'auth', 'roles', 'add')))
            await core.addUserRule(lowuser.get('iden'), (True, ('storm', 'lib', 'auth', 'roles', 'del')))
            unfo = await core.callStorm('return ( $lib.auth.users.add(giggles) )', opts=aslowuser)
            iden = unfo.get('iden')
            msgs = await core.stormlist(f'$lib.auth.users.del({iden})', opts=aslowuser)
            self.stormHasNoWarnErr(msgs)

            rnfo = await core.callStorm('return ( $lib.auth.roles.add(giggles) )', opts=aslowuser)
            iden = rnfo.get('iden')
            msgs = await core.stormlist(f'$lib.auth.roles.del({iden})', opts=aslowuser)
            self.stormHasNoWarnErr(msgs)

            # Use arbitrary idens when creating roles.
            iden = '9e0998f68b662ed3776b6ce33a2d21eb'
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.auth.roles.add(runners, iden=12345)')
            opts = {'vars': {'iden': iden}}
            rdef = await core.callStorm('$r=$lib.auth.roles.add(runners, iden=$iden) return ( $r )',
                            opts=opts)
            self.eq(rdef.get('iden'), iden)
            ret = await core.callStorm('return($lib.auth.roles.get($iden))', opts=opts)
            self.eq(ret, rdef)
            with self.raises(s_exc.DupRoleName):
                await core.callStorm('$lib.auth.roles.add(runners, iden=$iden)', opts=opts)
            with self.raises(s_exc.DupIden):
                await core.callStorm('$lib.auth.roles.add(walkers, iden=$iden)', opts=opts)

            # The role & user.authgates local is a passthrough to the getRoleDef & getUserDef
            # results, which are a pack()'d structure. Modifying the results of that structure
            # does not persist.
            q = '$u = $lib.auth.users.byname(root) $u.authgates.newp = ({}) return ($u)'
            udef = await core.callStorm(q)
            self.notin('newp', udef.get('authgates'))
            q = '$u = $lib.auth.users.byname(root) return ( $lib.dict.has($u.authgates, newp) )'
            self.false(await core.callStorm(q))

            q = '$r = $lib.auth.roles.byname(all) $r.authgates.newp = ({}) return ($r)'
            rdef = await core.callStorm(q)
            self.notin('newp', rdef.get('authgates'))
            q = '$r = $lib.auth.roles.byname(all) return ( $lib.dict.has($r.authgates, newp) )'
            self.false(await core.callStorm(q))

    async def test_stormlib_auth_gateadmin(self):

        async with self.getTestCore() as core:
            uowner = await core.auth.addUser('uowner')
            await uowner.addRule((True, ('node', 'add',)))
            await uowner.addRule((True, ('layer', 'add',)))
            await uowner.addRule((True, ('view', 'add',)))

            await core.auth.addRole('ninjas')
            ureader = await core.auth.addUser('ureader')
            uwriter = await core.auth.addUser('uwriter')

            viewiden = await core.callStorm('''
                $layr = $lib.layer.add().iden
                $view = $lib.view.add(($layr,))
                return($view.iden)
            ''', opts={'user': uowner.iden})

            opts = {
                'view': viewiden,
                'user': uowner.iden,
                'vars': {
                    'ureader': ureader.iden,
                    'uwriter': uwriter.iden,
                },
            }

            self.len(1, await core.nodes('[ test:str=foo ]', opts=opts))

            opts['user'] = ureader.iden
            await self.asyncraises(s_exc.AuthDeny, core.nodes('test:str', opts=opts))

            opts['user'] = uwriter.iden
            await self.asyncraises(s_exc.AuthDeny, core.nodes('test:str', opts=opts))

            # add a read user
            opts['user'] = uowner.iden
            scmd = '''
                $viewiden = $lib.view.get().iden
                $layriden = $lib.layer.get().iden
                $usr = $lib.auth.users.get($ureader)

                $rule = $lib.auth.ruleFromText(view.read)
                $usr.addRule($rule, $viewiden)

                $rule = $lib.auth.ruleFromText(layer.read)
                $usr.addRule($rule, $layriden)

                return(($lib.auth.gates.get($viewiden), $lib.auth.gates.get($layriden)))
            '''

            opts['view'] = None
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            opts['view'] = viewiden
            viewgate, layrgate = await core.callStorm(scmd, opts=opts)
            self.len(2, viewgate['users'])
            self.len(2, layrgate['users'])

            opts['user'] = ureader.iden
            self.len(1, await core.nodes('test:str', opts=opts))
            await self.asyncraises(s_exc.AuthDeny, core.nodes('[ test:str=bar ]', opts=opts))

            # add a user as admin
            opts['user'] = uowner.iden
            scmd = '''
                $viewiden = $lib.view.get().iden
                $layriden = $lib.layer.get().iden
                $usr = $lib.auth.users.get($uwriter)

                $usr.setAdmin($lib.true, $viewiden)
                $usr.setAdmin($lib.true, $layriden)

                return(($lib.auth.gates.get($viewiden), $lib.auth.gates.get($layriden)))
            '''

            opts['view'] = None
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            opts['view'] = viewiden
            viewgate, layrgate = await core.callStorm(scmd, opts=opts)
            self.len(3, viewgate['users'])
            self.len(3, layrgate['users'])

            opts['user'] = uwriter.iden
            self.len(1, await core.nodes('[ test:str=bar ]', opts=opts))

            # set rule
            opts['user'] = uowner.iden
            scmd = '''
                $viewiden = $lib.view.get().iden
                $layriden = $lib.layer.get().iden
                $usr = $lib.auth.users.get($ureader)
                $role = $lib.auth.roles.byname(ninjas)

                $rule0 = $lib.auth.ruleFromText(view.read)
                $rule1 = $lib.auth.ruleFromText(node.add)
                $usr.setRules(($rule0, $rule1), $viewiden)
                $role.setRules(($rule0, $rule1), $viewiden)

                $rule0 = $lib.auth.ruleFromText(layr.read)
                $rule1 = $lib.auth.ruleFromText(node.add)
                $usr.setRules(($rule0, $rule1), $layriden)
                $role.setRules(($rule0, $rule1), $layriden)

                return(($lib.auth.gates.get($viewiden), $lib.auth.gates.get($layriden)))
            '''

            opts['view'] = None
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            opts['view'] = viewiden
            await core.callStorm(scmd, opts=opts)

            opts['user'] = ureader.iden
            self.len(1, await core.nodes('[ test:str=bam ]', opts=opts))

            # del rule
            opts['user'] = uowner.iden
            scmd = '''
                $viewiden = $lib.view.get().iden
                $layriden = $lib.layer.get().iden
                $usr = $lib.auth.users.get($ureader)
                $role = $lib.auth.roles.byname(ninjas)

                $rule = $lib.auth.ruleFromText(node.add)
                $usr.delRule($rule, $viewiden)
                $role.delRule($rule, $viewiden)

                $rule = $lib.auth.ruleFromText(node.add)
                $usr.delRule($rule, $layriden)
                $role.delRule($rule, $layriden)

                return(($lib.auth.gates.get($viewiden), $lib.auth.gates.get($layriden)))
            '''

            opts['view'] = None
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            opts['view'] = viewiden
            await core.callStorm(scmd, opts=opts)

            opts['user'] = ureader.iden
            await self.asyncraises(s_exc.AuthDeny, core.nodes('[ test:str=baz ]', opts=opts))
            self.len(3, await core.nodes('test:str', opts=opts))

    async def test_stormlib_auth_gates(self):

        async with self.getTestCore() as core:
            viewiden = await core.callStorm('return($lib.view.get().iden)')
            gate = await core.callStorm('return($lib.auth.gates.get($lib.view.get().iden))')
            self.eq('view', await core.callStorm('return($lib.auth.gates.get($lib.view.get().iden).type)'))

            self.eq(gate.get('iden'), viewiden)
            # default view should only have root user as admin and all as read
            self.eq(gate['users'][0], {
                'iden': core.auth.rootuser.iden,
                'admin': True,
                'rules': (),
            })

            self.eq(gate['roles'][0], {
                'iden': core.auth.allrole.iden,
                'admin': False,
                'rules': (
                    (True, ('view', 'read')),
                ),
            })

            gates = await core.callStorm('return($lib.auth.gates.list())')
            self.isin(viewiden, [g['iden'] for g in gates])

    async def test_stormlib_auth_apikey(self):

        async with self.getTestCore() as core:

            await core.auth.rootuser.setPasswd('root')
            root = core.auth.rootuser.iden

            lowuser = await core.addUser('lowuser')
            lowuser = lowuser.get('iden')

            hhost, hport = await core.addHttpsPort(0, host='127.0.0.1')

            ltk0, ltdf0 = await core.addUserApiKey(lowuser, 'test')

            q = '$u=$lib.auth.users.byname(root) return($u.genApiKey("Test Key"))'
            rtk0, rtdf0 = await core.callStorm(q)
            q = '$u=$lib.auth.users.byname(root) return($u.genApiKey("Backup Key"))'
            bkk0, bkdf0 = await core.callStorm(q)

            self.notin('shadow', rtdf0)
            self.eq(rtdf0.get('name'), 'Test Key')
            self.eq(rtdf0.get('user'), root)
            self.nn(rtdf0.get('iden'))
            self.gt(rtdf0.get('updated'), 0)
            self.none(rtdf0.get('expires'))

            q = '$u=$lib.auth.users.byname(root) return($u.listApiKeys())'
            rootkeys = await core.callStorm(q)
            self.len(2, rootkeys)
            _kdefs = [rtdf0, bkdf0]
            for kdef in rootkeys:
                self.isin(kdef, _kdefs)
                _kdefs.remove(kdef)
            self.len(0, _kdefs)

            opts = {'vars': {'iden': rtdf0.get('iden')}}
            q = '$u=$lib.auth.users.byname(root) return( $u.getApiKey($iden) )'
            _rtdf0 = await core.callStorm(q, opts=opts)
            self.eq(rtdf0, _rtdf0)

            q = '$u=$lib.auth.users.byname(root) return( $u.modApiKey($iden, name, "heheKey!") )'
            _rtdf0 = await core.callStorm(q, opts=opts)
            self.eq(_rtdf0.get('name'), 'heheKey!')
            self.eq(_rtdf0.get('iden'), rtdf0.get('iden'))
            self.gt(_rtdf0.get('updated'), rtdf0.get('updated'))

            q = '$u=$lib.auth.users.byname(root) return($u.delApiKey($iden))'
            self.true(await core.callStorm(q, opts=opts))

            q = '$u=$lib.auth.users.byname(root) return($u.listApiKeys())'
            rootkeys = await core.callStorm(q)
            self.eq(rootkeys, (bkdf0,))

            # Root can get API keys for other users
            q = '$u=$lib.auth.users.byname(lowuser) return($u.listApiKeys())'
            lowkeys = await core.callStorm(q)
            self.len(1, lowkeys)
            self.eq(lowkeys, (ltdf0,))
            q = '$u=$lib.auth.users.byname(lowuser) return($u.getApiKey($iden))'
            _ltdf0 = await core.callStorm(q, opts={'vars': {'iden': ltdf0.get('iden')}})
            self.eq(_ltdf0, ltdf0)

            # Perms tests - lowuser is denied from managing their API keys
            lowuser_opts = {'user': lowuser, 'vars': {'iden': ltdf0.get('iden')}}
            await core.addUserRule(lowuser, (False, ('auth', 'self', 'set', 'apikey')))
            q = 'return($lib.auth.users.byname(lowuser).genApiKey(newp))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            q = 'return($lib.auth.users.byname(lowuser).getApiKey($iden))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            q = 'return($lib.auth.users.byname(lowuser).listApiKeys())'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            q = 'return($lib.auth.users.byname(lowuser).modApiKey($iden, name, wow))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            q = 'return($lib.auth.users.byname(lowuser).delApiKey($iden))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            # Not allowed to manage others API keys by default
            q = 'return($lib.auth.users.byname(root).genApiKey(newp))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=lowuser_opts)

            # Remove the deny permission
            await core.delUserRule(lowuser, (False, ('auth', 'self', 'set', 'apikey')))
            ntk0, ntdf0 = await core.callStorm('return($lib.auth.users.byname(lowuser).genApiKey(weee, duration=10))',
                                               opts=lowuser_opts)
            self.nn(ntk0)
            self.eq(ntdf0.get('name'), 'weee')
            self.eq(ntdf0.get('expires'), ntdf0.get('updated') + 10)  # really short but...example...
            self.eq(ntdf0.get('created'), ntdf0.get('updated'))

            q = 'return($lib.auth.users.byname(lowuser).getApiKey($iden))'
            _ltdf0 = await core.callStorm(q, opts=lowuser_opts)
            self.eq(_ltdf0, ltdf0)

            q = '$u=$lib.auth.users.byname(lowuser) return($u.listApiKeys())'
            lowkeys = await core.callStorm(q, opts=lowuser_opts)
            self.len(2, lowkeys)
            _kdefs = [ltdf0, ntdf0]
            for kdef in lowkeys:
                self.isin(kdef, _kdefs)
                _kdefs.remove(kdef)
            self.len(0, _kdefs)

            await asyncio.sleep(0.001)
            q = 'return($lib.auth.users.byname(lowuser).modApiKey($iden, name, ohmy))'
            lowuser_opts = {'user': lowuser, 'vars': {'iden': ntdf0.get('iden')}}
            _ntdf0 = await core.callStorm(q, opts=lowuser_opts)
            self.eq(_ntdf0.get('iden'), ntdf0.get('iden'))
            self.gt(_ntdf0.get('updated'), ntdf0.get('updated'))
            self.eq(_ntdf0.get('expires'), ntdf0.get('expires'))
            self.eq(_ntdf0.get('name'), 'ohmy')

            q = 'return($lib.auth.users.byname(lowuser).delApiKey($iden))'
            self.true(await core.callStorm(q, opts=lowuser_opts))

            q = '$u=$lib.auth.users.byname(lowuser) return($u.listApiKeys())'
            lowkeys = await core.callStorm(q, opts=lowuser_opts)
            self.len(1, lowkeys)
            self.eq(lowkeys, (ltdf0,))

            # Perm allows lowuser to manage others API keys
            await core.addUserRule(lowuser, (True, ('auth', 'user', 'set', 'apikey')))

            _, rtdf1 = await core.callStorm('return($lib.auth.users.byname(root).genApiKey(weee, duration=10))',
                                            opts=lowuser_opts)
            self.eq(rtdf1.get('user'), root)
            lowuser_opts = {'user': lowuser, 'vars': {'iden': rtdf1.get('iden')}}

            q = 'return($lib.auth.users.byname(root).getApiKey($iden))'
            _rtdf1 = await core.callStorm(q, opts=lowuser_opts)
            self.eq(_rtdf1, rtdf1)

            q = '$u=$lib.auth.users.byname(root) return($u.listApiKeys())'
            rootkeys = await core.callStorm(q, opts=lowuser_opts)
            self.len(2, rootkeys)
            _kdefs = [bkdf0, rtdf1]
            for kdef in rootkeys:
                self.isin(kdef, _kdefs)
                _kdefs.remove(kdef)
            self.len(0, _kdefs)

            q = 'return($lib.auth.users.byname(root).modApiKey($iden, name, hahah))'
            _rtdf1_2 = await core.callStorm(q, opts=lowuser_opts)
            self.eq(_rtdf1_2.get('iden'), _rtdf1.get('iden'))
            self.eq(_rtdf1_2.get('name'), 'hahah')

            q = 'return($lib.auth.users.byname(root).delApiKey($iden))'
            self.true(await core.callStorm(q, opts=lowuser_opts))

            q = '$u=$lib.auth.users.byname(root) return($u.listApiKeys())'
            rootkeys = await core.callStorm(q, opts=lowuser_opts)
            self.len(1, rootkeys)
            self.eq(rootkeys, (bkdf0,))

            # API keys work to identify the user
            async with self.getHttpSess(port=hport) as sess:

                headers0 = {'X-API-KEY': bkk0}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/storm/call', headers=headers0,
                                       json={'query': 'return( $lib.user.name() )'})
                answ = await resp.json()
                self.eq('ok', answ['status'])
                self.eq('root', answ['result'])

                headers0 = {'X-API-KEY': ltk0}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/storm/call', headers=headers0,
                                       json={'query': 'return( $lib.user.name() )'})
                answ = await resp.json()
                self.eq('ok', answ['status'])
                self.eq('lowuser', answ['result'])
