import os
import json
import signal
import asyncio
import logging
import traceback
import collections

import regex

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.parser as s_parser
import synapse.lib.grammar as s_grammar
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)


class Cmd:
    '''
    Base class for modular commands in the synapse CLI.
    '''
    _cmd_name = 'fixme'
    _cmd_syntax = ()

    def __init__(self, cli, **opts):
        self._cmd_cli = cli
        self._cmd_opts = opts

    async def runCmdLine(self, line):
        '''
        Run a line of command input for this command.

        Args:
            line (str): Line to execute

        Examples:
            Run the foo command with some arguments:

                await foo.runCmdLine('foo --opt baz woot.com')

        '''
        opts = self.getCmdOpts(line)
        return await self.runCmdOpts(opts)

    def getCmdItem(self):
        '''
        Get a reference to the object we are commanding.
        '''
        return self._cmd_cli.item

    def getCmdOpts(self, text):
        '''
        Use the _cmd_syntax def to split/parse/normalize the cmd line.

        Args:
            text (str): Command to process.

        Notes:
            This is implemented independent of argparse (et al) due to the
            need for syntax aware argument splitting. Also, allows different
            split per command type

        Returns:
            dict: An opts dictionary.
        '''
        off = 0

        _, off = s_grammar.nom(text, off, s_grammar.whites)

        name, off = s_grammar.meh(text, off, s_grammar.whites)

        _, off = s_grammar.nom(text, off, s_grammar.whites)

        opts = {}

        args = collections.deque([synt for synt in self._cmd_syntax if not synt[0].startswith('-')])
        switches = {synt[0]: synt for synt in self._cmd_syntax if synt[0].startswith('-')}

        # populate defaults and lists
        for synt in self._cmd_syntax:
            snam = synt[0].strip('-')

            defval = synt[1].get('defval')
            if defval is not None:
                opts[snam] = defval

            if synt[1].get('type') == 'list':
                opts[snam] = []

        def atswitch(t, o):
            # check if we are at a recognized switch.  if not
            # assume the data is part of regular arguments.
            if not text.startswith('-', o):
                return None, o

            name, x = s_grammar.meh(t, o, s_grammar.whites)
            swit = switches.get(name)
            if swit is None:
                return None, o

            return swit, x

        while off < len(text):

            _, off = s_grammar.nom(text, off, s_grammar.whites)

            swit, off = atswitch(text, off)
            if swit is not None:

                styp = swit[1].get('type', 'flag')
                snam = swit[0].strip('-')

                if styp == 'valu':
                    valu, off = s_parser.parse_cmd_string(text, off)
                    opts[snam] = valu

                elif styp == 'list':
                    valu, off = s_parser.parse_cmd_string(text, off)
                    if not isinstance(valu, list):
                        valu = valu.split(',')
                    opts[snam].extend(valu)

                elif styp == 'enum':
                    vals = swit[1].get('enum:vals')
                    valu, off = s_parser.parse_cmd_string(text, off)
                    if valu not in vals:
                        raise s_exc.BadSyntax(mesg='%s (%s)' % (swit[0], '|'.join(vals)),
                                                   text=text)

                    opts[snam] = valu

                else:
                    opts[snam] = True

                continue

            if not args:
                raise s_exc.BadSyntax(mesg='trailing text: [%s]' % (text[off:],),
                                           text=text)

            synt = args.popleft()
            styp = synt[1].get('type', 'valu')

            # a glob type eats the remainder of the string
            if styp == 'glob':
                opts[synt[0]] = text[off:]
                break

            # eat the remainder of the string as separate vals
            if styp == 'list':
                valu = []

                while off < len(text):
                    item, off = s_parser.parse_cmd_string(text, off)
                    valu.append(item)

                opts[synt[0]] = valu
                break

            valu, off = s_parser.parse_cmd_string(text, off)
            opts[synt[0]] = valu

        return opts

    def getCmdBrief(self):
        '''
        Return the single-line description for this command.
        '''
        return self.getCmdDoc().strip().split('\n', 1)[0].strip()

    def getCmdName(self):
        return self._cmd_name

    def getCmdDoc(self):
        '''
        Return the help/doc output for this command.
        '''
        if not self.__doc__:  # pragma: no cover
            return ''
        return self.__doc__

    def printf(self, mesg, addnl=True, color=None):
        return self._cmd_cli.printf(mesg, addnl=addnl, color=color)

    async def runCmdOpts(self, opts):
        '''
        Perform the command actions. Must be implemented by Cmd implementers.

        Args:
            opts (dict): Options dictionary.

        '''
        raise s_exc.NoSuchImpl(mesg='runCmdOpts must be implemented by subclasses.',
                               name='runCmdOpts')

_setre = regex.compile(r'\s*set\s+editing-mode\s+vi\s*')

def _inputrc_enables_vi_mode():
    '''
    Emulate a small bit of readline behavior.

    Returns:
        (bool) True if current user enabled vi mode ("set editing-mode vi") in .inputrc
    '''
    for filepath in (os.path.expanduser('~/.inputrc'), '/etc/inputrc'):
        try:
            with open(filepath) as f:
                for line in f:
                    if _setre.fullmatch(line):
                        return True
        except IOError:
            continue
    return False

class Cli(s_base.Base):
    '''
    A modular / event-driven CLI base object.
    '''
    histfile = 'cmdr_history'

    async def __anit__(self, item, outp=None, **locs):

        await s_base.Base.__anit__(self)

        if outp is None:
            outp = s_output.OutPut()

        self.outp = outp
        self.locs = locs
        self.cmdtask = None  # type: asyncio.Task

        self.sess = None
        self.vi_mode = _inputrc_enables_vi_mode()

        self.item = item    # whatever object we are commanding

        self.echoline = False
        self.colorsenabled = False

        if isinstance(self.item, s_base.Base):
            self.item.onfini(self._onItemFini)

        self.locs['syn:local:version'] = s_version.verstring

        if isinstance(self.item, s_telepath.Proxy):
            version = self.item._getSynVers()
            if version is None:  # pragma: no cover
                self.locs['syn:remote:version'] = 'Remote Synapse version unavailable'
            else:
                self.locs['syn:remote:version'] = '.'.join([str(v) for v in version])

        self.cmds = {}
        self.cmdprompt = 'cli> '

        self.initCmdClasses()

    def initCmdClasses(self):
        self.addCmdClass(CmdHelp)
        self.addCmdClass(CmdQuit)
        self.addCmdClass(CmdLocals)

    async def _onItemFini(self):

        if self.isfini:
            return

        self.printf('connection closed...')

        await self.fini()

    async def addSignalHandlers(self):
        '''
        Register SIGINT signal handler with the ioloop to cancel the currently running cmdloop task.
        '''

        def sigint():
            self.printf('<ctrl-c>')
            if self.cmdtask is not None:
                self.cmdtask.cancel()

        self.loop.add_signal_handler(signal.SIGINT, sigint)

    def get(self, name, defval=None):
        return self.locs.get(name, defval)

    def set(self, name, valu):
        self.locs[name] = valu

    async def prompt(self, text=None):
        '''
        Prompt for user input from stdin.
        '''
        if self.sess is None:
            histfp = s_common.getSynPath(self.histfile)
            # Ensure the file is read/writeable
            with s_common.genfile(histfp):
                pass
            self.sess = PromptSession(history=FileHistory(histfp))

        if text is None:
            text = self.cmdprompt

        with patch_stdout():
            retn = await self.sess.prompt_async(text, vi_mode=self.vi_mode, enable_open_in_editor=True)
            return retn

    def printf(self, mesg, addnl=True, color=None):
        if not self.colorsenabled:
            return self.outp.printf(mesg, addnl=addnl)

        # print_formatted_text can't handle \r
        mesg = mesg.replace('\r', '')

        if color is not None:
            mesg = FormattedText([(color, mesg)])
        return print_formatted_text(mesg, end='\n' if addnl else '')

    def addCmdClass(self, ctor, **opts):
        '''
        Add a Cmd subclass to this cli.
        '''
        item = ctor(self, **opts)
        name = item.getCmdName()
        self.cmds[name] = item

    def getCmdNames(self):
        '''
        Return a list of all the known command names for the CLI.
        '''
        return list(self.cmds.keys())

    def getCmdByName(self, name):
        '''
        Return a Cmd instance by name.
        '''
        return self.cmds.get(name)

    def getCmdPrompt(self):
        '''
        Get the command prompt.

        Returns:
            str: Configured command prompt
        '''
        return self.cmdprompt

    async def runCmdLoop(self):
        '''
        Run commands from a user in an interactive fashion until fini() or EOFError is raised.
        '''
        while not self.isfini:

            self.cmdtask = None

            try:

                line = await self.prompt()
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                coro = self.runCmdLine(line)
                self.cmdtask = self.schedCoro(coro)
                await self.cmdtask

            except KeyboardInterrupt:

                if self.isfini:
                    return

                self.printf('<ctrl-c>')

            except (s_exc.CliFini, EOFError):
                await self.fini()

            except Exception:
                s = traceback.format_exc()
                self.printf(s)

            finally:
                if self.cmdtask is not None:
                    self.cmdtask.cancel()
                    try:
                        self.cmdtask.result()
                    except asyncio.CancelledError:
                        # Wait a beat to let any remaining nodes to print out before we print the prompt
                        await asyncio.sleep(1)
                    except Exception:
                        pass

    async def runCmdLine(self, line):
        '''
        Run a single command line.

        Args:
            line (str): Line to execute.

        Examples:
            Execute the 'woot' command with the 'help' switch:

                await cli.runCmdLine('woot --help')

        Returns:
            object: Arbitrary data from the cmd class.
        '''
        if self.echoline:
            self.outp.printf(f'{self.cmdprompt}{line}')

        ret = None

        name = line.split(None, 1)[0]

        cmdo = self.getCmdByName(name)
        if cmdo is None:
            self.printf('cmd not found: %s' % (name,))
            return

        try:

            ret = await cmdo.runCmdLine(line)

        except s_exc.CliFini:
            await self.fini()

        except asyncio.CancelledError:
            self.printf('Cmd cancelled')

        except s_exc.ParserExit as e:
            pass  # avoid duplicate print

        except Exception as e:
            exctxt = traceback.format_exc()
            self.printf(exctxt)
            self.printf('error: %s' % e)

        return ret

class CmdQuit(Cmd):
    '''
    Quit the current command line interpreter.

    Example:

        quit
    '''

    _cmd_name = 'quit'

    async def runCmdOpts(self, opts):
        self.printf('o/')
        raise s_exc.CliFini()

class CmdHelp(Cmd):
    '''
    List commands and display help output.

    Example:

        help foocmd

    '''
    _cmd_name = 'help'
    _cmd_syntax = (
        ('cmds', {'type': 'list'}),  # type: ignore
    )

    async def runCmdOpts(self, opts):
        cmds = opts.get('cmds')

        # if they didn't specify one, just show the list
        if not cmds:
            cmds = sorted(self._cmd_cli.getCmdNames())

            padsize = max([len(n) for n in cmds])

            for name in cmds:
                padname = name.ljust(padsize)
                cmdo = self._cmd_cli.getCmdByName(name)
                brief = cmdo.getCmdBrief()
                self.printf('%s - %s' % (padname, brief))

            return

        for name in cmds:

            cmdo = self._cmd_cli.getCmdByName(name)
            if cmdo is None:
                self.printf('=== NOT FOUND: %s' % (name,))
                continue

            self.printf('=== %s' % (name,))
            self.printf(cmdo.getCmdDoc())

        return

class CmdLocals(Cmd):
    '''
    List the current locals for a given CLI object.
    '''
    _cmd_name = 'locs'

    async def runCmdOpts(self, opts):
        ret = {}
        for k, v in self._cmd_cli.locs.items():
            if isinstance(v, (int, str)):
                ret[k] = v
            else:
                ret[k] = repr(v)
        mesg = json.dumps(ret, indent=2, sort_keys=True)
        self.printf(mesg)
