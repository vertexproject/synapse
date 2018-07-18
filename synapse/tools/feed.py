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

def getItems(*paths):
    items = []
    for path in paths:
        if path.endswith('.json'):
            item = s_common.jsload(path)
            items.append(item)
        elif path.endswith(('.yaml', '.yml')):
            item = s_common.yamlload(path)
            items.append(item)
        else:  # pragma: no cover
            logger.warning('Unsupported file path: [%s]', path)
    return items


def addFeedData(core, outp, format,
                debug=False,
                *paths):
    items = getItems(*paths)
    core.addFeedData(format, items)
    if debug:
        cmdr = s_cmdr.getItemCmdr(core, outp)
        cmdr.runCmdLoop()

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
                addFeedData(core, outp, opts.format, opts.debug, *opts.files)

    elif opts.cortex:
        with s_telepath.openurl(opts.cortex) as core:
            addFeedData(core, outp, opts.format, opts.debug, *opts.files)

    else:  # pragma: no cover
        outp.printf('No valid options provided [%s]', opts)
        return 1

    return 0

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
    pars.add_argument('--format', '-f', type=str, action='store', default='syn.ingest',
                      help='Feed format to use for the ingested data.')
    pars.add_argument('--modules', '-m', type=str, action='append', default=[],
                      help='Additional modules to load locally with a test Cortex.')

    pars.add_argument('files', nargs='*', help='JSON ingest definition files')

    return pars

def _main():  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    return main(sys.argv[1:])

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
