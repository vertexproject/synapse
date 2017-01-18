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
    pars.add_argument('--tags', default=None, help='Tags to add to *all* created nodes')
    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect cortex')
    pars.add_argument('--verbose', default=False, action='store_true', help='Show changes to local cortex incrementally')
    pars.add_argument('--json', default=None, help='JSON ingest definition file')
    pars.add_argument('files', nargs='*', help='Data files to parse and ingest')

    opts = pars.parse_args(argv)

    core = s_cortex.openurl(opts.core)
    core.setConfOpt('enforce',1)

    # FIXME check for telepath proxy and bitch.
    # this core may not be remote because we use
    # the transaction API.

    def _print_tufo_add(mesg):
        tufo = mesg[1].get('tufo')
        form = tufo[1].get('tufo:form')
        outp.printf('add: %s=%s' % (form,tufo[1].get(form)))

    def _print_tufo_tag_add(mesg):
        tag = mesg[1].get('tag')
        tufo = mesg[1].get('tufo')
        form = tufo[1].get('tufo:form')
        outp.printf('tag: %s=%s (%s)' % (form,tufo[1].get(form),tag))

    tags = []
    if opts.tags != None:
        tags = opts.tags.split(',')

    if opts.verbose:
        core.on('tufo:add', _print_tufo_add)
        core.on('tufo:tag:add', _print__tufo_tag_add)

    pump = None
    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        pump = core.getSyncPump(sync)

    # by default, we scrape text from lines
    jsfo = {
        'format':'lines',

        'ingest':{
            'scrapes':(
                ('*',{}),
            ),
        }
    }

    if opts.json:
        jsfo = jsload( opts.json )

    if tags:
        tags.extend( jsfo.get('ingest',{}).get('tags',()) )
        jsfo['ingest']['tags'] = tags

    gest = s_ingest.Ingest(jsfo)

    tick = time.time()

    with core.getCoreXact() as xact:

        openinfo = jsfo.get('opendata',{})
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

