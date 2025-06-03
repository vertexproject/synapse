import os
import sys
import asyncio
import argparse

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.time as s_time
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

descr = '''
Import node edits to a Synapse layer.
'''

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='layer.load', description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')

    pars.add_argument('iden', help='The iden of the layer to import to.')
    pars.add_argument('files', nargs='+', help='The .nodeedits files to import from.')

    opts = pars.parse_args(argv)

    infiles = []

    # Load the files
    for filename in opts.files:
        if not os.path.exists(filename) or not os.path.isfile(filename):
            mesg = f'Invalid input file specified: {filename}.'
            raise s_exc.BadArg(mesg=mesg, filename=filename)

        genr = s_msgpack.iterfile(filename)
        header = next(genr)
        if header[0] != 'init':
            mesg = f'Invalid header in {filename}.'
            raise s_exc.BadDataValu(mesg=mesg)

        infiles.append((header[1], filename, genr))

    # Sort the files based on their offset
    infiles = sorted(infiles, key=lambda x: x[0].get('offset'))

    reqver = infiles[0][0].get('cellvers')

    # Check we have contiguity
    offset = infiles[0][0].get('offset')
    chunksize = infiles[0][0].get('chunksize')
    for header, *_ in infiles[1:]:
        curo = header.get('offset')

        if offset + chunksize != curo:
            mesg = 'Non-continguous nodeedits provided.'
            raise s_exc.BadDataValu(mesg=mesg)

        offset = curo
        chunksize = header.get('chunksize')

        if (synver := header.get('cellvers')) > reqver:
            reqver = synver

    outp.printf('Processing the following nodeedits:')
    outp.printf('Offset           | Filename')
    outp.printf('-----------------|----------')
    for header, filename, genr in infiles:
        offset = header.get('offset')
        outp.printf(f'{offset:<16d} | {filename}')

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.url) as cell:

            info = await cell.getCellInfo()

            if (synver := info.get('cell').get('version')) < reqver:
                synstr = s_version.fmtVersion(*synver)
                reqstr = s_version.fmtVersion(*reqver)
                mesg = f'Synapse version mismatch ({synstr} < {reqstr}).'
                raise s_exc.BadVersion(mesg, vers=synstr, reqver=reqstr)

        async with await s_telepath.openurl(opts.url, name=f'*/layer/{opts.iden}') as layer:
            for header, filename, genr in infiles:
                start = header.get('offset')
                tick = header.get('tick')

                outp.printf(f'Processing {filename}, offset={start}, tick={s_time.repr(tick)}.')

                end = None
                fini = None

                for item in genr:
                    match item:
                        case ('edit', (end, edit, meta)):
                            await layer.saveNodeEdits(edit, meta=meta)

                        case ('fini', info):
                            fini = info
                            break

                        case _:
                            mtype = item[0]
                            mesg = f'Unexpected message type: {mtype}'
                            raise s_exc.BadDataValu(mesg=mesg, mtype=mtype)

                if fini is None:
                    mesg = f'Incomplete/corrupt export {filename}.'
                    raise s_exc.BadDataValu(mesg, filename=filename)

                elif (offset := fini.get('offset')) != end:
                    mesg = f'Incomplete/corrupt export {filename}, expected offset {end}, got {offset}.'
                    raise s_exc.BadDataValu(mesg, filename=filename, expected=end, got=offset)

                else:
                    outp.printf(f'Completed {filename} with {end + 1 - start} edits ({start} - {end}).')

    return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
