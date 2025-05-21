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

import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.encoding as s_encoding

import synapse.tools.storm as s_t_storm

logger = logging.getLogger(__name__)

reqver = '>=3.0.0,<4.0.0'

def getItems(*paths):
    items = []
    for path in paths:
        if path.endswith('.json'):
            item = s_json.jsload(path)
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
        elif path.endswith('.mpk') or path.endswith('.nodes'):
            genr = s_msgpack.iterfile(path)
            items.append((path, genr))
        else:  # pragma: no cover
            logger.warning('Unsupported file path: [%s]', path)
    return items

async def ingest_items(core, items, outp, path, bname, viewiden=None, offset=None, chunksize=1000, debug=False):
    tick = time.time()
    outp.printf(f'Adding items from [{path}]')
    foff = -1
    for chunk in s_common.chunks(items, chunksize):
        clen = len(chunk)
        if offset and foff + clen <= offset:
            foff += clen
            continue
        await core.addFeedData(chunk, viewiden=viewiden)
        foff += clen
        outp.printf(f'Added [{clen}] items from [{bname}] - offset [{foff}]')
    tock = time.time()
    outp.printf(f'Done consuming from [{bname}]')
    outp.printf(f'Took [{tock - tick}] seconds.')
    if debug: # pragma: no cover
        await s_t_storm.runItemStorm(core, outp=outp)

async def addFeedData(core, outp, debug=False, *paths, chunksize=1000, offset=0, viewiden=None, extend_model=False, summary=False):
    items = getItems(*paths)
    if (summary or extend_model):
        for path, _ in items:
            if not (path.endswith('.mpk') or path.endswith('.nodes')):
                outp.printf(f'Warning: --summary and --extend-model are only supported for .mpk/.nodes files. Skipping [{path}].')
                continue

    for path, item in items:
        bname = os.path.basename(path)
        is_synnode3 = path.endswith('.mpk') or path.endswith('.nodes')

        if is_synnode3:

            genr = s_msgpack.iterfile(path)
            meta = next(genr)

            if not (isinstance(meta, dict) and meta.get('type') == 'meta'):
                outp.printf(f'Warning: {path} is not a valid syn.nodes file!')
                continue # Next file

            if summary:
                outp.printf(f"Summary for [{bname}]:")
                outp.printf(f"  Creator: {meta.get('creatorname')}")
                outp.printf(f"  Created: {meta.get('created')}")
                outp.printf(f"  Forms: {meta.get('forms')}")
                outp.printf(f"  Count: {meta.get('count')}")
                model_ext = meta.get('model_ext', {})
                nonempty_exts = {k: v for k, v in model_ext.items() if v}
                if nonempty_exts:
                    outp.printf("  Model Extensions:")
                    for k, v in nonempty_exts.items():
                        outp.printf(f"    {k}:")
                        for item in v:
                            outp.printf(f"      {item}")
                else:
                    outp.printf("  Model Extensions: (none)")
                continue  # Skip ingest

            if extend_model:
                await core.importStormMeta(meta, extmodel=True, viewiden=viewiden)
                outp.printf(f"Extended model elements from metadata in [{bname}]")

            await ingest_items(core, genr, outp, path, bname, viewiden=viewiden, offset=offset, chunksize=chunksize, debug=debug)
            continue # Next file

        # all other supported file types
        await ingest_items(core, item, outp, path, bname, viewiden=viewiden, offset=offset, chunksize=chunksize, debug=debug)

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
        async with s_cortex.getTempCortex() as prox:
            await addFeedData(prox, outp, opts.debug,
                        chunksize=opts.chunksize,
                        offset=opts.offset,
                        extend_model=opts.extend_model,
                        summary=opts.summary,
                        *opts.files)

    elif opts.cortex:
        async with s_telepath.withTeleEnv():
            async with await s_telepath.openurl(opts.cortex) as core:
                try:
                    s_version.reqVersion(core._getSynVers(), reqver)
                except s_exc.BadVersion as e:
                    valu = s_version.fmtVersion(*e.get('valu'))
                    outp.printf(f'Cortex version {valu} is outside of the feed tool supported range ({reqver}).')
                    outp.printf(f'Please use a version of Synapse which supports {valu}; '
                          f'current version is {s_version.verstring}.')
                    return 1
                await addFeedData(core, outp, opts.debug,
                                  chunksize=opts.chunksize,
                                  offset=opts.offset,
                                  viewiden=opts.view,
                                  extend_model=opts.extend_model,
                                  summary=opts.summary,
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


    pars.add_argument('--extend-model', '-e', default=False, action='store_true',
                      help='Extend the model with the data.')
    pars.add_argument('--summary', '-s', default=False, action='store_true',
                      help='Show a summary of the data. Do not add any data.')
    pars.add_argument('--debug', '-d', default=False, action='store_true',
                      help='Drop to interactive prompt to inspect cortex after loading data.')
    pars.add_argument('--chunksize', type=int, action='store', default=1000,
                      help='Default chunksize for iterating over items.')
    pars.add_argument('--offset', type=int, action='store', default=0,
                      help='Item offset to start consuming data from.')
    pars.add_argument('--view', type=str, action='store', default=None,
                      help='The View to ingest the data into.')
    pars.add_argument('files', nargs='*', help='json/yaml/msgpack feed files')

    return pars

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
