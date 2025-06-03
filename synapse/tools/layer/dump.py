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

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='layer.dump', description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')
    pars.add_argument('--offset', default=0, type=int, help='The starting offset of the node edits to export.')
    pars.add_argument('--chunksize', default=100_000, type=int, help='The number of node edits to store in a single file.')
    pars.add_argument('--outdir', default='.', help='The directory to save the exported node edits to.')

    pars.add_argument('iden', help='The iden of the layer to export.')

    opts = pars.parse_args(argv)

    if os.path.exists(opts.outdir) and not os.path.isdir(opts.outdir):
        mesg = f'Specified output directory {opts.outdir} exists but is not a directory.'
        outp.printf(f'ERROR: {mesg}')
        return 1

    os.makedirs(opts.outdir, exist_ok=True)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            info = await cell.getCellInfo()

            celliden = info['cell']['iden']
            cellvers = info['cell']['version']

        async with await s_telepath.openurl(opts.url, name=f'*/layer/{opts.iden}') as layer:

            # Handle no edits to export
            if opts.offset >= await layer.getEditIndx():
                mesg = f'ERROR: No edits to export starting from offset (10000).'
                outp.printf(mesg)
                return 1

            finished = False

            start = opts.offset
            end = None

            while not finished:

                kwargs = {}

                if s_common.majmin >= (3, 12):
                    kwargs['delete_on_close'] = False

                with tempfile.NamedTemporaryFile(dir=opts.outdir, delete=False, **kwargs) as fd:

                    genr = layer.syncNodeEdits2(start, wait=False)

                    # Pull the first edit so we can get the starting offset
                    first = await anext(aiter(genr))

                    start = first[0]

                    count = 1

                    # Write header to file
                    fd.write(s_msgpack.en((
                        'init',
                        {
                            'hdrvers': 1,
                            'celliden': celliden,
                            'layriden': opts.iden,
                            'offset': start,
                            'chunksize': opts.chunksize,
                            'tick': s_common.now(),
                            'cellvers': cellvers,
                        }
                    )))

                    # Now write the first edit that we already pulled
                    fd.write(s_msgpack.en(('edit', first)))

                    async for nodeedit in genr:

                        # Write individual edits to file
                        fd.write(s_msgpack.en(('edit', nodeedit)))

                        end = nodeedit[0]

                        if count == 0 and start != end:
                            mesg = f'ERROR: First offset ({end}) differs from requested starting offset ({start}).'
                            outp.printf(mesg)
                            if start != 0:
                                return 1
                            start = end

                        count += 1

                        if count % opts.chunksize == 0:
                            break

                    else:
                        finished = True

                    # Write footer to file
                    fd.write(s_msgpack.en(('fini', {
                        'offset': end,
                        'tock': s_common.now(),
                    })))

                    tmpname = fd.name

                path = os.path.join(opts.outdir, f'{celliden}.{opts.iden}.{start}-{end}.nodeedits')
                os.rename(tmpname, path)

                # Update start offset for next loop
                start = end + 1

            outp.printf(f'Successfully exported layer {opts.iden} from cortex {celliden}.')

    return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
