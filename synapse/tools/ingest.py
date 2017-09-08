import sys
import time
import argparse
import collections

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.lib.tufo as s_tufo
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output

def main(argv, outp=None):

    if outp is None:  # pragma: no cover
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
    try:
        s_telepath.reqNotProxy(core)
    except s_common.MustBeLocal:
        outp.printf('Ingest requires a local cortex to deconflict against, not a Telepath proxy')
        raise
    core.setConfOpt('enforce', 1)

    if opts.debug:  # pragma: no cover
        core.setConfOpt('log:save', 1)

    # FIXME check for telepath proxy and bitch.
    # this core may not be remote because we use
    # the transaction API.

    def _print_tufo_add(mesg):
        tufo = mesg[1].get('node')
        form = tufo[1].get('tufo:form')
        outp.printf('add: %s=%s' % (form, tufo[1].get(form)))
        for prop, valu in sorted(s_tufo.props(tufo).items()):
            outp.printf('       :%s = %s' % (prop, valu))

    def _print_tufo_tag_add(mesg):
        tag = mesg[1].get('tag')
        tufo = mesg[1].get('node')
        form = tufo[1].get('tufo:form')
        outp.printf('tag: %s=%s (%s)' % (form, tufo[1].get(form), tag))

    progtot = collections.defaultdict(int)
    proglast = collections.defaultdict(int)

    proglocs = {'tick': None, 'datatot': 0, 'datalast': 0, 'tufotot': 0, 'tufolast': 0}

    def onGestData(mesg):
        proglocs['datatot'] += 1
        proglocs['datalast'] += 1

    def onNodeAdd(mesg):
        proglocs['tufotot'] += 1
        proglocs['tufolast'] += 1

    # callback for displaying progress...
    def onGestProg(mesg):

        act = mesg[1].get('act')

        progtot[act] += 1
        proglast[act] += 1

        progtot['total'] += 1
        proglast['total'] += 1

        progtick = proglocs.get('tick')
        if progtick is None:
            proglocs['tick'] = time.time()
            return

        if progtick is not None:

            now = time.time()
            delta = now - progtick

            if delta >= 1.0:

                tot = sum(proglast.values())
                persec = int(float(tot) / delta)
                tot = proglast.get('total', 0)

                datatot = proglocs.get('datatot', 0)
                datalast = proglocs.get('datalast', 0)
                datasec = int(float(datalast) / delta)

                tufotot = proglocs.get('tufotot', 0)
                tufolast = proglocs.get('tufolast', 0)
                tufosec = int(float(tufolast) / delta)

                totstat = tuple(sorted(progtot.items()))
                laststat = tuple(sorted(proglast.items()))

                totstr = ' '.join(['%s=%s' % (n, v) for (n, v) in totstat])
                laststr = ' '.join(['%s=%s' % (n, v) for (n, v) in laststat])

                outp.printf('data: %s %s/sec (%d) nodes: %s %s/sec (%d)' % (datalast, datasec, datatot, tufolast, tufosec, tufotot))

                proglast.clear()
                proglocs['tick'] = time.time()
                proglocs['datalast'] = 0
                proglocs['tufolast'] = 0

    if opts.save:
        outp.printf('saving sync events to: %s' % (opts.save,))
        core.addSpliceFd(s_common.genfile(opts.save))

    if opts.verbose:
        core.on('node:add', _print_tufo_add)
        core.on('node:tag:add', _print_tufo_tag_add)

    pump = None
    if opts.sync is not None:
        sync = s_cortex.openurl(opts.sync)
        pump = core.getSplicePump(sync)

    tick = time.time()

    with core.getCoreXact() as xact:

        for path in opts.files:
            gest = s_ingest.loadfile(path)

            if opts.progress:
                core.on('node:add', onNodeAdd)
                gest.on('gest:data', onGestData)
                gest.on('gest:prog', onGestProg)

            gest.ingest(core)

    tock = time.time()

    outp.printf('ingest took: %s sec' % (tock - tick,))

    if opts.debug:  # pragma: no cover
        s_cmdr.runItemCmdr(core)

    if pump is not None:
        pump.done()
        outp.printf('waiting on sync pump...')
        pump.waitfini()

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
