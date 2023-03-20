import synapse.exc as s_exc
import synapse.lib.storm as s_storm

import synapse.tests.utils as s_test

visishow = '''
User: visi (8d19302a671c3d5c8eeaccde305413a0)

  Admin: False
  Rules:
    [0  ] - foo.bar
    [1  ] - !baz.faz

  Roles:
    878e79f585e74258d2a33ccdf817a47f - all
    1284e1976e8a4ad139a976482adb1588 - ninjas

  Gates:
    14aaa84884773c7791a388e48ca93029 - (layer)
      [0  ] - node
'''.strip()

ninjashow = '''
Role: ninjas (3c5318903adb4bbd67e100331d37961d)

  Rules:
    [0  ] - foo.bar
    [1  ] - !baz.faz

  Gates:
    734245de81ccb4284f0a169be9b81aa8 - (layer)
      [0  ] - node
'''.strip()

gateshow = '''
Gate Type: layer

Auth Gate Users:
  b1d8d5b4c946399113a25ebed44f490b - root
    Admin: True
    Rules:
  59f9e2c6d6f7cfae6dabe313a1f55396 - visi
    Admin: False
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

class StormLibAuthTest(s_test.SynTest):

    async def test_stormlib_auth(self):

        async with self.getTestCore() as core:

            for pdef in await core.getPermDefs():
                s_storm.reqValidPermDef(pdef)

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

            msgs = await core.stormlist('auth.user.grant visi ninjas')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Granting role ninjas to user visi.', msgs)

            msgs = await core.stormlist('auth.user.addrule visi foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule foo.bar to user visi.', msgs)
            msgs = await core.stormlist('auth.user.addrule visi "!baz.faz"')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule !baz.faz to user visi.', msgs)

            msgs = await core.stormlist('auth.role.addrule ninjas foo.bar')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule foo.bar to role ninjas.', msgs)
            msgs = await core.stormlist('auth.role.addrule ninjas "!baz.faz"')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Added rule !baz.faz to role ninjas.', msgs)

            msgs = await core.stormlist('auth.user.delrule visi --index 10')
            self.stormIsInErr('only has 2 rules', msgs)

            msgs = await core.stormlist('auth.role.delrule ninjas --index 10')
            self.stormIsInErr('only has 2 rules', msgs)

            msgs = await core.stormlist('auth.user.addrule visi node --gate $lib.view.get().layers.0.iden')
            self.stormHasNoWarnErr(msgs)

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
