import synapse.tools.reload as s_t_reload

import synapse.tests.utils as s_test

class ReloadToolTest(s_test.SynTest):

    async def test_tool_reload(self):
        outp = self.getTestOutp()

        async with self.getTestCell(s_test.ReloadCell) as cell:  # type: s_test.ReloadCell
            url = cell.getLocalUrl()
            argb = ('--svcurl', url)

            argv = argb + ('list',)
            ret = await s_t_reload.main(argv, outp)
            self.eq(0, ret)
            outp.expect('no registered reload subsystems')

            outp.clear()
            argv = argb + ('reload',)
            ret = await s_t_reload.main(argv, outp)
            self.eq(0, ret)
            outp.expect('No subsystems reloaded.')

            await cell.addTestReload()
            await cell.addTestBadReload()

            outp.clear()
            argv = argb + ('list',)
            ret = await s_t_reload.main(argv, outp)
            self.eq(0, ret)
            outp.expect('testreload')
            outp.expect('badreload')

            outp.clear()
            argv = argb + ('reload', '-n', 'testreload')
            ret = await s_t_reload.main(argv, outp)
            self.eq(0, ret)
            outp.expect('testreload                              Success')

            outp.clear()
            argv = argb + ('reload',)
            ret = await s_t_reload.main(argv, outp)
            self.eq(0, ret)
            outp.expect('testreload                              Success')
            outp.expect('badreload                               Failed')

            # Sad name test
            outp.clear()
            argv = argb + ('reload', '-n', 'haha')
            ret = await s_t_reload.main(argv, outp)
            self.eq(1, ret)
            outp.expect('Error reloading cell')
            outp.expect('NoSuchName')
