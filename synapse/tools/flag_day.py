import argparse
import logging
import pathlib

from typing import Optional, List

import synapse.cortex as s_cortex
import synapse.cores.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def loadTufo(tufo):
    logger.debug(tufo)

def convertField(oldval):
    return oldval

def translatePre010Tufo(oldtufo):
    _, oldprops = oldtufo
    formname = oldprops['tufo:form']
    pk = convertField(oldprops[formname])
    props = {}
    tags = {}
    for oldk, oldv in oldprops.items():
        if oldk[0] == '#':
            tags[oldk[1:]] = oldv
        elif oldk.startswith(formname + ':'):
            newprop = oldk[len(formname) + 1:]
            props[newprop] = convertField(oldv)
        elif oldk == 'node:created':
            props['.created'] = oldv
        else:
            logger.debug('Skipping propname %s', oldk)

    return ((formname, pk), {'props': props, 'tags': tags})


def migrateCortex(core: s_common.Cortex, indir: pathlib.Path):
    '''
    Translates all the data from a < 0.1.0 cortex dumped using dump_cortex.py into 0.1.0 and loads into an existing
    cortex.
    '''
    for i, fn in enumerate(indir.glob('*.dump')):
        for j, oldtufo in enumerate(s_msgpack.iterfile(fn)):
            try:
                newtufo = translatePre010Tufo(oldtufo)
            except Exception:
                logger.exception('Translating failed on item %d in %s', j, fn)
            else:
                loadTufo(newtufo)
            # Nic tmp
            if j > 3:
                break

def main(argv: List[str], outp: Optional[s_output.OutPut]=None):
    p = argparse.ArgumentParser()
    p.add_argument('cortex', help='telepath URL for a cortex to be dumped')
    p.add_argument('indir', help='directory to find dump files')
    p.add_argument('--verbose', '-v', action='count', help='Verbose output')
    opts = p.parse_args(argv)
    if opts.verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif opts.verbose > 0:
        logger.setLevel(logging.INFO)

    # core = s_cortex.openurl(opts.cortex)
    core = None
    dirpath = pathlib.Path(opts.indir)
    migrateCortex(core, dirpath)
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    sys.exit(main(sys.argv[1:]))
