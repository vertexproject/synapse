import sys
import code
import argparse
import cProfile

import synapse.cortex as s_cortex

import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.scrape as s_scrape

from synapse.common import *

def main(argv, outp=None):

    if outp == None:
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='ingest', description='Command line tool for ingesting data into a cortex')

    pars.add_argument('--sync', default=None, help='Sync to an additional cortex')
    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect cortex')
    pars.add_argument('json', default=None, help='JSON ingest definition file')
    pars.add_argument('files', nargs='*', help='Data files to parse and ingest')

    opts = pars.parse_args(argv)

    core = s_cortex.openurl('ram://')
    core.setConfOpt('enforce',1)

    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        core.on('core:sync', sync.sync )

    jsfo = jsload( opts.json )

    gest = s_ingest.Ingest(jsfo)

    for datafile in opts.files:
        data = s_ingest.opendata(datafile,gest)
        gest.ingest(core,data)

    if opts.debug:
        code.interact( local=locals() )

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:] ) )

