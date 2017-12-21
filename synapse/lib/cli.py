import json
import traceback
import collections

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.mixins as s_mixins
import synapse.lib.output as s_output
import synapse.lib.syntax as s_syntax
import synapse.lib.reflect as s_reflect


def get_input(text):  # pragma: no cover
    '''
    Get input from a user via stdin.

    Notes:
        This is just a wrapper for input() so mocking does not have to replace builtin functions for testing runCmdLoop.

    Args:
        text (str): Text displayed prior to the input prompt.

    Returns:
        str: String of text from the user.
    '''
    return input(text)

class Cmd:
    '''
    Base class for modular commands in the synapse CLI.

    FIXME: document the _cmd_syntax definitions.
    '''
    _cmd_name = 'FIXME'
    _cmd_syntax = ()

    def __init__(self, cli, **opts):
        self._cmd_cli = cli
        self._cmd_opts = opts

    def runCmdLine(self, line):
        '''
        Run a line of command input for this command.

        Example:

            foo.runCmdLine('foo --opt baz woot.com')

        '''
        opts = self.getCmdOpts(line)
        return self.runCmdOpts(opts)

    def getCmdItem(self):
        '''
        Get a reference to the object we are commanding.
        '''
        return self._cmd_cli.item

    def getCmdOpts(self, text):
        '''
        Use the _cmd_syntax def to split/parse/normalize the cmd line.

        NOTE: This is implemented indepedent of argparse (et.al) due to
              the need for syntax aware argument splitting.
              ( also, allows different split per command type )
        '''
        off = 0

        _, off = s_syntax.nom(text, off, s_syntax.whites)

        name, off = s_syntax.meh(text, off, s_syntax.whites)

        _, off = s_syntax.nom(text, off, s_syntax.whites)

        opts = {}

        args = collections.deque([synt for synt in self._cmd_syntax if not synt[0].startswith('-')])

        switches = {synt[0]: synt for synt in self._cmd_syntax if synt[0].startswith('-')}

        # populate defaults and lists
        for synt in self._cmd_syntax:
            snam = synt[0].strip('-')

            defval = synt[1].get('defval')
            if defval is not None:
                opts[snam] = defval

            if synt[1].get('type') in ('list', 'kwlist'):
                opts[snam] = []

        def atswitch(t, o):
            # check if we are at a recognized switch.  if not
            # assume the data is part of regular arguments.
            if not text.startswith('-', o):
                return None, o

            name, x = s_syntax.meh(t, o, s_syntax.whites)
            swit = switches.get(name)
            if swit is None:
                return None, o

            return swit, x

        while off < len(text):

            _, off = s_syntax.nom(text, off, s_syntax.whites)

            swit, off = atswitch(text, off)
            if swit is not None:

                styp = swit[1].get('type', 'flag')
                snam = swit[0].strip('-')

                if styp == 'valu':
                    valu, off = s_syntax.parse_cmd_string(text, off)
                    opts[snam] = valu

                elif styp == 'list':
                    valu, off = s_syntax.parse_cmd_string(text, off)
                    if not isinstance(valu, list):
                        valu = valu.split(',')
                    opts[snam].extend(valu)

                elif styp == 'enum':
                    vals = synt[1].get('enum:vals')
                    valu, off = s_syntax.parse_cmd_string(text, off)
                    if valu not in vals:
                        raise s_common.BadSyntaxError('%s (%s)' % (synt[0], '|'.join(vals)))

                    opts[snam] = valu

                else:
                    opts[snam] = True

                continue

            if not args:
                raise s_common.BadSyntaxError('trailing text: %s' % (text[off:],))

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
                    item, off = s_syntax.parse_cmd_string(text, off)
                    valu.append(item)

                opts[synt[0]] = valu
                break

            if styp == 'kwlist':
                kwlist, off = s_syntax.parse_cmd_kwlist(text, off)
                opts[snam] = kwlist
                break

            valu, off = s_syntax.parse_cmd_string(text, off)
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

    def printf(self, mesg, addnl=True):
        return self._cmd_cli.printf(mesg, addnl=addnl)

class Cli(s_eventbus.EventBus):
    '''
    A modular / event-driven CLI base object.
    '''
    def __init__(self, item, outp=None, **locs):
        s_eventbus.EventBus.__init__(self)

        if outp is None:
            outp = s_output.OutPut()

        self.outp = outp
        self.locs = locs
        self.item = item    # whatever object we are commanding

        self.cmds = {}
        self.cmdprompt = 'cli> '

        self.addCmdClass(CmdHelp)
        self.addCmdClass(CmdQuit)
        self.addCmdClass(CmdLocals)

    def reflectItem(self):
        refl = s_reflect.getItemInfo(self.item)
        if refl is None:
            return

        for name in refl.get('inherits', ()):
            for mixi in s_mixins.getSynMixins('cmdr', name):
                self.addCmdClass(mixi)

    def get(self, name, defval=None):
        return self.locs.get(name, defval)

    def set(self, name, valu):
        self.locs[name] = valu

    def get_input(self, prompt=None):
        '''
        Get the input string to parse.

        Args:
            prompt (str): Optional string to use as the prompt. Otherwise self.cmdprompt is used.

        Returns:
            str: A string to process.
        '''
        if not prompt:
            prompt = self.cmdprompt

        self.fire('cli:getinput')
        return get_input(prompt)

    def printf(self, mesg, addnl=True):
        return self.outp.printf(mesg, addnl=addnl)

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

    def runCmdLoop(self):
        '''
        Run commands from a user in an interactive fashion until fini() or EOFError is raised.
        '''
        import readline
        readline.read_init_file()

        while not self.isfini:

            # FIXME history / completion

            try:

                line = self.get_input()
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                self.runCmdLine(line)

            except KeyboardInterrupt as e:
                self.printf('<ctrl-c>')

            except (s_common.CliFini, EOFError) as e:
                self.fini()

            except Exception as e:
                s = traceback.format_exc()
                self.printf(s)

    def runCmdLine(self, line):
        '''
        Run a single command line.

        Args:
            line (str): Line to execute.

        Examples:
            Execute the 'woot' command with the 'help' switch:

                cli.runCmdLine('woot --help')

        Returns:
            object: Arbitrary data from the cmd class.
        '''
        ret = None

        name = line.split(None, 1)[0]

        cmdo = self.getCmdByName(name)
        if cmdo is None:
            self.printf('cmd not found: %s' % (name,))
            return

        self.fire('cli:cmd:run', line=line)

        try:

            ret = cmdo.runCmdLine(line)

        except s_common.CliFini as e:
            self.fini()

        except KeyboardInterrupt as e:
            self.printf('<ctrl-c>')

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

    def runCmdOpts(self, opts):
        self.printf('o/')
        raise s_common.CliFini()

class CmdHelp(Cmd):
    '''
    List commands and display help output.

    Example:

        help foocmd

    '''
    _cmd_name = 'help'
    _cmd_syntax = [
        ('cmds', {'type': 'list'})
    ]

    def runCmdOpts(self, opts):
        cmds = opts.get('cmds')

        # if they didn't specify one, just show the list
        if not cmds:
            cmds = self._cmd_cli.getCmdNames()
            cmds.sort()

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
    List the current locals for a given CLI object
    '''
    _cmd_name = 'locs'

    def runCmdOpts(self, opts):
        ret = {}
        for k, v in self._cmd_cli.locs.items():
            ret[k] = repr(v)
        mesg = json.dumps(ret, indent=2, sort_keys=True)
        self.printf(mesg)
