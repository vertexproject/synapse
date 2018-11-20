import csv
import sys
import json

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

def iterrows(csv_header=None, *paths):
    for path in paths:

        with open(path, 'r', encoding='utf8') as fd:

            if csv_header:
                fd.readline()

            def genr():

                for row in csv.reader(fd):
                    yield row

            for rows in s_common.chunks(genr(), 1000):
                yield rows

def main(argv, outp=s_output.stdout):
    pars = makeargparser()
    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:
        return e.get('status')

    with open(opts.stormfile, 'r', encoding='utf8') as fd:
        text = fd.read()

    logfd = None
    if opts.logfile is not None:
        logfd = s_common.genfile(opts.logfile)

    newcount = 0
    nodecount = 0
    with s_telepath.openurl(opts.cortex) as core:

        for rows in iterrows(opts.csv_header, *opts.csvfiles):

            stormopts = {
                'vars': {'rows': rows},
            }

            for mesg in core.storm(text, opts=stormopts):

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
    pars.add_argument('--csv-header', default=False, action='store_true', help='Skip the first line from each CSV file.')
    pars.add_argument('--debug', default=False, action='store_true', help='Enable verbose debug output.')
    pars.add_argument('cortex', help='The telepath URL for the cortex ( or alias from ~/.syn/aliases ).')
    pars.add_argument('stormfile', help='A STORM script describing how to create nodes from rows.')
    pars.add_argument('csvfiles', nargs='+', help='CSV files to load.')
    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
