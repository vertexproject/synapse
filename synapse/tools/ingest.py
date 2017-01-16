import sys
import code
import time
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

    pars.add_argument('--core', default='ram://', help='Cortex to use for ingest deconfliction')
    pars.add_argument('--sync', default=None, help='Sync to an additional cortex')
    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect cortex')
    pars.add_argument('--verbose', default=False, action='store_true', help='Show changes to local cortex incrementally')
    pars.add_argument('json', default=None, help='JSON ingest definition file')
    pars.add_argument('files', nargs='*', help='Data files to parse and ingest')

    opts = pars.parse_args(argv)

    core = s_cortex.openurl(opts.core)
    core.setConfOpt('enforce',1)

    def _tufo_add(mesg):
        tufo = mesg[1].get('tufo')
        form = tufo[1].get('tufo:form')
        outp.printf('add: %s=%s' % (form,tufo[1].get(form)))

    def _tufo_tag(mesg):
        tag = mesg[1].get('tag')
        tufo = mesg[1].get('tufo')
        form = tufo[1].get('tufo:form')
        outp.printf('tag: %s=%s (%s)' % (form,tufo[1].get(form),tag))

    if opts.verbose:
        core.on('tufo:add', _tufo_add)
        core.on('tufo:tag:add', _tufo_tag)

    pump = None
    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        pump = core.getSyncPump(sync)

    jsfo = jsload( opts.json )

    gest = s_ingest.Ingest(jsfo)

    tick = time.time()

    openinfo = jsfo.get('opendata')
    for datafile in opts.files:
        data = s_ingest.opendata(datafile,**openinfo)
        gest.ingest(core,data)

    tock = time.time()
    outp.printf('ingest took: %s sec' % (tock-tick,))

    if opts.debug:
        code.interact( local=locals() )

    if pump != None:
        pump.done()
        outp.printf('waiting on sync pump...')
        pump.waitfini()

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:] ) )

