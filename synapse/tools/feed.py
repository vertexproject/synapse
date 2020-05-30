import os
import sys
import time
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cmdr as s_cmdr
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.encoding as s_encoding

logger = logging.getLogger(__name__)

reqver = '>=0.2.0,<3.0.0'

def getItems(*paths):
    items = []
    for path in paths:
        if path.endswith('.json'):
            item = s_common.jsload(path)
            if not isinstance(item, list):
                item = [item]
            items.append((path, item))
        elif path.endswith('.jsonl'):
            with s_common.genfile(path) as fd:
                item = list(s_encoding.iterdata(fd, False, format='jsonl'))
                items.append((path, item))
        elif path.endswith(('.yaml', '.yml')):
            item = s_common.yamlload(path)
            if not isinstance(item, list):
                item = [item]
            items.append((path, item))
        elif path.endswith('.mpk'):
            genr = s_msgpack.iterfile(path)
            items.append((path, genr))
        else:  # pragma: no cover
            logger.warning('Unsupported file path: [%s]', path)
    return items

async def addFeedData(core, outp, feedformat, debug=False, *paths, chunksize=1000, offset=0):

    items = getItems(*paths)
    for path, item in items:

        bname = os.path.basename(path)

        tick = time.time()
        outp.printf(f'Adding items from [{path}]')

        foff = 0
        for chunk in s_common.chunks(item, chunksize):

            clen = len(chunk)
            if offset and foff + clen < offset:
                # We have not yet encountered a chunk which
                # will include the offset size.
                foff += clen
                continue

            await core.addFeedData(feedformat, chunk)

            foff += clen
            outp.printf(f'Added [{clen}] items from [{bname}] - offset [{foff}]')

        tock = time.time()

        outp.printf(f'Done consuming from [{bname}]')
        outp.printf(f'Took [{tock - tick}] seconds.')

    if debug:
        await s_cmdr.runItemCmdr(core, outp, True)

async def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = makeargparser()
    opts = pars.parse_args(argv)

    if opts.offset:
        if len(opts.files) > 1:
            outp.printf('Cannot start from a arbitrary offset for more than 1 file.')
            return 1

        outp.printf(f'Starting from offset [{opts.offset}] - it may take a while'
                    f' to get to that location in the input file.')

    if opts.test:
        async with s_cortex.getTempCortex(mods=opts.modules) as prox:
            await addFeedData(prox, outp, opts.format, opts.debug,
                        chunksize=opts.chunksize,
                        offset=opts.offset,
                        *opts.files)

    elif opts.cortex:
        async with await s_telepath.openurl(opts.cortex) as core:
            try:
                s_version.reqVersion(core._getSynVers(), reqver)
            except s_exc.BadVersion as e:
                valu = s_version.fmtVersion(*e.get('valu'))
                outp.printf(f'Cortex version {valu} is outside of the feed tool supported range ({reqver}).')
                outp.printf(f'Please use a version of Synapse which supports {valu}; '
                      f'current version is {s_version.verstring}.')
                return 1
            await addFeedData(core, outp, opts.format, opts.debug,
                              chunksize=opts.chunksize,
                              offset=opts.offset,
                              *opts.files)

    else:  # pragma: no cover
        outp.printf('No valid options provided [%s]', opts)
        return 1

    return 0

def makeargparser():
    desc = 'Command line tool for ingesting data into a cortex'
    pars = argparse.ArgumentParser('synapse.tools.feed', description=desc)

    muxp = pars.add_mutually_exclusive_group(required=True)
    muxp.add_argument('--cortex', '-c', type=str,
                      help='Cortex to connect and add nodes too.')
    muxp.add_argument('--test', '-t', default=False, action='store_true',
                      help='Perform a local ingest against a temporary cortex.')

    pars.add_argument('--debug', '-d', default=False, action='store_true',
                      help='Drop to interactive prompt to inspect cortex after loading data.')
    pars.add_argument('--format', '-f', type=str, action='store', default='syn.nodes',
                      help='Feed format to use for the ingested data.')
    pars.add_argument('--modules', '-m', type=str, action='append', default=[],
                      help='Additional modules to load locally with a test Cortex.')
    pars.add_argument('--chunksize', type=int, action='store', default=1000,
                      help='Default chunksize for iterating over items.')
    pars.add_argument('--offset', type=int, action='store', default=0,
                      help='Item offset to start consuming msgpack files from.')
    pars.add_argument('files', nargs='*', help='json/yaml/msgpack feed files')

    return pars

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    asyncio.run(main(sys.argv[1:]))
