import synapse.exc as s_exc
import synapse.lib.storm as s_storm

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

            q = '$lib.auth.users.byname(visi).setAdmin($admin, gateiden=$lib.view.get().layers.0.iden)'
            await core.nodes(q, opts={'vars': {'admin': True}})
            msgs = await core.stormlist('auth.user.allowed visi node.tag.del --gate $lib.view.get().layers.0.iden')
            self.stormIsInPrint('allowed: true - The user is an admin of auth gate 741529fa80e3fb42f63c5320e4bf348f',
                                msgs, deguid=True)
            await core.nodes(q, opts={'vars': {'admin': False}})

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
