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

    if opts.sync != None:
        sync = s_cortex.openurl( opts.sync )
        core.on('core:sync', sync.sync )

    for path in opts.files:

        hset = s_axon.HashSet()
        with reqfile(path) as fd:
            iden,props = hset.consume(fd)

        props['name'] = os.path.basename(path)

        node = core.formTufoByProp('file:bytes',iden,**props)

        print(repr(node))
        core.addTufoTags(node,tags)

        for line in reqlines(path):

            for form,valu in s_scrape.scrape(line):

                if opts.verbose:
                    outp.printf('%s=%s' % (form,valu))

                node = core.formTufoByFrob(form,valu)
                core.addTufoTags(node,tags)

    if opts.debug:
        code.interact( local=locals() )

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:] ) )

