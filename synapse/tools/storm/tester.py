import sys
import json
import shutil
import tempfile

import synapse.cortex as s_cortex

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

import synapse.tools.storm._printer as s_printer

desc = 'Run Storm queries against a local Cortex.'

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.tester', outp=outp, description=desc)
    pars.add_argument('file', help='Path to a .storm file to run (use - for stdin).')
    pars.add_argument('--raw', action='store_true', default=False, help='Output raw JSON lines.')
    pars.add_argument('--dir', help='Cortex data directory (persists between runs).')
    pars.add_argument('--view', help='View iden to execute the query in.')
    pars.add_argument('--forked', action='store_true', default=False,
                      help='Fork the target view before running, then delete the fork after.')

    opts = pars.parse_args(argv)

    if opts.file == '-':
        text = sys.stdin.read()
    else:
        with open(opts.file, 'r') as fd:
            text = fd.read()

    if text is None or text.strip() == '':
        outp.printf('No Storm query text provided.')
        return 1

    cleanup = False
    dirn = opts.dir
    if dirn is None:
        dirn = tempfile.mkdtemp()
        cleanup = True

    try:

        ret = 0

        printer = s_printer.StormPrinter(outp)

        async with await s_cortex.Cortex.anit(dirn) as core:

            stormopts = {'node:opts': {'repr': True}}

            forkiden = None

            if opts.forked:
                if opts.view is not None:
                    view = core.getView(opts.view)
                else:
                    view = core.view

                vdef = await view.fork()
                forkiden = vdef.get('iden')
                stormopts['view'] = forkiden

            elif opts.view is not None:
                stormopts['view'] = opts.view

            try:

                async for mesg in core.storm(text, opts=stormopts):

                    if opts.raw:
                        outp.printf(json.dumps(mesg, sort_keys=True))
                        continue

                    if not printer.printMesg(mesg):
                        ret = 1

            finally:
                if forkiden is not None:
                    await core.delViewWithLayer(forkiden)

        return ret

    finally:
        if cleanup:
            shutil.rmtree(dirn, ignore_errors=True)

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
