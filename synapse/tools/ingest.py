import sys
import time
import shutil
import logging
import argparse
import tempfile
import contextlib
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.lib.node as s_node
import synapse.lib.const as s_const
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

@contextlib.contextmanager
def getTempDir():
    tempdir = tempfile.mkdtemp()

    try:
        yield tempdir

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

def runIngest(core, *paths):
    for path in paths:
        gestdef = s_common.jsload(path)
        ing = s_ingest.Ingest(gestdef)
        nodes = ing.ingest(core)
        yield nodes

def getRet(core, outp, verbose=False, debug=False, *paths):
    c = 0
    for nodes in runIngest(core, *paths):
        for node in nodes:
            if node is None:
                outp.printf('Failed to create a node.')
                return 1
            c = c + 1
            if verbose:
                if isinstance(node, s_node.Node):
                    node = node.pack()
                outp.printf(f'{node}')
    outp.printf(f'Made {c} nodes from {list(paths)}.')
    if debug:
        cmdr = s_cmdr.getItemCmdr(core, outp)
        cmdr.runCmdLoop()
    return 0

def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = makeargpaser()
    opts = pars.parse_args(argv)

    if opts.test:
        with getTempDir() as dirn:
            s_common.yamlsave({'layer:lmdb:mapsize': s_const.gibibyte * 5}, dirn, 'cell.yaml')
            with s_cortex.Cortex(dirn) as core:
                for mod in opts.modules:
                    outp.printf(f'Loading [{mod}]')
                    core.loadCoreModule(mod)
                ret = getRet(core, outp, opts.verbose, opts.debug, *opts.files)

    elif opts.cortex:
        with s_telepath.openurl(opts.cortex) as core:
            ret = getRet(core, outp, opts.verbose, opts.debug, *opts.files)

    else:  # pragma: no cover
        outp.printf('No valid options provided [%s]', opts)
        return 1

    if ret != 0:
        outp.printf('Error encountered during data loading.')
        return ret

    return ret

def makeargpaser():
    desc = 'Command line tool for ingesting data into a cortex'
    pars = argparse.ArgumentParser('synapse.tools.ingest', description=desc)

    muxp = pars.add_mutually_exclusive_group(required=True)
    muxp.add_argument('--cortex', '-c', type=str,
                      help='Cortex to connect and add nodes too.')
    muxp.add_argument('--test', '-t', default=False, action='store_true',
                      help='Perform a local ingest against a temporary cortex.')

    pars.add_argument('--debug', '-d', default=False, action='store_true',
                      help='Drop to interactive prompt to inspect cortex after loading data.')
    pars.add_argument('--verbose', '-v', default=False, action='store_true',
                      help='Print nodes created by ingest.')

    pars.add_argument('--save', '-s', type=str, action='store',
                      help='Save cortex splice events to a file.')
    pars.add_argument('--modules', '-m', type=str, action='append', default=[],
                      help='Additional modules to load locally with a test Cortex.')

    pars.add_argument('files', nargs='*', help='JSON ingest definition files')

    return pars

def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    return main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
