import sys
import shlex
import argparse
import traceback

from synapse.eventbus import EventBus

class CmdArgErr(Exception):

    def __init__(self, pars, msg):
        self.msg = msg
        self.pars = pars
        Exception.__init__(self, msg)

# fucking argparse....
class CmdArgExit(Exception):pass

class ArgumentParser(argparse.ArgumentParser):

    def error(self, msg):
        # fuck argparse and it's thinking it should unilaterally exit()
        raise CmdArgErr(self,msg)

    def exit(self, *args, **kwargs):
        raise CmdArgExit()

class CliFini(Exception): pass

class Cli(EventBus):
    '''
    A modular / event-driven CLI object similar to cmd.Cmd (but not lame)

    Example:

        import synapse.lib.cli as s_cli

        class WootCli(s_cli.Cli):

            def cmd_woot(self, cli, line):
                """
                The woot command.
                """
                # using CLI rather than self allows cli "federation"
                cli.vprint('woot!')

        wootcli = WootCli()

        # can also dynamically register commands...

        def lulz(cli,line):
            """
            Lulz the live long day.
            """
            stuff()

        wootcli.addCmdFunc(lulz)

        # or methods from other objects...

        class Foo:
            def cmd_bar(self, cli, line):

        foo = Foo()
        cli.addCmdMeths(foo)

        # cli now has "bar" command

    '''

    def __init__(self):
        #cmd.Cmd.__init__(self)
        EventBus.__init__(self)

        self.cmdfuncs = {}
        self.cmdprompt = 'cli> '

        self.addCmdMeths(self)
        self.addCmdFunc(cmd_quit, name='quit')
        self.addCmdFunc(cmd_help, name='help')

    def getCmdNames(self):
        '''
        Return a list of all the known command names for the CLI.
        '''
        return list(self.cmdfuncs.keys())

    def delCmdFunc(self, name):
        '''
        Remove a previously registered command function.
        '''
        return self.cmdfuncs.pop(name,None)

    def getCmdDoc(self, name):
        '''
        Return the doc string for the given function name.
        '''
        func = self.getCmdFunc(name)
        if func == None:
            return None

        return func.__doc__

    def getCmdBrief(self, name):
        '''
        Return the strip()d first line from the cmd doc string.
        '''
        doc = self.getCmdDoc(name)
        if doc == None:
            return None

        return doc.strip().split('\n',1)[0].strip()

    def getCmdFunc(self, name):
        '''
        Return the func callback for a given command.
        '''
        return self.cmdfuncs.get(name)

    def addStdPrint(self):
        '''
        Add a callback to print cli:print events to stdout.
        '''
        self.on('cli:print', _cliprint)

    def addCmdFunc(self, func, name=None):
        '''
        Add an additional command callback to the CLI object.

        def woot(cli,line):
            do_woot_stuff(line)

        cli.addCmdFunc('woot', woot)

        # cli now has "woot" command

        '''
        if name == None:
            name = func.__name__

        self.cmdfuncs[name] = func

    def _printCliExc(self, exc):
        exctxt = traceback.format_exc()
        self.vprint(exctxt)
        self.vprint('error: %s' % exc)

    def getArgParser(self, prog):
        '''
        Return a synapse ArgumentParser instance.

        Example:

            pars = cli.getArgParser()

        Notes:

            * our ArgumentParser subclass doesnt exit()

        '''
        return ArgumentParser(prog=prog)

    def vprint(self, msg, addnl=True):
        '''
        Print output for the CLI.
        '''
        self.fire('cli:print', msg=msg, addnl=addnl)

    def getLineArgv(self, line):
        '''
        Chop up an input line and return argv list.

        Example:

            argv = cli.getLineArgv(line)

        '''
        return shlex.split(line)[1:]

    def addCmdMeths(self, item):
        '''
        Add all cmd_<foo> methods from the given item as commands.

        Example:

            import synapse.lib.cli as s_cli

            class Lulz:

                def cmd_woot(self, cli, line):
                    cli.vprint('woot: %s' % (line,))

            lulz = Lulz()

            cli = s_cli.Cli()
            cli.addCmdMeths(lulz)

            # cli now has command named "woot"

        '''
        for name in dir(item):

            if not name.startswith('cmd_'):
                continue

            meth = getattr(item,name,None)
            if not meth:
                continue

            self.addCmdFunc(meth, name=name[4:])

    def runCmdLoop(self, stdin=sys.stdin):
        '''
        Run commands from stdin until close or fini().
        '''

        while not self.isfini:

            # if our stdin closes, return from runCmdLoop

            # FIXME raw_input
            # FIXME history / completion

            try:

                self.vprint( self.cmdprompt, addnl=False )

                line = input()
                #line = stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    self.vprint('FIXME EMPTY')
                    continue

                self.runCmdLine(line)

            except KeyboardInterrupt as e:
                self.vprint('<ctrl-c>')

            except Exception as e:
                traceback.print_exc()

    def runCmdLine(self, line):
        '''
        Run a single command line.

        Example:

            cli.runCmdLine('woot --help')

        '''
        ret = None
        name = line.split(None,1)[0]
        func = self.getCmdFunc(name)

        # FIXME partial match!
        if func == None:
            self.vprint('cmd not found: %s' % (name,))
            return

        self.fire('cli:cmd:run', line=line)

        try:

            ret = func(self,line)

        except CliFini as e:
            self.fini()

        except KeyboardInterrupt as e:
            self.vprint('<ctrl-c>')

        except CmdArgErr as e:
            self.vprint( e.pars.format_usage() )
            self.vprint( e.msg )

        except CmdArgExit as e:
            pass

        except Exception as e:
            self._printCliExc(e)

        self.fire('cli:cmd:ret', line=line, ret=ret)

        return ret

def _cliprint(mesg):
    '''
    Callback for printing cli:print events.
    '''
    msg = mesg[1].get('msg')

    addnl = mesg[1].get('addnl')
    if addnl:
        msg += '\n'

    sys.stdout.write(msg)
    sys.stdout.flush()

def cmd_quit(cli, line):
    '''
    Quit the CLI.
    '''
    cli.fini()
    raise CliFini()

def cmd_help(cli, line):
    '''
    Show command list and descriptions.
    '''
    argv = cli.getLineArgv(line)
    if argv:

        for name in argv:
            cli.vprint('=== %s' % (name,))

            doc = cli.getCmdDoc(name)
            if doc != None:
                cli.vprint(doc)

            cli.runCmdLine('%s --help' % name)

        return

    names = cli.getCmdNames()

    names.sort()
    padsize = max( [ len(n) for n in names ] )

    for name in names:
        brief = cli.getCmdBrief(name)
        padname = name.ljust(padsize)
        cli.vprint('%s - %s' % (padname,brief))

    cli.vprint('(%d cmds)' % (len(names),))

