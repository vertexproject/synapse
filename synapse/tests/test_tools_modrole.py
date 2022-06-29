import synapse.lib.output as s_output
import synapse.tests.utils as s_test
import synapse.tools.modrole as s_t_modrole

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
