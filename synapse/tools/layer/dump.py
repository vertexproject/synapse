import os
import sys
import asyncio
import argparse
import tempfile

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

descr = '''
Export node edits from a Synapse layer.
'''

async def exportLayer(opts, outp):

    async with await s_telepath.openurl(opts.url) as cell:

        info = await cell.getCellInfo()

        if (celltype := info['cell']['type']) != 'cortex':
            mesg = f'Layer dump tool only works on cortexes, not {celltype}'
            raise s_exc.TypeMismatch(mesg=mesg)

        celliden = info['cell']['iden']
        cellvers = info['cell']['version']

    # Find and read state file
    state = {}
    statefile = opts.statefile
    if statefile is None:
        statefile = s_common.genpath(opts.outdir, f'{celliden}.{opts.iden}.yaml')

    if (data := s_common.yamlload(statefile)) is not None:
        state = data

    if (soffs := opts.offset) is None:
        soffs = state.get('offset:next', 0)

    eoffs = None

    async with await s_telepath.openurl(opts.url, name=f'*/layer/{opts.iden}') as layer:

        # Handle no edits to export
        if soffs >= await layer.getEditIndx():
            mesg = f'No edits to export starting from offset ({soffs})'
            raise s_exc.BadArg(mesg=mesg)

        finished = False

        genr = layer.syncNodeEdits2(soffs, wait=False)

        nodeiter = aiter(genr)

        while not finished:

            kwargs = {}

            if s_common.majmin >= (3, 12): # pragma: no cover
                kwargs['delete_on_close'] = False

            with tempfile.NamedTemporaryFile(dir=opts.outdir, delete=False, **kwargs) as fd:

                try:
                    # Pull the first edit so we can get the starting offset
                    first = await anext(nodeiter)
                except StopAsyncIteration:
                    break

                soffs = first[0]

                count = 1

                # Write header to file
                fd.write(s_msgpack.en((
                    'init',
                    {
                        'hdrvers': 1,
                        'celliden': celliden,
                        'cellvers': cellvers,
                        'layriden': opts.iden,
                        'offset': soffs,
                        'chunksize': opts.chunksize,
                        'tick': s_common.now(),
                    }
                )))

                # Now write the first edit that we already pulled
                fd.write(s_msgpack.en(('edit', first)))

                async for nodeedit in nodeiter:

                    # Write individual edits to file
                    fd.write(s_msgpack.en(('edit', nodeedit)))

                    eoffs = nodeedit[0]

                    count += 1

                    if count % opts.chunksize == 0:
                        break

                else:
                    finished = True

                # Write footer to file
                fd.write(s_msgpack.en(('fini', {
                    'offset': eoffs,
                    'tock': s_common.now(),
                })))

                tmpname = fd.name

            path = os.path.join(opts.outdir, f'{celliden}.{opts.iden}.{soffs}-{eoffs}.nodeedits')
            os.rename(tmpname, path)
            outp.printf(f'Wrote layer node edits {soffs}-{eoffs} to {path}.')

            # Update start offset for next loop
            soffs = eoffs + 1

    # Save state file
    state['offset:next'] = eoffs + 1
    s_common.yamlsave(state, statefile)

    return 0

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='layer.dump', description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--offset', default=None, type=int, help='The starting offset of the node edits to export.')
    pars.add_argument('--chunksize', default=100_000, type=int, help='The number of node edits to store in a single file.')
    pars.add_argument('--outdir', default='.', help='The directory to save the exported node edits to.')
    pars.add_argument('--statefile', type=str, default=None, help='Path to the state tracking file for this layer dump.')

    pars.add_argument('iden', help='The iden of the layer to export.')

    opts = pars.parse_args(argv)

    if os.path.exists(opts.outdir) and not os.path.isdir(opts.outdir):
        mesg = f'Specified output directory {opts.outdir} exists but is not a directory.'
        outp.printf(f'ERROR: {mesg}')
        return 1

    os.makedirs(opts.outdir, exist_ok=True)

    async with s_telepath.withTeleEnv():
        try:
            await exportLayer(opts, outp)
        except s_exc.SynErr as exc:
            mesg = exc.get('mesg')
            outp.printf(f'ERROR: {mesg}.')
            return 1

    outp.printf(f'Successfully exported layer {opts.iden}.')

    return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
