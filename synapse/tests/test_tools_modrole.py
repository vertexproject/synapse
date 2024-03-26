import synapse.lib.output as s_output
import synapse.tests.utils as s_test
import synapse.tools.modrole as s_t_modrole

rolelist = s_test.deguidify('''
Roles:
  ce6928dfe88cace918c405bbef51e72f - all
  0f316b3f3e6ec970fcdb9a085fcd5b77 - visi
'''.strip())

roleinfo = s_test.deguidify('''
Role: visi (145c3321a0cd0cd06de19174415a7aeb)

  Rules:
    [0  ] - !foo.bar.baz
    [1  ] - foo.bar

  Gates:
    3ad191c63a201df3246c6d6ff81763ad
      Admin: False
      [0  ] - !bar.baz.faz
      [1  ] - bar.baz
'''.strip())

class ModRoleTest(s_test.SynTest):

    async def test_tools_modrole(self):
        async with self.getTestCore() as core:

            svcurl = core.getLocalUrl()
            argv = (
                '--svcurl', svcurl,
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_modrole.main(argv, outp=outp))
            self.isin('ERROR: Role not found (need --add?): visi', str(outp))

            argv = (
                '--svcurl', svcurl,
                '--add',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin('Adding role: visi', str(outp))
            self.nn(await core.auth.getRoleByName('visi'))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--allow', 'foo.bar',
                '--deny', 'foo.bar.baz',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin('...adding allow rule: foo.bar', str(outp))
            self.isin('...adding deny rule: foo.bar.baz', str(outp))
            visi = await core.auth.getRoleByName('visi')
            self.true(bool(visi.allowed('foo.bar.gaz'.split('.'))))
            self.false(bool(visi.allowed('foo.bar.baz'.split('.'))))

            gateiden = core.getLayer().iden
            argv = (
                '--svcurl', svcurl,
                'visi',
                '--allow', 'bar.baz',
                '--deny', 'bar.baz.faz',
                '--gate', gateiden,
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin(f'...adding allow rule: bar.baz on gate {gateiden}', str(outp))
            self.isin(f'...adding deny rule: bar.baz.faz on gate {gateiden}', str(outp))

            gate = await core.getAuthGate(gateiden)
            for role in gate['roles']:
                if role['iden'] == visi.iden:
                    self.isin((True, ('bar', 'baz')), role['rules'])
                    self.isin((False, ('bar', 'baz', 'faz')), role['rules'])

            argv = (
                '--svcurl', svcurl,
                '--list',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin(rolelist, s_test.deguidify(str(outp)))

            argv = (
                '--svcurl', svcurl,
                '--list',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin(roleinfo, s_test.deguidify(str(outp)))

            argv = (
                '--svcurl', svcurl,
                '--list',
                'newprole',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_modrole.main(argv, outp=outp))
            self.isin('ERROR: Role not found: newprole', str(outp))

            argv = (
                '--svcurl', svcurl,
                'visi',
                '--gate', 'newp',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_modrole.main(argv, outp=outp))
            self.isin('ERROR: No auth gate found with iden: newp', str(outp))

            argv = (
                '--svcurl', svcurl,
                '--add',
                '--del',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_modrole.main(argv, outp=outp))
            self.isin('ERROR: Cannot specify --add and --del together.', str(outp))

            argv = (
                '--svcurl', svcurl,
                '--del',
                'visi',
            )
            outp = s_output.OutPutStr()
            self.eq(0, await s_t_modrole.main(argv, outp=outp))
            self.isin('...deleting role: visi', str(outp))
            self.none(await core.auth.getRoleByName('visi'))

            argv = (
                '--svcurl', svcurl,
            )
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_modrole.main(argv, outp=outp))
            self.isin('ERROR: A rolename argument is required when --list is not specified.', str(outp))
