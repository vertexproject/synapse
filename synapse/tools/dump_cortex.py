import argparse
import logging
import pathlib
import time

from typing import Optional, List

import synapse.cortex as s_cortex
import synapse.cores.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def dumpCortex(core: s_common.Cortex, outdir: pathlib.Path):
    '''
    Sucks all *tufos* out of a cortex and dumps to a directory with one file per form
    '''
    forms = core.getTufoForms()
    for i, fnam in enumerate(forms):
        safe_fnam = fnam.replace(':', '_')
        with (outdir / safe_fnam).with_suffix('.dump').open(mode='wb') as f:
            logger.debug('Starting to dump form %s', fnam)
            start = time.time()

            tufos = core.getTufosByProp('tufo:form', fnam)
            after_query = time.time()
            for t in tufos:
                f.write(s_msgpack.en(t))
            finish = time.time()
            if len(tufos):
                logger.debug('Query time: %.2f, write time %.2f, total time %.2f, total/tufo %.4f',
                             after_query - start, finish - after_query, finish - start, (finish - start) / len(tufos))
            logger.info('(%3d/%3d) Dumped %d %s tufos', i + 1, len(forms), len(tufos), fnam)

def main(argv: List[str], outp: Optional[s_output.OutPut]=None):
    p = argparse.ArgumentParser()
    p.add_argument('cortex', help='telepath URL for a cortex to be dumped')
    p.add_argument('outdir', help='directory in which to place dump files')
    p.add_argument('--verbose', '-v', action='count', help='Verbose output')
    opts = p.parse_args(argv)
    if opts.verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif opts.verbose > 0:
        logger.setLevel(logging.INFO)

    core = s_cortex.openurl(opts.cortex)
    dirpath = pathlib.Path(opts.outdir)
    dirpath.mkdir(parents=True, exist_ok=True)
    dumpCortex(core, dirpath)
    return 0

if __name__ == '__main__':  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    sys.exit(main(sys.argv[1:]))
