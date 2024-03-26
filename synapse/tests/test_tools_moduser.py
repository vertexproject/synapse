import synapse.lib.output as s_output
import synapse.tests.utils as s_test
import synapse.tools.moduser as s_t_moduser

userlist = '''
Users:
  root
  visi
'''.strip()

userinfo = s_test.deguidify('''
User: visi (04dddd4ff39e4ce00b36c7d526b9eac7)

  Locked: False
  Admin: False
  Email: visi@test.com
  Rules:
    [0  ] - !foo.bar.baz
    [1  ] - foo.bar

  Roles:
    576a948f9944c58d3953f0d36bc2da81 - all

  Gates:
    c7b276154c0c799430668cb3c4cd259d
      Admin: False
      [0  ] - !bar.baz.faz
      [1  ] - bar.baz
'''.strip())

class ModUserTest(s_test.SynTest):

    async def test_tools_moduser(self):
        async with self.getTestCore() as core:

            ninjas = await core.auth.addRole('ninjas')

            svcurl = core.getLocalUrl()
            argv = (
                '--svcurl', svcurl,
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: User not found (need --add?): visi', str(outp))

            argv = (
                '--svcurl', svcurl,
                '--add',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('Adding user: visi', str(outp))
            self.nn(await core.auth.getUserByName('visi'))

            argv = (
                '--svcurl', svcurl,
                '--grant', 'woot',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: Role not found: woot', str(outp))

            argv = (
                '--svcurl', svcurl,
                '--revoke', 'woot',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: Role not found: woot', str(outp))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--passwd', 'mySecretPassword',
            )
            outp = s_output.OutPutStr()
            visi = await core.auth.getUserByName('visi')
            self.false(await visi.tryPasswd('mySecretPassword'))
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('...setting passwd: mySecretPassword', str(outp))
            self.true(await visi.tryPasswd('mySecretPassword'))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--email', 'visi@test.com',
            )
            outp = s_output.OutPutStr()
            visi = await core.auth.getUserByName('visi')
            self.none(visi.info.get('email'))
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('...setting email: visi@test.com', str(outp))
            self.eq('visi@test.com', visi.info.get('email'))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--admin', 'true',
                '--locked', 'true',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('...setting admin: true', str(outp))
            self.isin('...setting locked: true', str(outp))
            visi = await core.auth.getUserByName('visi')
            self.true(visi.isAdmin())
            self.true(visi.isLocked())

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--grant', 'ninjas',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            visi = await core.auth.getUserByName('visi')
            self.true(visi.hasRole(ninjas.iden))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--revoke', 'ninjas',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            visi = await core.auth.getUserByName('visi')
            self.false(visi.hasRole(ninjas.iden))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--admin', 'false',
                '--locked', 'false',
                '--allow', 'foo.bar',
                '--deny', 'foo.bar.baz',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('...setting admin: false', str(outp))
            self.isin('...setting locked: false', str(outp))
            self.isin('...adding allow rule: foo.bar', str(outp))
            self.isin('...adding deny rule: foo.bar.baz', str(outp))
            visi = await core.auth.getUserByName('visi')
            self.false(visi.isAdmin())
            self.false(visi.isLocked())
            self.true(bool(visi.allowed('foo.bar.gaz'.split('.'))))
            self.false(bool(visi.allowed('foo.bar.baz'.split('.'))))

            gateiden = core.getLayer().iden
            argv = (
                '--svcurl', svcurl,
                'visi',
                '--admin', 'true',
                '--gate', gateiden,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin(f'...setting admin: true on gate {gateiden}', str(outp))

            gate = await core.getAuthGate(gateiden)
            for user in gate['users']:
                if user['iden'] == visi.iden:
                    self.true(user['admin'])

            gateiden = core.getLayer().iden
            argv = (
                '--svcurl', svcurl,
                'visi',
                '--admin', 'false',
                '--allow', 'bar.baz',
                '--deny', 'bar.baz.faz',
                '--gate', gateiden,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin(f'...setting admin: false on gate {gateiden}', str(outp))
            self.isin(f'...adding allow rule: bar.baz on gate {gateiden}', str(outp))
            self.isin(f'...adding deny rule: bar.baz.faz on gate {gateiden}', str(outp))

            gate = await core.getAuthGate(gateiden)
            for user in gate['users']:
                if user['iden'] == visi.iden:
                    self.isin((True, ('bar', 'baz')), user['rules'])
                    self.isin((False, ('bar', 'baz', 'faz')), user['rules'])

            argv = (
                '--svcurl', svcurl,
                '--list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin(userlist, str(outp))

            argv = (
                '--svcurl', svcurl,
                '--list',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin(userinfo, s_test.deguidify(str(outp)))

            argv = (
                '--svcurl', svcurl,
                '--list',
                'newpuser',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: User not found: newpuser', str(outp))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--gate', 'newp',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: No auth gate found with iden: newp', str(outp))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--add',
                '--del',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: Cannot specify --add and --del together.', str(outp))

            # Del visi
            argv = (
                '--svcurl', svcurl,
                'visi',
                '--del',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_moduser.main(argv, outp=outp))
            self.isin('...deleting user: visi', str(outp))

            argv = (
                '--svcurl', svcurl,
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: User not found (need --add?): visi', str(outp))

            argv = (
                '--svcurl', svcurl,
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_moduser.main(argv, outp=outp))
            self.isin('ERROR: A username argument is required when --list is not specified.', str(outp))
