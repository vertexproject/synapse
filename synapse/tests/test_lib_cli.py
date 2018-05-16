import synapse.lib.cli as s_cli

from synapse.tests.common import *

class TstThrowCmd(s_cli.Cmd):
    '''
    Throw an exception.
    '''
    _cmd_name = 'throwzero'

    def runCmdOpts(self, opts):
        ret = 1 / 0

class TstThrowKeyboard(s_cli.Cmd):
    '''
    Throw an exception.
    '''
    _cmd_name = 'throwkeyboard'

    def runCmdOpts(self, opts):
        raise KeyboardInterrupt('TstThrowKeyboard')


class CliTest(SynTest):

    def test_cli_prompt(self):
        outp = self.getTestOutp()
        with s_cli.Cli(None, outp=outp) as cli:
            self.eq(cli.getCmdPrompt(), 'cli> ')
            cli.cmdprompt = 'hehe> '
            self.eq(cli.getCmdPrompt(), 'hehe> ')

    def test_cli_get_set(self):
        outp = self.getTestOutp()
        with s_cli.Cli(None, outp=outp, hehe='haha') as cli:
            self.eq(cli.get('hehe'), 'haha')
            self.none(cli.get('foo'))
            cli.set('foo', 'bar')
            self.eq(cli.get('foo'), 'bar')
            cli.runCmdLine('locs')
            self.true(outp.expect('hehe'))
            self.true(outp.expect('haha'))
            self.true(outp.expect('foo'))
            self.true(outp.expect('bar'))

    def test_cli_quit(self):
        outp = self.getTestOutp()
        with s_cli.Cli(None, outp=outp) as cli:
            cli.runCmdLine('quit')
            self.true(cli.isfini)

    def test_cli_help(self):
        outp = self.getTestOutp()
        with s_cli.Cli(None, outp=outp) as cli:
            cli.runCmdLine('help')
        self.true(outp.expect('Quit the current command line interpreter.'))

    def test_cli_notacommand(self):
        outp = self.getTestOutp()
        with s_cli.Cli(None, outp=outp) as cli:
            cli.runCmdLine('notacommand')
        self.true(outp.expect('cmd not found: notacommand'))

    def test_cli_cmdret(self):

        class WootCmd(s_cli.Cmd):
            _cmd_name = 'woot'
            def runCmdOpts(self, opts):
                return 20

        with s_cli.Cli(None) as cli:
            cli.addCmdClass(WootCmd)
            self.eq(cli.runCmdLine('woot'), 20)

    def test_cli_cmd(self):
        with s_cli.Cli(None) as cli:
            quit = cli.getCmdByName('quit')
            self.nn(quit.getCmdDoc())
            self.nn(quit.getCmdBrief())

    def test_cli_opts_flag(self):
        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho')

            self.eq(opts.get('bar'), True)
            self.eq(opts.get('haha'), 'hoho')

    def test_cli_opts_list(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'list'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho haha "hehe hehe"')

            self.eq(opts.get('bar'), True)
            self.eq(tuple(opts.get('haha')), ('hoho', 'haha', 'hehe hehe'))

    def test_cli_opts_glob(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'glob'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho lulz')

            self.eq(opts.get('bar'), True)
            self.eq(opts.get('haha'), 'hoho lulz')

    def test_cli_opts_defval(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'valu', 'defval': 'lol'}),
                ('haha', {'type': 'glob'}),
            )

            opts = quit.getCmdOpts('quit hoho lulz')
            self.eq(opts.get('bar'), 'lol')

    def test_cli_opts_parse_valu(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar woah')
            self.eq(opts.get('bar'), 'woah')

            self.raises(BadSyntaxError, quit.getCmdOpts, 'quit --bar woah this is too much text')

    def test_cli_opts_parse_list(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'list'}),
            )

            # The list must be quoted
            opts = quit.getCmdOpts('quit --bar "1,2,3"')
            self.eq(opts.get('bar'), ['1', '2', '3'])

            # Or encapsulated in a storm list syntax
            opts = quit.getCmdOpts('quit --bar (1, 2, 3)')
            self.eq(opts.get('bar'), [1, 2, 3])

            # A single item is fine
            opts = quit.getCmdOpts('quit --bar woah')
            self.eq(opts.get('bar'), ['woah'])

    def test_cli_opts_parse_enums(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'enum', 'enum:vals': ('foo', 'baz')}),
            )

            opts = quit.getCmdOpts('quit --bar foo')
            self.eq(opts.get('bar'), 'foo')
            opts = quit.getCmdOpts('quit --bar baz')
            self.eq(opts.get('bar'), 'baz')
            self.raises(BadSyntaxError, quit.getCmdOpts, 'quit --bar')
            self.raises(BadSyntaxError, quit.getCmdOpts, 'quit --bar bar')

    def test_cli_opts_parse_kwlist(self):

        with s_cli.Cli(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('bar', {'type': 'kwlist'}),
            )

            opts = quit.getCmdOpts('quit hehe=haha')
            self.eq(opts.get('bar'), [('hehe', 'haha')])

    def test_cli_cmd_loop_quit(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator(['help', 'quit'])

        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            with s_cli.Cli(None, outp) as cli:
                cli.runCmdLoop()
                self.eq(cli.isfini, True)
        self.true(outp.expect('o/'))

    def test_cli_cmd_loop_eof(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator(['help'], on_end=EOFError)
        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            with s_cli.Cli(None, outp) as cli:
                cli.runCmdLoop()
                self.eq(cli.isfini, True)
        self.false(outp.expect('o/', throw=False))

    def test_cli_cmd_loop_bad_input(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator([1234], on_end=EOFError)
        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            with s_cli.Cli(None, outp) as cli:
                cli.runCmdLoop()
                self.eq(cli.isfini, True)
        self.true(outp.expect("AttributeError: 'int' object has no attribute 'strip'", throw=False))

    def test_cli_cmd_loop_keyint(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator(['help'], on_end=KeyboardInterrupt)

        data = {'count': 0}

        def _onGetInput(mesg):
            data['count'] = data['count'] + 1
            if data['count'] > 2:
                cmdg.addCmd('quit')

        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            with s_cli.Cli(None, outp) as cli:
                cli.on('cli:getinput', _onGetInput)
                cli.runCmdLoop()
                self.eq(cli.isfini, True)

        self.true(outp.expect('<ctrl-c>'))

    def test_cli_cmd_loop(self):
        outp = self.getTestOutp()
        cmdg = CmdGenerator(['help',
                             'locs',
                             '',
                             '    ',
                             'throwzero',
                             'throwkeyboard',
                             'quit',
                             ])
        with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
            with s_cli.Cli(None, outp) as cli:
                cli.addCmdClass(TstThrowCmd)
                cli.addCmdClass(TstThrowKeyboard)
                cli.runCmdLoop()
                self.true(outp.expect('o/'))
                self.true(outp.expect('{}'))
                self.true(outp.expect('ZeroDivisionError'))
                self.true(outp.expect('<ctrl-c>'))
                self.true(cli.isfini)
