#import cmd
import os
import sys
import argparse
import collections

import synapse.glob as s_glob
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.output as s_output

import traceback

splicenames = set([
    'node:add',
    'node:del',
    'prop:set',
    'prop:del',
    'tag:add',
    'tag:del',
])

class Cmdr(s_eventbus.EventBus):

    def __init__(self, core, outp=s_output.stdout):

        s_eventbus.EventBus.__init__(self)

        self.core = core
        self.outp = outp

        self.show = {
            'debug': False,
            'splices': True,
            'unknowns': True,

            'node:tags': True,
            'node:props': True,
        }

        self.mbus = s_eventbus.EventBus()

        self.mbus.on('err', self._onMesgErr)
        self.mbus.on('node', self._onMesgNode)
        self.mbus.on('print', self._onMesgPrint)

        self.bangs = {}
        self.counters = collections.defaultdict(int)

        self.addBangCmd(HelpCmd)
        self.addBangCmd(QuitCmd)

        self.addBangCmd(ScriptCmd)

    def addBangCmd(self, ctor):
        self.bangs[ctor.name] = ctor

    def printf(self, text):
        self.outp.printf(text)

    def onecmd(self, text):

        if not text.startswith('!'):
            return self.runstorm(text)

        # check for "bare" command...

        line = ''
        parts = text[1:].split(None, 1)

        name = parts[0]

        if len(parts) == 2:
            line = parts[1]

        ctor = self.bangs.get(name)
        if ctor is not None:
            bcmd = ctor(self)
            return bcmd.run(line)

        # TODO: partial command detection
        self.printf(f'unknown local command: {name} (use !help to see a list)')

    def _onMesgNode(self, mesg):

        node = mesg[1]

        formname = node[0][0]
        formvalu = node[1].get('repr')
        if formvalu is None:
            formvalu = str(node[0][1])

        self.printf(f'{formname}={formvalu}')

        if self.show.get('node:props'):

            for name, valu in sorted(node[1]['props'].items()):

                valu = node[1]['reprs'].get(name, valu)

                if name[0] != '.':
                    name = ':' + name

                self.printf(f'        {name} = {valu}')

        if self.show.get('node:tags'):

            for tag in sorted(s_node.tags(node, leaf=True)):

                valu = node[1]['tags'].get(tag)
                if valu == (None, None):
                    self.printf(f'        #{tag}')
                    continue

                mint = s_time.repr(valu[0])
                maxt = s_time.repr(valu[1])
                self.printf(f'        #{tag} = ({mint}, {maxt})')

    def _onMesgPrint(self, mesg):
        self.printf(mesg[1].get('mesg', ''))

    def _onMesgErr(self, mesg):
        errx, einfo = mesg[1]
        self.printf('ERROR: %r (%r)' % (errx, einfo))

    def runstorm(self, line):

        self.counters.clear()

        opts = {'repr': True}
        for mesg in self.core.storm(line, opts=opts):
            self.counters[mesg[0]] += 1
            self.mbus.dist(mesg)

        self.printf('(%d nodes)' % (self.counters['node'],))

    def cmdloop(self):

        import readline

        try:
            readline.read_init_file()
        except OSError:
            # from cpython 3.6 site.py:
            # An OSError here could have many causes, but the most likely one
            # is that there's no .inputrc file (or .editrc file in the case of
            # Mac OS X + libedit) in the expected location.  In that case, we
            # want to ignore the exception.
            pass

        while not self.isfini:

            # FIXME history / completion

            try:
                task = None

                line = input('storm> ')
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                self.onecmd(line)

            except KeyboardInterrupt as e:
                self.printf('<ctrl-c>')
                self.fini()

            except EOFError as e:
                self.fini()

            except Exception as e:
                s = traceback.format_exc()
                self.printf(s)

class Cmd:

    def __init__(self, cmdr):
        self.cmdr = cmdr

    def parser(self):
        return s_cmd.Parser(prog='!' + self.name, description=self.brief, outp=self.cmdr.outp)

    def tokens(self, line):
        import shlex
        # TODO: merge in stormcmd() via syntax
        return shlex.split(line)

    def run(self, line):
        pars = self.parser()
        toks = self.tokens(line)

        opts = pars.parse_args(toks)
        if pars.exited:
            return

        return self.runopts(opts)

    def runopts(self, opts):
        raise s_exc.NoSuchImpl('runopts')

    def runhelp(self):
        return self.run('--help')

    def printf(self, mesg):
        self.cmdr.printf(mesg)

class QuitCmd(Cmd):

    name = 'quit'
    brief = 'Quit the storm interpreter.'

    def runopts(self, opts):
        self.cmdr.printf('o/')
        self.cmdr.fini()

class HelpCmd(Cmd):

    name = 'help'
    brief = 'List the local commands.'

    def parser(self):
        pars = Cmd.parser(self)
        pars.add_argument('cmdname', nargs='?', help='The command name to get detailed help.')
        return pars

    def runopts(self, opts):

        if opts.cmdname is None:
            self.printf('Local commands...')
            for name, ctor in sorted(self.cmdr.bangs.items()):
                self.printf(f'!{name} - {ctor.brief}')
            return

        ctor = self.cmdr.bangs.get(opts.cmdname)
        if ctor is None:
            self.printf('unknown command: {opts.cmdname}')
            return

        ctor(self.cmdr).runhelp()

#class LoadCsv(Cmd):

class ScriptCmd(Cmd):

    name = 'script'
    brief = 'Run a storm script from a local file.'

    def parser(self):
        pars = Cmd.parser(self)
        #pars.add_argument('--csvfile',
        #pars.add_argument('--jsonfile',
        pars.add_argument('filename', help='Storm script to execute.')
        return pars

    def runopts(self, opts):

        text = s_common.getbytes(opts.filename).decode('utf8')
        self.cmdr.runstorm(text)

banner = '''
Welcome to the cortex...

type "help" for storm commands.
type "!help" for local commands.

( and use !quit to exit )
'''

def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser()

    pars.add_argument('--onecmd', help='Issue a single storm command/query and exit.')
    pars.add_argument('--cortex', default='tcp://127.0.0.1:27492/cortex', help='A telepath URL to a remote cortex.')

    opts = pars.parse_args(argv)

    outp.printf('connecting to cortex: %r' % (opts.cortex,))

    try:

        with s_telepath.openurl(opts.cortex) as core:

            cmdr = Cmdr(core)
            if opts.onecmd:
                cmdr.onecmd(opts.onecmd)

            else:
                cmdr.printf(banner)
                cmdr.cmdloop()

    except Exception as e:
        outp.printf('ERROR: %s' % (e,))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
