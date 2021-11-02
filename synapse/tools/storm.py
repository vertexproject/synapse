import os
import sys
import copy
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cli as s_cli
import synapse.lib.cmd as s_cmd
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.output as s_output
import synapse.lib.parser as s_parser
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

ERROR_COLOR = '#ff0066'
WARNING_COLOR = '#f4e842'
NODEEDIT_COLOR = "lightblue"

welcome = '''
Welcome to the Storm interpreter!

Local interpreter (non-storm) commands may be executed with a ! prefix:
    Use !quit to exit.
    Use !help to see local interpreter commands.
'''
class QuitCmd(s_cli.CmdQuit):
    '''
    Quit the current command line interpreter.

    Example:

        !quit
    '''
    _cmd_name = '!quit'

class HelpCmd(s_cli.CmdHelp):
    '''
    List interpreter extended commands and display help output.

    Example:

        !help foocmd
    '''
    _cmd_name = '!help'

class StormCliCmd(s_cli.Cmd):

    # cut the Cmd instance over to using argparser and cmdrargv split

    def getArgParser(self):
        desc = self.getCmdDoc()
        pars = s_cmd.Parser(prog=self._cmd_name, description=desc, outp=self._cmd_cli.outp)
        return pars

    def getCmdOpts(self, text):
        pars = self.getArgParser()
        argv = s_parser.Parser(text).cmdrargs()
        return pars.parse_args(argv[1:])

class RunFileCmd(StormCliCmd):
    '''
    Run a local storm file.

    Example:

        !runfile /path/to/file.storm
    '''

    _cmd_name = '!runfile'

    def getArgParser(self):
        pars = StormCliCmd.getArgParser(self)
        pars.add_argument('stormfile', help='A local file containing a storm query.')
        return pars

    async def runCmdOpts(self, opts):

        if not os.path.isfile(opts.stormfile):
            self.printf(f'no such file: {opts.stormfile}')
            return

        with open(opts.stormfile, 'rb') as fd:
            text = fd.read().decode()

        self.printf(f'running storm file: {opts.stormfile}')
        await self._cmd_cli.storm(text)

class PushFileCmd(StormCliCmd):
    '''
    Upload a file and create a file:bytes node.

    Example:

        !pushfile /path/to/file
    '''

    _cmd_name = '!pushfile'

    def getArgParser(self):
        pars = StormCliCmd.getArgParser(self)
        pars.add_argument('filepath', help='A local file to push to the Cortex.')
        return pars

    async def runCmdOpts(self, opts):

        if not os.path.isfile(opts.filepath):
            self.printf(f'no such file: {opts.filepath}')
            return

        self.printf(f'uploading file: {opts.filepath}')
        async with await self._cmd_cli.item.getAxonUpload() as upload:

            with open(opts.filepath, 'rb') as fd:

                byts = fd.read(10000000)
                while byts:
                    await upload.write(byts)
                    byts = fd.read(10000000)

            size, sha256 = await upload.save()

        opts = {'vars': {
            'sha256': s_common.ehex(sha256),
            'name': os.path.basename(opts.filepath),
        }}

        await self._cmd_cli.storm('[ file:bytes=$sha256 ] { -:name [:name=$name] }', opts=opts)

class PullFileCmd(StormCliCmd):
    '''
    Download a file by sha256 and store it locally.

    Example:

        !pullfile c00adfcc316f8b00772cdbce2505b9ea539d74f42861801eceb1017a44344ed3 /path/to/savefile
    '''

    _cmd_name = '!pullfile'

    def getArgParser(self):
        pars = StormCliCmd.getArgParser(self)
        pars.add_argument('sha256', help='The SHA256 of the file to download.')
        pars.add_argument('filepath', help='The file path to save the downloaded file to.')
        return pars

    async def runCmdOpts(self, opts):

        self.printf(f'downloading sha256: {opts.sha256}')

        try:
            with s_common.genfile(opts.filepath) as fd:
                async for byts in self._cmd_cli.item.getAxonBytes(opts.sha256):
                    byts = fd.write(byts)

            self.printf(f'saved to: {opts.filepath}')

        except asyncio.CancelledError as e:
            raise

        except s_exc.SynErr as e:
            self.printf(e.errinfo.get('mesg', str(e)))

class ExportCmd(StormCliCmd):
    '''
    Export the results of a storm query into a nodes file.

    Example:

        // Export nodes to a file
        !export dnsa.nodes { inet:fqdn#mynodes -> inet:dns:a }

        // Export nodes to a file and only include specific tags
        !export fqdn.nodes { inet:fqdn#mynodes } --include-tags footag
    '''

    _cmd_name = '!export'

    def getArgParser(self):
        pars = StormCliCmd.getArgParser(self)
        pars.add_argument('filepath', help='The file path to save the export to.')
        pars.add_argument('query', help='The Storm query to export nodes from.')
        pars.add_argument('--include-tags', nargs='*', help='Only include the specified tags in output.')
        pars.add_argument('--no-tags', default=False, action='store_true', help='Do not include any tags on exported nodes.')
        return pars

    async def runCmdOpts(self, opts):

        self.printf(f'exporting nodes')

        queryopts = {}
        if opts.include_tags:
            queryopts['scrub'] = {'include': {'tags': opts.include_tags}}

        if opts.no_tags:
            queryopts['scrub'] = {'include': {'tags': []}}

        try:
            query = opts.query[1:-1]
            with s_common.genfile(opts.filepath) as fd:
                cnt = 0
                async for pode in self._cmd_cli.item.exportStorm(query, opts=queryopts):
                    byts = fd.write(s_msgpack.en(pode))
                    cnt += 1

            self.printf(f'saved {cnt} nodes to: {opts.filepath}')

        except asyncio.CancelledError as e:
            raise

        except s_exc.SynErr as e:
            self.printf(e.errinfo.get('mesg', str(e)))

class StormCli(s_cli.Cli):

    histfile = 'storm_history'

    async def __anit__(self, item, outp=s_output.stdout, opts=None):

        await s_cli.Cli.__anit__(self, item, outp=outp)

        self.indented = False
        self.cmdprompt = 'storm> '

        self.stormopts = {'repr': True}
        self.hidetags = False
        self.hideprops = False
        self._print_skips = []

    def initCmdClasses(self):
        self.addCmdClass(QuitCmd)
        self.addCmdClass(HelpCmd)
        self.addCmdClass(ExportCmd)
        self.addCmdClass(RunFileCmd)
        self.addCmdClass(PullFileCmd)
        self.addCmdClass(PushFileCmd)

    def printf(self, mesg, addnl=True, color=None):
        if self.indented:
            s_cli.Cli.printf(self, '')
            self.indented = False
        return s_cli.Cli.printf(self, mesg, addnl=addnl, color=color)

    async def runCmdLine(self, line, opts=None):

        if line[0] == '!':
            return await s_cli.Cli.runCmdLine(self, line)

        await self.storm(line, opts=opts)

    async def handleErr(self, mesg):
        err = mesg[1]
        if err[0] == 'BadSyntax':
            pos = err[1].get('at', None)
            text = err[1].get('text', None)
            tlen = len(text)
            mesg = err[1].get('mesg', None)
            if pos is not None and text is not None and mesg is not None:
                text = text.replace('\n', ' ')
                # Handle too-long text
                if tlen > 60:
                    text = text[max(0, pos - 30):pos + 30]
                    if pos < tlen - 30:
                        text += '...'
                    if pos > 30:
                        text = '...' + text
                        pos = 33

                self.printf(text)
                self.printf(f'{" " * pos}^')
                self.printf(f'Syntax Error: {mesg}', color=ERROR_COLOR)
                return

        text = err[1].get('mesg', err[0])
        self.printf(f'ERROR: {text}', color=ERROR_COLOR)

    def _printNodeProp(self, name, valu):
        self.printf(f'        {name} = {valu}')

    async def storm(self, text, opts=None):

        realopts = copy.deepcopy(self.stormopts)
        if opts is not None:
            realopts.update(opts)

        async for mesg in self.item.storm(text, opts=realopts):

            mtyp = mesg[0]

            if mtyp in self._print_skips:
                continue

            if mtyp == 'node':

                node = mesg[1]
                formname, formvalu = s_node.reprNdef(node)

                self.printf(f'{formname}={formvalu}')

                if not self.hideprops:

                    props = []
                    extns = []
                    univs = []

                    for name in s_node.props(node).keys():

                        if name.startswith('.'):
                            univs.append(name)
                            continue

                        if name.startswith('_'):
                            extns.append(name)
                            continue

                        props.append(name)

                    props.sort()
                    extns.sort()
                    univs.sort()

                    for name in props:
                        valu = s_node.reprProp(node, name)
                        name = ':' + name
                        self._printNodeProp(name, valu)

                    for name in extns:
                        valu = s_node.reprProp(node, name)
                        name = ':' + name
                        self._printNodeProp(name, valu)

                    for name in univs:
                        valu = s_node.reprProp(node, name)
                        self._printNodeProp(name, valu)

                if not self.hidetags:

                    for tag in sorted(s_node.tagsnice(node)):

                        valu = s_node.reprTag(node, tag)
                        tprops = s_node.reprTagProps(node, tag)
                        printed = False
                        if valu:
                            self.printf(f'        #{tag} = {valu}')
                            printed = True

                        if tprops:
                            for prop, pval in tprops:
                                self.printf(f'        #{tag}:{prop} = {pval}')
                            printed = True

                        if not printed:
                            self.printf(f'        #{tag}')

            elif mtyp == 'node:edits':
                edit = mesg[1]
                count = sum(len(e[2]) for e in edit.get('edits', ()))
                s_cli.Cli.printf(self, '.' * count, addnl=False, color=NODEEDIT_COLOR)
                self.indented = True

            elif mtyp == 'fini':
                took = mesg[1].get('took')
                took = max(took, 1)
                count = mesg[1].get('count')
                pers = float(count) / float(took / 1000)
                self.printf('complete. %d nodes in %d ms (%d/sec).' % (count, took, pers))

            elif mtyp == 'print':
                self.printf(mesg[1].get('mesg'))

            elif mtyp == 'warn':
                info = mesg[1]
                warn = info.pop('mesg', '')
                xtra = ', '.join([f'{k}={v}' for k, v in info.items()])
                if xtra:
                    warn = ' '.join([warn, xtra])
                self.printf(f'WARNING: {warn}', color=WARNING_COLOR)

            elif mtyp == 'err':
                await self.handleErr(mesg)

def getArgParser():
    pars = argparse.ArgumentParser(prog='synapse.tools.storm')
    pars.add_argument('cortex', help='A telepath URL for the Cortex.')
    pars.add_argument('onecmd', nargs='?', help='A single storm command to run and exit.')
    return pars

async def main(argv, outp=s_output.stdout):

    pars = getArgParser()
    opts = pars.parse_args(argv)

    path = s_common.getSynPath('telepath.yaml')
    telefini = await s_telepath.loadTeleEnv(path)

    async with await s_telepath.openurl(opts.cortex) as proxy:

        if telefini is not None:
            proxy.onfini(telefini)

        async with await StormCli.anit(proxy, outp=outp, opts=opts) as cli:

            if opts.onecmd:
                await cli.runCmdLine(opts.onecmd)
                return

            # pragma: no cover
            cli.colorsenabled = True
            cli.printf(welcome)

            await cli.addSignalHandlers()
            await cli.runCmdLoop()

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
