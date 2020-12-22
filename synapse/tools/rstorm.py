import sys
import json
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

async def cortex():
    base = await s_base.Base.anit()
    dirn = await base.enter_context(s_common.getTempDir())
    core = await s_cortex.Cortex.anit(dirn)
    core.onfini(base.fini)
    return core

class StormOutput:
    '''
    Produce standard output from a stream of storm runtime messages.
    '''
    # TODO: Eventually make this obey all cmdr options and swap it in

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
            context['opts'] = item
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

            opts = context.get('opts')
            await core.callStorm(text, opts=opts)
            continue

        if line.startswith('.. storm::'):

            text = line.split('::', 1)[1].strip()

            core = context.get('cortex')
            if core is None:
                mesg = 'No cortex set.  Use .. storm-cortex::'
                raise s_exc.NoSuchVar(mesg=mesg)

            outp.append('::\n')
            outp.append('\n')

            outp.append(f'    > {text}\n')

            opts = context.get('opts')
            msgs = await core.stormlist(text, opts=opts)

            # TODO use StormOutput
            for mesg in await core.stormlist(text, opts=opts):

                if mesg[0] == 'print':
                    ptxt = mesg[1]['mesg']
                    outp.append(f'    {ptxt}\n')
                    continue

                if mesg[0] == 'warn':
                    ptxt = mesg[1]['mesg']
                    outp.append(f'    WARNING: {ptxt}\n')
                    continue

                if mesg[0] == 'err':
                    raise s_exc.StormRuntimeError(mesg=mesg)

            outp.append('\n')
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
