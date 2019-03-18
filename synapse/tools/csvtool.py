import csv
import sys
import json
import asyncio

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.base as s_base
import synapse.lib.cmdr as s_cmdr
import synapse.lib.output as s_output

async def main(argv, outp=s_output.stdout):

    pars = makeargparser()

    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:
        return e.get('status')

    with open(opts.stormfile, 'r', encoding='utf8') as fd:
        text = fd.read()

    def iterrows():
        for path in opts.csvfiles:

            with open(path, 'r', encoding='utf8') as fd:

                if opts.csv_header:
                    fd.readline()

                def genr():

                    for row in csv.reader(fd):
                        yield row

                for rows in s_common.chunks(genr(), 1000):
                    yield rows

    rowgenr = iterrows()

    logfd = None
    if opts.logfile is not None:
        logfd = s_common.genfile(opts.logfile)

    async def addCsvData(core):

        newcount, nodecount = 0, 0

        for rows in rowgenr:

            stormopts = {
                'vars': {'rows': rows},
            }

            async for mesg in core.storm(text, opts=stormopts):

                if mesg[0] == 'node:add':
                    newcount += 1

                elif mesg[0] == 'node':
                    nodecount += 1

                elif mesg[0] == 'err' and not opts.debug:
                    outp.printf(repr(mesg))

                if opts.debug:
                    outp.printf(repr(mesg))

                if logfd is not None:
                    byts = json.dumps(mesg).encode('utf8')
                    logfd.write(byts + b'\n')

        if opts.cli:
            await s_cmdr.runItemCmdr(core, outp)

        return newcount, nodecount

    if opts.test:
        async with s_cortex.getTempCortex() as core:
            newcount, nodecount = await addCsvData(core)

    else:
        async with await s_telepath.openurl(opts.cortex) as core:
            newcount, nodecount = await addCsvData(core)

    if logfd is not None:
        logfd.close()

    outp.printf('%d nodes (%d created).' % (nodecount, newcount,))

def makeargparser():
    desc = '''
    Command line tool for ingesting csv files into a cortex

    The storm file is run with the CSV rows specified in the variable "rows" so most
    storm files will use a variable based for loop to create edit nodes.  For example:

    for ($fqdn, $ipv4, $tag) in $rows {

        [ inet:dns:a=($fqdn, $ipv4) +#$tag ]

    }

    More advanced uses may include switch cases to provide different logic based on
    a column value.

    for ($type, $valu, $info) in $rows {

        switch $type {

            fqdn: {
                [ inet:fqdn=$valu ]
            }

            "person name": {
                [ ps:name=$valu ]
            }

            *: {
                // default case...
            }

        }

        switch $info {
            "known malware": { [+#cno.mal] }
        }

    }
    '''
    pars = s_cmd.Parser('synapse.tools.csvtool', description=desc)
    pars.add_argument('--logfile', help='Set a log file to get JSON lines from the server events.')
    pars.add_argument('--csv-header', default=False, action='store_true',
                      help='Skip the first line from each CSV file.')
    pars.add_argument('--cli', default=False, action='store_true',
                      help='Drop into a cli session after loading data.')
    pars.add_argument('--debug', default=False, action='store_true', help='Enable verbose debug output.')
    muxp = pars.add_mutually_exclusive_group(required=True)
    muxp.add_argument('--cortex', '-c', type=str,
                      help='The telepath URL for the cortex ( or alias from ~/.syn/aliases ).')
    muxp.add_argument('--test', '-t', default=False, action='store_true',
                      help='Perform a local CSV ingest against a temporary cortex.')
    pars.add_argument('stormfile', help='A STORM script describing how to create nodes from rows.')
    pars.add_argument('csvfiles', nargs='+', help='CSV files to load.')
    return pars

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
