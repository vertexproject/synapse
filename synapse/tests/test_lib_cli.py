import synapse.lib.cli as s_cli

from synapse.tests.common import *

class Hehe:

    def cmd_hehe(self, cli, line):
        '''
        The hehe cmd.
        '''
        cli.vprint('hehe')

class CliTest(SynTest):

    def test_cli_quit(self):
        cli = s_cli.Cli()
        cli.runCmdLine('quit')
        self.assertTrue(cli.isfini)

    def test_cli_help(self):
        outp = s_output.OutPutStr()
        with s_cli.Cli(outp=outp) as cli:
            cli.runCmdLine('help')

        self.true( str(outp).find('Quit the current command line interpreter.') != -1 )

    def test_cli_cmdret(self):

        class WootCmd(s_cli.Cmd):
            _cmd_name = 'woot'
            def runCmdOpts(self, opts):
                return 20

        with s_cli.Cli() as cli:
            cli.addCmdClass(WootCmd)
            self.eq( cli.runCmdLine('woot'), 20 )

    def test_cli_cmd(self):
        with s_cli.Cli() as cli:
            quit = cli.getCmdByName('quit')
            self.nn( quit.getCmdDoc() )
            self.nn( quit.getCmdBrief() )

    def test_cli_opts_flag(self):
        with s_cli.Cli() as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar',{}),
                ('haha',{'type':'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho')

            self.eq( opts.get('--bar'), True )
            self.eq( opts.get('haha'), 'hoho')

    def test_cli_opts_flag(self):
        with s_cli.Cli() as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar',{}),
                ('haha',{'type':'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho')

            self.eq( opts.get('--bar'), True )
            self.eq( opts.get('haha'), 'hoho')

    def test_cli_opts_list(self):

        with s_cli.Cli() as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar',{}),
                ('haha',{'type':'list'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho haha "hehe hehe"')

            self.eq( opts.get('--bar'), True )
            self.eq( tuple(opts.get('haha')), ('hoho','haha','hehe hehe') )

    def test_cli_opts_glob(self):

        with s_cli.Cli() as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar',{}),
                ('haha',{'type':'glob'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho lulz')

            self.eq( opts.get('--bar'), True )
            self.eq( opts.get('haha'), 'hoho lulz')

