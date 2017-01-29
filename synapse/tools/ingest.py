import sys
import code
import time
import argparse
import cProfile
import collections

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
    pars.add_argument('--progress', default=False, action='store_true', help='Print loading progress')
    pars.add_argument('--sync', default=None, help='Sync to an additional cortex')
    pars.add_argument('--save', default=None, help='Save cortex sync events to a file')
    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect cortex')
    pars.add_argument('--verbose', default=False, action='store_true', help='Show changes to local cortex incrementally')
    pars.add_argument('files', nargs='*', help='JSON ingest definition files')

    opts = pars.parse_args(argv)

    core = s_cortex.openurl(opts.core)
    core.setConfOpt('enforce',1)

    if opts.debug:
        core.setConfOpt('log:save',1)

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

    progtot = collections.defaultdict(int)
    proglast = collections.defaultdict(int)

    proglocs = {'tick':None}

    # callback for displaying progress...
    def onGestProg(mesg):

        act = mesg[1].get('act')

        progtot[act] += 1
        proglast[act] += 1

        progtot['total'] += 1
        proglast['total'] += 1

        progtick = proglocs.get('tick')
        if progtick == None:
            proglocs['tick'] = time.time()
            return

        if progtick != None:

            now = time.time()
            delta = now - progtick

            if delta >= 1.0:

                tot = sum( proglast.values() )
                persec = int( float(tot) / delta )

                totstat = tuple( sorted( progtot.items() ) )
                laststat = tuple( sorted( proglast.items() ) )

                totstr = ' '.join([ '%s=%s' % (n,v) for (n,v) in totstat ])
                laststr = ' '.join([ '%s=%s' % (n,v) for (n,v) in laststat ])

                outp.printf('%s/sec %s (%s)' % (persec,laststr,totstr))

                proglast.clear()
                proglocs['tick'] = time.time()

    if opts.save:
        outp.printf('saving sync events to: %s' % (opts.save,))
        core.addSyncFd( genfile( opts.save ) )

    if opts.verbose:
        core.on('tufo:add', _print_tufo_add)
        core.on('tufo:tag:add', _print_tufo_tag_add)

    pump = None
    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        pump = core.getSyncPump(sync)

    tick = time.time()

    with core.getCoreXact() as xact:

        for path in opts.files:
            gest = s_ingest.loadfile(path)

            if opts.progress:
                gest.on('gest:prog',onGestProg)

            gest.ingest(core)

    tock = time.time()

    outp.printf('ingest took: %s sec' % (tock-tick,))

    if opts.debug:
        code.interact( local=locals() )

    if pump != None:
        pump.done()
        outp.printf('waiting on sync pump...')
        pump.waitfini()

    return 0

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:] ) )

