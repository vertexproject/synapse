import synapse.lib.output as s_output
import synapse.tests.utils as s_test
import synapse.tools.moduser as s_t_moduser

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
