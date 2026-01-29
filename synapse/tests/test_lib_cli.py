import asyncio

import synapse.exc as s_exc

import synapse.lib.cli as s_cli
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

class TstThrowCmd(s_cli.Cmd):
    '''
    Throw an exception.
    '''
    _cmd_name = 'throwzero'

    async def runCmdOpts(self, opts):
        1 / 0

class TstThrowKeyboard(s_cli.Cmd):
    '''
    Throw an exception.
    '''
    _cmd_name = 'throwkeyboard'

    async def runCmdOpts(self, opts):
        raise asyncio.CancelledError()


class CliTest(s_t_utils.SynTest):

    async def test_cli_prompt(self):
        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp) as cli:
            self.eq(cli.getCmdPrompt(), 'cli> ')
            cli.cmdprompt = 'hehe> '
            self.eq(cli.getCmdPrompt(), 'hehe> ')

    async def test_cli_get_set(self):
        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp, hehe='haha') as cli:
            self.eq(cli.get('hehe'), 'haha')
            self.none(cli.get('foo'))
            cli.set('foo', 'bar')
            self.eq(cli.get('foo'), 'bar')
            await cli.runCmdLine('locs')
            self.true(outp.expect('hehe'))
            self.true(outp.expect('haha'))
            self.true(outp.expect('foo'))
            self.true(outp.expect('bar'))

        outp = self.getTestOutp()
        async with self.getTestCoreAndProxy() as (core, proxy):
            async with await s_cli.Cli.anit(proxy, outp=outp) as cli:
                cli.echoline = True
                await cli.runCmdLine('locs')
                self.true(outp.expect('syn:local:version'))
                self.true(outp.expect('syn:remote:version'))
                self.true(outp.expect(s_version.verstring))

    async def test_cli_quit(self):
        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp) as cli:
            await cli.runCmdLine('quit')
            self.true(cli.isfini)

    async def test_cli_help(self):
        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp) as cli:
            await cli.runCmdLine('help')
        self.true(outp.expect('Quit the current command line interpreter.'))

        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp) as cli:
            await cli.runCmdLine('help newp')
        self.true(outp.expect('=== NOT FOUND: newp'))

    async def test_cli_notacommand(self):
        outp = self.getTestOutp()
        async with await s_cli.Cli.anit(None, outp=outp) as cli:
            await cli.runCmdLine('notacommand')
        self.true(outp.expect('cmd not found: notacommand'))

    async def test_cli_cmdret(self):

        class WootCmd(s_cli.Cmd):
            _cmd_name = 'woot'

            async def runCmdOpts(self, opts):
                return 20

        async with await s_cli.Cli.anit(None) as cli:
            cli.addCmdClass(WootCmd)
            self.eq(await cli.runCmdLine('woot'), 20)

    async def test_cli_cmd(self):
        async with await s_cli.Cli.anit(None) as cli:
            quit = cli.getCmdByName('quit')
            self.nn(quit.getCmdDoc())
            self.nn(quit.getCmdBrief())

    async def test_cli_opts_flag(self):

        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho')

            self.eq(opts.get('bar'), True)
            self.eq(opts.get('haha'), 'hoho')

    async def test_cli_opts_list(self):

        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'list'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho haha "hehe hehe"')

            self.eq(opts.get('bar'), True)
            self.eq(tuple(opts.get('haha')), ('hoho', 'haha', 'hehe hehe'))

    async def test_cli_opts_enum(self):
        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--enum', {'type': 'enum', 'enum:vals': ('foo', 'bar', 'baz'), 'defval': 'def'}),
            )
            opts = quit.getCmdOpts('quit')
            self.eq(opts.get('enum'), 'def')

            opts = quit.getCmdOpts('quit --enum foo')
            self.eq(opts.get('enum'), 'foo')

            opts = quit.getCmdOpts('quit --enum bar')
            self.eq(opts.get('enum'), 'bar')

            opts = quit.getCmdOpts('quit --enum baz')
            self.eq(opts.get('enum'), 'baz')

            self.raises(s_exc.BadSyntax, quit.getCmdOpts, 'quit --enum newp')

    async def test_cli_opts_glob(self):

        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {}),
                ('haha', {'type': 'glob'}),
            )

            opts = quit.getCmdOpts('quit --bar hoho lulz')

            self.eq(opts.get('bar'), True)
            self.eq(opts.get('haha'), 'hoho lulz')

    async def test_cli_opts_defval(self):

        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'valu', 'defval': 'lol'}),
                ('haha', {'type': 'glob'}),
            )

            opts = quit.getCmdOpts('quit hoho lulz')
            self.eq(opts.get('bar'), 'lol')

    async def test_cli_opts_parse_valu(self):

        async with await s_cli.Cli.anit(None) as cli:

            quit = cli.getCmdByName('quit')

            quit._cmd_syntax = (
                ('--bar', {'type': 'valu'}),
            )

            opts = quit.getCmdOpts('quit --bar woah')
            self.eq(opts.get('bar'), 'woah')

            self.raises(s_exc.BadSyntax, quit.getCmdOpts, 'quit --bar woah this is too much text')

    async def test_cli_opts_parse_list(self):

        async with await s_cli.Cli.anit(None) as cli:

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

    async def test_cli_cmd_loop_quit(self):
        outp = self.getTestOutp()
        cmdg = s_t_utils.CmdGenerator(['help', 'quit'])

        async with await s_cli.Cli.anit(None, outp) as cli:
            cli.prompt = cmdg
            await cli.runCmdLoop()
            self.eq(cli.isfini, True)

        self.true(outp.expect('o/'))

    async def test_cli_cmd_loop_eof(self):
        outp = self.getTestOutp()
        cmdg = s_t_utils.CmdGenerator(['help', EOFError()])
        async with await s_cli.Cli.anit(None, outp) as cli:
            cli.prompt = cmdg
            await cli.runCmdLoop()
            self.eq(cli.isfini, True)
        self.false(outp.expect('o/', throw=False))

    async def test_cli_cmd_loop_bad_input(self):
        outp = self.getTestOutp()
        cmdg = s_t_utils.CmdGenerator([1234, EOFError()])
        async with await s_cli.Cli.anit(None, outp) as cli:
            cli.prompt = cmdg
            await cli.runCmdLoop()
            self.eq(cli.isfini, True)
        self.true(outp.expect("AttributeError: 'int' object has no attribute 'strip'", throw=False))

    async def test_cli_cmd_loop_keyint(self):

        outp = self.getTestOutp()

        cmdg = s_t_utils.CmdGenerator(['help', KeyboardInterrupt(), 'quit'])

        async with await s_cli.Cli.anit(None, outp) as cli:
            cli.prompt = cmdg
            await cli.runCmdLoop()
            self.eq(cli.isfini, True)

        self.true(outp.expect('<ctrl-c>'))

    async def test_cli_cmd_loop(self):

        outp = self.getTestOutp()
        cmdg = s_t_utils.CmdGenerator(['help', 'locs', '', '    ', 'throwzero', 'throwkeyboard', 'quit'])

        async with await s_cli.Cli.anit(None, outp) as cli:

            cli.prompt = cmdg

            cli.addCmdClass(TstThrowCmd)
            cli.addCmdClass(TstThrowKeyboard)

            await cli.runCmdLoop()

            self.true(outp.expect('o/'))
            self.true(outp.expect('"syn:local:version"'))
            self.true(outp.expect(f'"{s_version.verstring}"'))
            self.true(outp.expect('ZeroDivisionError'))
            self.true(outp.expect('Cmd cancelled'))
            self.true(cli.isfini)

    async def test_cli_fini_disconnect(self):

        outp = self.getTestOutp()

        async with self.getTestCoreAndProxy() as (core, prox):
            cli = await s_cli.Cli.anit(prox, outp=outp)

        self.true(prox.isfini)
        self.true(core.isfini)
        self.true(cli.isfini)
        self.true(outp.expect('connection closed...'))
