import synapse.lib.cli as s_cli

from synapse.tests.common import *

class Hehe:

    def cmd_hehe(self, cli, line):
        '''
        The hehe cmd.
        '''
        cli.vprint('hehe')

class CliTest(SynTest):

    def test_cli_print(self):

        cli = s_cli.Cli()
        wait = self.getTestWait(cli, 1, 'cli:print')

        cli.vprint('hi there!')

        wait.wait()

        self.assertEqual( wait.events[0][1].get('msg'), 'hi there!')

    def test_cli_cmdfunc(self):

        data = {}
        def woot(xcli,line):
            data['line'] = line

        cli = s_cli.Cli()
        cli.addCmdFunc(woot)

        cli.runCmdLine('woot haha')

        self.assertEqual( data.get('line'), 'woot haha')

    def test_cli_quit(self):
        cli = s_cli.Cli()
        cli.runCmdLine('quit')
        self.assertTrue(cli.isfini)

    def test_cli_brief(self):

        def woot(xcli,line):
            '''
            This is a brief.
            And this is some description.
            '''
            pass

        cli = s_cli.Cli()
        cli.addCmdFunc(woot)

        self.assertEqual( cli.getCmdBrief('woot'), 'This is a brief.' )

        cli.fini()

    def test_cli_cmdmeths(self):
        hehe = Hehe()
        cli = s_cli.Cli()

        cli.addCmdMeths(hehe)

        self.assertEqual( cli.getCmdBrief('hehe'), 'The hehe cmd.')

        cli.fini()

    def test_cli_delcmd(self):
        cli = s_cli.Cli()
        self.assertIsNotNone( cli.getCmdFunc('quit') )
        cli.delCmdFunc('quit')
        self.assertIsNone( cli.getCmdFunc('quit') )

    def test_cli_cmdret(self):

        def woot(cli,line):
            return 20

        cli = s_cli.Cli()
        cli.addCmdFunc(woot)

        self.assertEqual( cli.runCmdLine('woot hehe'), 20 )

        cli.fini()
