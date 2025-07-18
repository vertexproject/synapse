import csv

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.cmdr as s_cmdr
import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.version as s_version

reqver = '>=0.2.0,<3.0.0'
desc = '''Command line tool for ingesting csv files into a cortex

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

async def runCsvExport(opts, outp, text, stormopts):
    if not opts.cortex:
        outp.printf('--export requires --cortex')
        return 1

    if len(opts.csvfiles) != 1:
        outp.printf('--export requires exactly 1 csvfile')
        return 1

    path = s_common.genpath(opts.csvfiles[0])
    outp.printf(f'Exporting CSV rows to: {path}')

    async with await s_telepath.openurl(opts.cortex) as core:

        try:
            s_version.reqVersion(core._getSynVers(), reqver)
        except s_exc.BadVersion as e:
            valu = s_version.fmtVersion(*e.get('valu'))
            outp.printf(f'Cortex version {valu} is outside of the csvtool supported range ({reqver}).')
            outp.printf(f'Please use a version of Synapse which supports {valu}; '
                        f'current version is {s_version.verstring}.')
            return 1

        with open(path, 'w') as fd:

            wcsv = csv.writer(fd)
            # prevent streaming nodes by limiting shown events
            stormopts['show'] = ('csv:row', 'print', 'warn', 'err')
            count = 0
            async for name, info in core.storm(text, opts=stormopts):

                if name == 'csv:row':
                    count += 1
                    wcsv.writerow(info['row'])
                    continue

                if name in ('init', 'fini'):
                    continue

                outp.printf('%s: %r' % (name, info))

            outp.printf(f'exported {count} csv rows.')

    return 0

async def runCsvImport(opts, outp, text, stormopts):

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
        logfd.seek(0, 2)

    async def addCsvData(core):

        nodecount = 0

        stormopts['editformat'] = 'nodeedits'

        vars = stormopts.setdefault('vars', {})

        for rows in rowgenr:

            vars['rows'] = rows

            async for mesg in core.storm(text, opts=stormopts):

                if mesg[0] == 'node':
                    nodecount += 1

                elif mesg[0] == 'err' and not opts.debug:
                    outp.printf(repr(mesg))

                elif mesg[0] == 'print':
                    outp.printf(mesg[1].get('mesg'))

                if opts.debug:
                    outp.printf(repr(mesg))

                if logfd is not None:
                    logfd.write(s_json.dumps(mesg, newline=True))

        if opts.cli:
            await s_cmdr.runItemCmdr(core, outp, True)

        return nodecount

    if opts.test:
        async with s_cortex.getTempCortex() as core:
            nodecount = await addCsvData(core)

    else:
        async with await s_telepath.openurl(opts.cortex) as core:

            try:
                s_version.reqVersion(core._getSynVers(), reqver)
            except s_exc.BadVersion as e:
                valu = s_version.fmtVersion(*e.get('valu'))
                outp.printf(f'Cortex version {valu} is outside of the csvtool supported range ({reqver}).')
                outp.printf(f'Please use a version of Synapse which supports {valu}; '
                            f'current version is {s_version.verstring}.')
                return 1

            nodecount = await addCsvData(core)

    if logfd is not None:
        logfd.close()

    outp.printf('%d nodes.' % (nodecount, ))
    return 0

async def main(argv, outp=s_output.stdout):
    pars = makeargparser(outp)

    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:
        return e.get('status')

    with open(opts.stormfile, 'r', encoding='utf8') as fd:
        text = fd.read()

    stormopts = {}
    if opts.optsfile:
        stormopts = s_common.yamlload(opts.optsfile)

    if opts.view:
        if not s_common.isguid(opts.view):
            outp.printf(f'View is not a guid {opts.view}')
            return 1
        stormopts['view'] = opts.view

    async with s_telepath.withTeleEnv():

        if opts.export:
            return await runCsvExport(opts, outp, text, stormopts)
        else:
            return await runCsvImport(opts, outp, text, stormopts)

def makeargparser(outp):
    pars = s_cmd.Parser(prog='synapse.tools.csvtool', description=desc, outp=outp)
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
    pars.add_argument('--export', default=False, action='store_true',
                      help='Export CSV data to file from storm using $lib.csv.emit(...) events.')
    pars.add_argument('--view', default=None, action='store',
                      help='Optional view to work in.')
    pars.add_argument('--optsfile', default=None, action='store',
                      help='Path to an opts file (.yaml) on disk.')
    pars.add_argument('stormfile', help='A Storm script describing how to create nodes from rows.')
    pars.add_argument('csvfiles', nargs='+', help='CSV files to load.')
    return pars

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
