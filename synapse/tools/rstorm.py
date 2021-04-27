import sys
import copy
import json
import pprint
import asyncio
import argparse

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.stormhttp as s_stormhttp

import synapse.cmds.cortex as s_cmds_cortex

import synapse.tools.genpkg as s_genpkg

async def cortex():
    base = await s_base.Base.anit()
    dirn = await base.enter_context(s_common.getTempDir())
    core = await s_cortex.Cortex.anit(dirn)
    core.onfini(base.fini)
    return core

class StormOutput(s_cmds_cortex.StormCmd):
    '''
    Produce standard output from a stream of storm runtime messages.
    Must be instantiated for a single query with a rstorm context.
    '''
    # TODO: Eventually make this obey all cmdr options and swap it in

    def __init__(self, core, ctx, stormopts=None, opts=None):
        if opts is None:
            opts = {}

        s_cmds_cortex.StormCmd.__init__(self, None, **opts)

        self.stormopts = stormopts or {}

        # hide a few mesg types by default
        for mtype in ('init', 'fini', 'node:edits', 'node:edits:count', 'prov:new'):
            self.cmdmeths[mtype] = self._silence

        self.core = core
        self.ctx = ctx
        self.lines = []

    async def runCmdLine(self, line):
        opts = self.getCmdOpts(f'storm {line}')
        self.printf(f'> {opts.get("query")}')
        return await self.runCmdOpts(opts)

    async def _mockHttp(self, *args, **kwargs):
        info = {
            'code': 200,
            'body': '{}',
        }

        resp = self.ctx.get('mock-http')
        if resp:
            body = resp.get('body')

            if isinstance(body, dict):
                body = json.dumps(body)

            info = {
                'code': resp.get('code', 200),
                'body': body,
            }

        return s_stormhttp.HttpResp(info)

    def printf(self, mesg, addnl=True, color=None):
        line = f'    {mesg}'
        self.lines.append(line)
        return line

    def _silence(self, mesg, opts):
        pass

    def _onErr(self, mesg, opts):
        # raise on err for rst
        raise s_exc.StormRuntimeError(mesg=mesg)

    async def runCmdOpts(self, opts):

        text = opts.get('query')

        stormopts = copy.deepcopy(self.stormopts)

        stormopts.setdefault('repr', True)
        stormopts.setdefault('path', opts.get('path', False))

        hide_unknown = True

        showtext = opts.get('show')
        if showtext is not None:
            stormopts['show'] = showtext.split(',')

        editformat = opts['editformat']
        if editformat != 'nodeedits':
            stormopts['editformat'] = editformat

        # Let this raise on any errors
        with mock.patch('synapse.lib.stormhttp.LibHttp._httpRequest', new=self._mockHttp):
            async for mesg in self.core.storm(text, opts=self.stormopts):

                if opts.get('debug'):
                    self.printf(pprint.pformat(mesg))
                    continue

                try:
                    func = self.cmdmeths[mesg[0]]
                except KeyError:
                    if hide_unknown:
                        continue
                    self.printf(repr(mesg), color=s_cmds_cortex.UNKNOWN_COLOR)
                else:
                    func(mesg, opts)

        return '\n'.join(self.lines)


async def genStormRst(path, debug=False):

    outp = []
    context = {}

    with open(path, 'r') as fd:
        lines = fd.readlines()

    for line in lines:

        if line.startswith('.. storm-cortex::'):
            ctor = line.split('::', 1)[1].strip()
            core = await (s_dyndeps.getDynLocal(ctor))()
            if context.get('cortex') is not None:
                await (context.pop('cortex')).fini()
            context['cortex'] = core
            continue

        if line.startswith('.. storm-opts::'):
            item = json.loads(line.split('::', 1)[1].strip())
            context['storm-opts'] = item
            continue

        if line.startswith('.. storm-expect::'):
            # TODO handle some light weight output confirmation.
            continue

        if line.startswith('.. storm-pre::'):
            # runt a storm query to prepare the cortex (do not output)

            text = line.split('::', 1)[1].strip()

            core = context.get('cortex')
            if core is None:
                mesg = 'No cortex set.  Use .. storm-cortex::'
                raise s_exc.NoSuchVar(mesg=mesg)

            soutp = StormOutput(core, context, stormopts=context.get('storm-opts'))
            await soutp.runCmdLine(text)
            continue

        if line.startswith('.. storm-pkg::'):
            # load a package into the cortex from a directory

            yamlpath = line.split('::', 1)[1].strip()

            core = context.get('cortex')
            if core is None:
                mesg = 'No cortex set.  Use .. storm-cortex::'
                raise s_exc.NoSuchVar(mesg=mesg)

            pkg = s_genpkg.loadPkgProto(yamlpath)
            await core.addStormPkg(pkg)
            continue

        if line.startswith('.. storm-mock-http::'):
            # setup a mock to use with a later storm command
            jsonpath = line.split('::', 1)[1].strip()
            context['mock-http'] = s_common.jsload(jsonpath)
            continue

        if line.startswith('.. storm::'):

            text = line.split('::', 1)[1].strip()

            core = context.get('cortex')
            if core is None:
                mesg = 'No cortex set.  Use .. storm-cortex::'
                raise s_exc.NoSuchVar(mesg=mesg)

            outp.append('::\n')
            outp.append('\n')

            soutp = StormOutput(core, context, stormopts=context.get('storm-opts'))
            outp.extend(await soutp.runCmdLine(text))

            outp.append('\n\n')
            continue

        outp.append(line)

    core = context.get('cortex')
    if core is not None:
        await core.fini()

    return outp

prog = 'synapse.tools.rstorm'
descr = 'An RST pre-processor that allows you to embed storm directives.'

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog=prog, description=descr)
    pars.add_argument('rstfile', help='Input RST file with storm directives.')
    pars.add_argument('--save', help='Output file to save (default: stdout)')

    opts = pars.parse_args(argv)
    path = s_common.genpath(opts.rstfile)

    lines = await genStormRst(path)

    if opts.save:
        with open(s_common.genpath(opts.save), 'w') as fd:
            [fd.write(line) for line in lines]
    else:
        for line in lines:
            outp.printf(line, addnl=False)

if __name__ == '__main__':
    sys.exit(asyncio.run(main(sys.argv[1:])))
