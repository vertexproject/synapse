import os
import sys
import code
import argparse
import cProfile

import synapse.axon as s_axon
import synapse.cortex as s_cortex

import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.scrape as s_scrape

from synapse.common import *

def main(argv, outp=None):

    if outp == None:
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='scrape', description='Command line tool for scraping data into a cortex')

    pars.add_argument('--sync', default=None, help='Sync to an additional cortex')
    pars.add_argument('--axon', default=None, help='Axon URL to save the file bytes')
    pars.add_argument('--save', default=None, help='Save changes to a .sync file for later loading')
    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect cortex')
    pars.add_argument('--verbose',default=False, action='store_true', help='Show the nodes being scraped')
    pars.add_argument('--tags', default=None, help='Tags to add to scraped nodes')
    pars.add_argument('files', nargs='*', help='Data files to scrape')

    opts = pars.parse_args(argv)

    tags = []
    if opts.tags:
        tags = opts.tags.split(',')

    core = s_cortex.openurl('ram://')
    core.setConfOpt('enforce',1)

    axon = None
    if opts.axon != None:
        outp.printf('connecting to axon: %s' % (opts.axon,))
        axon = s_axon.openurl(opts.axon)
        outp.printf('...success! %r' % (axon,))

    if opts.save:
        outp.printf('adding save file: %s' % (opts.save,))
        fd = genfile(opts.save)
        core.addSyncFd(fd)

    pump = None
    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        pump = core.getSyncPump(sync)

    for path in opts.files:

        with reqfile(path) as fd:

            if axon != None:
                outp.printf('Sending to Axon %s -> %s' % (path,opts.axon))
                axon.eatfd(fd)

            hset = s_axon.HashSet()
            iden,props = hset.eatfd(fd)

        props['name'] = os.path.basename(path)
        node = core.formTufoByProp('file:bytes',iden,**props)

        core.addTufoTags(node,tags)

        for line in reqlines(path):

            for form,valu in s_scrape.scrape(line):

                if opts.verbose:
                    outp.printf('%s=%s' % (form,valu))

                node = core.formTufoByFrob(form,valu)
                core.addTufoTags(node,tags)

    if pump != None:
        outp.printf('Waiting For Sync Pump...')
        pump.done()
        pump.waitfini()

    if opts.debug:
        code.interact( local=locals() )

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:] ) )

