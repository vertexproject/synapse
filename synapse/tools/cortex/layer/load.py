import os

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.time as s_time
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

descr = '''
Import node edits to a Synapse layer.
'''

async def importLayer(infiles, opts, outp):

    async with await s_telepath.openurl(opts.url) as cell:

        info = await cell.getCellInfo()

        if (celltype := info['cell']['type']) != 'cortex':
            mesg = f'Layer load tool only works on cortexes, not {celltype}.'
            raise s_exc.TypeMismatch(mesg=mesg)

        # Get the highest cellvers from all the input files
        reqver = max([infile[0].get('cellvers') for infile in infiles])

        if (synver := info.get('cell').get('version')) < reqver:
            synstr = s_version.fmtVersion(*synver)
            reqstr = s_version.fmtVersion(*reqver)
            mesg = f'Synapse version mismatch ({synstr} < {reqstr}).'
            raise s_exc.BadVersion(mesg=mesg)

    async with await s_telepath.openurl(opts.url, name=f'*/layer/{opts.iden}') as layer:
        for header, filename, genr in infiles:
            soffs = header.get('offset')
            tick = header.get('tick')

            outp.printf(f'Loading {filename}, offset={soffs}, tick={s_time.repr(tick)}.')

            eoffs = soffs
            fini = None

            for item in genr:
                match item:
                    case ('edit', (eoffs, edit, meta)):
                        if opts.dryrun:
                            continue

                        await layer.saveNodeEdits(edit, meta=meta)

                    case ('fini', info):
                        fini = info
                        break

                    case _:
                        mtype = item[0]
                        mesg = f'Unexpected message type: {mtype}.'
                        raise s_exc.BadMesgFormat(mesg=mesg)

            if fini is None:
                mesg = f'Incomplete/corrupt export: {filename}.'
                raise s_exc.BadDataValu(mesg=mesg)

            elif (offset := fini.get('offset')) != eoffs:
                mesg = f'Incomplete/corrupt export: {filename}. Expected offset {offset}, got {eoffs}.'
                raise s_exc.BadDataValu(mesg=mesg)

            else:
                if opts.dryrun:
                    outp.printf(f'Successfully read {filename} as a dryrun test.')
                else:
                    outp.printf(f'Successfully loaded {filename} with {eoffs + 1 - soffs} edits ({soffs} - {eoffs}).')

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='layer.load', outp=outp, description=descr)
    pars.add_argument('--dryrun', action='store_true', help="Process files but don't apply changes.")
    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL of the Synapse service.')

    pars.add_argument('iden', help='The iden of the layer to import to.')
    pars.add_argument('files', nargs='+', help='The .nodeedits files to import from.')

    opts = pars.parse_args(argv)

    infiles = []

    try:
        # Load the files
        for filename in opts.files:
            if not os.path.exists(filename) or not os.path.isfile(filename):
                mesg = f'Invalid input file specified: {filename}.'
                raise s_exc.NoSuchFile(mesg=mesg)

            genr = s_msgpack.iterfile(filename)
            header = next(genr)
            if header[0] != 'init':
                mesg = f'Invalid header in {filename}.'
                raise s_exc.BadMesgFormat(mesg=mesg)

            infiles.append((header[1], filename, genr))

        # Sort the files based on their offset
        infiles = sorted(infiles, key=lambda x: x[0].get('offset'))

        outp.printf('Processing the following nodeedits:')
        outp.printf('Offset           | Filename')
        outp.printf('-----------------|----------')
        for header, filename, genr in infiles:
            offset = header.get('offset')
            outp.printf(f'{offset:<16d} | {filename}')

        async with s_telepath.withTeleEnv():
            await importLayer(infiles, opts, outp)

        return 0

    except s_exc.SynErr as exc:
        mesg = exc.get('mesg')
        outp.printf(f'ERROR: {mesg}.')
        return 1

    except Exception as exc: # pragma: no cover
        outp.printf(f'ERROR: {str(exc)}.')
        return 1

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
