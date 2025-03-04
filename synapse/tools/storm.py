import os
import sys
import copy
import asyncio
import logging
import argparse

import regex
import prompt_toolkit

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cli as s_cli
import synapse.lib.cmd as s_cmd
import synapse.lib.node as s_node
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

Use the <Tab> key for suggestion/completion of forms, commands, and tags.
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
            return False

        with open(opts.stormfile, 'rb') as fd:
            text = fd.read().decode()

        self.printf(f'running storm file: {opts.stormfile}')
        return await self._cmd_cli.storm(text)

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
            return False

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

        return await self._cmd_cli.storm('[ file:bytes=$sha256 ] { -:name [:name=$name] }', opts=opts)

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
            return False

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

        queryopts = copy.deepcopy(self._cmd_cli.stormopts)
        if opts.include_tags:
            queryopts['scrub'] = {'include': {'tags': opts.include_tags}}

        if opts.no_tags:
            queryopts['scrub'] = {'include': {'tags': []}}

        try:
            with s_common.genfile(opts.filepath) as fd:
                cnt = 0
                async for pode in self._cmd_cli.item.exportStorm(opts.query, opts=queryopts):
                    byts = fd.write(s_msgpack.en(pode))
                    cnt += 1

            self.printf(f'saved {cnt} nodes to: {opts.filepath}')

        except asyncio.CancelledError as e:
            raise

        except s_exc.SynErr as e:
            self.printf(e.errinfo.get('mesg', str(e)))
            return False

def cmplgenr(*genrs, prefix=''):
    '''
    Iterate over all the generators/iterators passed in as args and return Completions from them.
    If prefix is specified, make sure the current item in the generator starts with the prefix value.
    '''
    for genr in genrs:
        for (valu, display) in genr:
            if prefix and not valu.startswith(prefix):
                continue

            completion = prompt_toolkit.completion.Completion(
                valu[len(prefix):],
                display=display
            )

            yield completion

tagre = regex.compile(r'#(\w+[\w\.]*)$')
libre = regex.compile(r'\$([a-z_][a-zA-Z0-9_\.]*)$')
cmdpropre = regex.compile(r'([a-z_][a-z0-9_]+[a-z0-9_:\.]+)$')

class StormCompleter(prompt_toolkit.completion.Completer):
    def __init__(self, cli):
        self._cli = cli

        self.initialized = False

        # These are all the possible completions. Their format should be as follows:
        # (<name>, <display>)

        # ('misp.event.add', '[cmd] misp.event.add - Add Synapse nodes to a MISP server.')
        self._cmds = []

        # ('lib.cast', '[lib] $lib.cast(name: str, valu: any) - Normalize a value as a Synapse Data Model Type.')
        # ('lib.debug', '[lib] $lib.debug - True if the current runtime has debugging enabled.')
        self._libs = []

        # ('inet:fqdn', '[form] inet:fqdn - A Fully Qualified Domain Name (FQDN).')
        # ('inet:fqdn:domain', '[prop] inet:fqdn:domain - The parent domain for the FQDN.')
        self._forms = []
        self._props = []

    async def load(self):
        info = await self._cli.item.getCoreInfoV2()
        types = info['modeldict']['types']

        # Process forms/props
        for form in info['modeldict']['forms'].values():
            formname = form['name']
            formdoc = ''

            formtype = types.get(formname)
            if formtype:
                forminfo = formtype.get('info')
                if forminfo:
                    formdoc = forminfo.get('doc')

            if formdoc:
                formdoc = f' - {formdoc}'

            self._forms.append((formname, f'[form] {formname}{formdoc}'))

            for prop in form['props'].values():
                propname = prop['name']
                if not propname.startswith('.'):
                    propname = f':{propname}'

                propdoc = prop.get('doc', '')
                if propdoc:
                    propdoc = f' - {propdoc}'

                self._props.append((f'{formname}{propname}', f'[prop] {formname}{propname}{propdoc}'))

        # Process cmds
        commands = info['stormdocs'].get('commands', ())
        for command in commands:
            name = command['name']
            doc = command['doc']
            if doc:
                doc = f' - {doc}'
            self._cmds.append((name, f'[cmd] {name}{doc}'))

        # Process libs
        libraries = info['stormdocs']['libraries']
        for library in libraries:
            basename = '.'.join(library['path'])

            for local in library['locals']:
                libname = '.'.join((basename, local['name']))
                name = libname
                desc = local['desc'].strip().split('\n')[0]
                libtype = local['type']
                if isinstance(libtype, dict) and local['type']['type'] == 'function':
                    args = local['type'].get('args')
                    if args:
                        params = []
                        for arg in args:
                            argname = arg['name']
                            argtype = arg['type']

                            params.append(f'{argname}: {argtype}')

                        params = ', '.join(params)
                        name = f'{name}({params})'
                    else:
                        name = f'{name}()'

                self._libs.append((libname, f'[lib] ${name} - {desc}'))

        self._forms.sort(key=lambda x: x[0])
        self._props.sort(key=lambda x: x[0])
        self._cmds.sort(key=lambda x: x[0])
        self._libs.sort(key=lambda x: x[0])

        self.initialized = True

    async def _get_tag_completions(self, prefix='', limit=100):
        if not prefix:
            depth = 1
        else:
            depth = prefix.count('.') + 1

        q = '''
        $rslt = ()
        if ($prefix != '') { syn:tag=$lib.regex.replace("\\.$", '', $prefix) }
        syn:tag^=$prefix
        +:depth<=$depth
        | uniq
        | limit $limit
        | $doc = ''
        if $node.props.doc {
            $doc = ` - {$node.props.doc}`
        }
        $rslt.append(($node.value(), `[tag] {$node.value()}{$doc}`))
        | spin
        | return($rslt)
        '''
        opts = {'vars': {'prefix': prefix, 'limit': limit, 'depth': depth}}
        view = self._cli.stormopts.get('view')
        if view:
            opts['view'] = view
        return await self._cli.item.callStorm(q, opts=opts)

    def get_completions(self, document, complete_event):  # pragma: no cover
        # This is the sync version of this method (vs get_completions_async()
        # below). We don't need the sync version but the base class has this
        # decorated as an abstract method so it needs to be configured. Do nothing.
        pass

    async def _get_completions_async(self, document, complete_event):
        # Note: Be careful when changing the order of matching in this function.
        text = document.text.strip()

        # If the last character is a hash, suggest tags
        if text[-1] == '#':
            return cmplgenr(await self._get_tag_completions())

        # Try to match partial tags
        match = tagre.search(text)
        if match:
            tag = match.group(1)
            return cmplgenr(await self._get_tag_completions(tag), prefix=tag)

        # Try to match partial libs
        match = libre.search(text)
        if match:
            name = match.group(1)
            if name.startswith('lib'):
                return cmplgenr(self._libs, prefix=name)
            else:
                # Nothing else below starts with $ so return
                return

        # Match on potential commands and props
        match = cmdpropre.search(text)
        if match:
            valu = match.group(1)
            if ':' in valu:
                return cmplgenr(self._forms, self._props, prefix=valu)

            return cmplgenr(self._cmds, self._forms, self._props, prefix=valu)

    async def get_completions_async(self, document, complete_event):
        # Only complete on TAB and if there is input
        if not complete_event.completion_requested or not document.text or not document.text.strip():
            return

        # Initialize completions
        if not self.initialized:
            await self.load()
            self.initialized = True

        completions = await self._get_completions_async(document, complete_event)
        if not completions:
            return

        for item in completions:
            yield item

class StormCli(s_cli.Cli):

    histfile = 'storm_history'

    async def __anit__(self, item, outp=s_output.stdout, opts=None):

        await s_cli.Cli.__anit__(self, item, outp=outp)

        self.indented = False
        self.cmdprompt = 'storm> '

        self.stormopts = {'repr': True}

        if opts is not None:

            if opts.optsfile is not None:

                stormopts = s_common.yamlload(opts.optsfile)
                if stormopts is None:
                    mesg = f'The --optsfile {opts.optsfile} does not exist.'
                    raise s_exc.NoSuchFile(mesg=mesg)

                self.stormopts.update(stormopts)

            if opts.view:
                self.stormopts['view'] = opts.view

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
        if self.echoline:
            self.outp.printf(f'{self.cmdprompt}{line}')

        if line[0] == '!':
            return await s_cli.Cli.runCmdLine(self, line)

        return await self.storm(line, opts=opts)

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

        ret = True
        realopts = copy.deepcopy(self.stormopts)
        if opts is not None:
            realopts.update(opts)

        async for mesg in self.item.storm(text, opts=realopts):

            await self.fire('storm:mesg', mesg=mesg)

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
                ret = False

        return ret

def getArgParser():
    pars = argparse.ArgumentParser(prog='synapse.tools.storm')
    pars.add_argument('cortex', help='A telepath URL for the Cortex.')
    pars.add_argument('onecmd', nargs='?', help='A single storm command to run and exit.')
    pars.add_argument('--view', default=None, help='The view iden to work in.')
    pars.add_argument('--optsfile', default=None, help='A JSON/YAML file which contains storm runtime options.')
    return pars

async def main(argv, outp=s_output.stdout):

    pars = getArgParser()
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.cortex) as proxy:

            async with await StormCli.anit(proxy, outp=outp, opts=opts) as cli:

                if opts.onecmd:
                    if await cli.runCmdLine(opts.onecmd) is False:
                        return 1
                    return 0

                else:  # pragma: no cover

                    completer = StormCompleter(cli)
                    cli.completer = completer
                    await completer.load()

                    cli.colorsenabled = True
                    cli.printf(welcome)

                    await cli.addSignalHandlers()
                    await cli.runCmdLoop()

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
