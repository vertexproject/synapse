import os
import tarfile
import tempfile

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.const as s_const
import synapse.lib.output as s_output

descr = '''
Dump blobs from a Synapse Axon.
'''

MAX_SPOOL_SIZE = s_const.mebibyte * 512
DEFAULT_ROTATE_SIZE = s_const.gigabyte * 4

def getTarName(celliden, start, end):
    return f'{celliden}.{start:012d}-{end:012d}.tar.gz'

async def dumpBlobs(opts, outp):

    try:
        async with await s_telepath.openurl(opts.url) as axon:

            cellinfo = await axon.getCellInfo()
            celltype = cellinfo['cell']['type']
            if "axon" not in celltype.lower():
                mesg = f'Axon dump tool only works on axons, not {celltype}'
                raise s_exc.TypeMismatch(mesg=mesg)
            celliden = cellinfo['cell']['iden']

            if os.path.exists(opts.outdir) and not os.path.isdir(opts.outdir):
                raise s_exc.BadDataValu(mesg=f'Specified output directory {opts.outdir} exists but is not a directory.')
            os.makedirs(opts.outdir, exist_ok=True)

            if opts.statefile is None:
                statefile_path = os.path.join(opts.outdir, f'{celliden}.yaml')
            else:
                statefile_path = opts.statefile
                if os.path.isdir(statefile_path):
                    statefile_path = os.path.join(statefile_path, f'{celliden}.yaml')
            state = {}
            if os.path.isfile(statefile_path):
                if (data := s_common.yamlload(statefile_path)) is not None:
                    state = data
            opts.statefile = statefile_path

            if opts.offset is not None:
                start = opts.offset
            else:
                start = state.get('offset:next', 0)
            outp.printf(f'Starting the dump from offs={start}')

            rotate_size = opts.rotate_size
            hashes_iter = axon.hashes(start)
            last_offset = start
            tar = None
            tar_path = None
            file_start = start
            file_blobcount = 0
            tar_size = 0
            for_open = True

            try:
                async for (offs, (sha256, size)) in hashes_iter:
                    if for_open:
                        tar_path = os.path.join(opts.outdir, getTarName(celliden, offs, -1))
                        tar = tarfile.open(tar_path, 'w:gz')
                        file_start = offs
                        tar_size = 0
                        file_blobcount = 0
                        for_open = False

                    last_offset = offs
                    file_blobcount += 1
                    sha2hex = s_common.ehex(sha256)
                    outp.printf(f'Dumping blob {sha2hex} (size={size}, offs={offs})')

                    with tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE, mode='w+b', dir=opts.outdir) as tmpf:
                        total = 0
                        async for byts in axon.get(sha256):
                            tmpf.write(byts)
                            total += len(byts)
                        if total != size:
                            raise s_exc.BadDataValu(mesg=f'Blob size mismatch for {sha2hex}: expected {size}, got {total}')
                        tmpf.flush()
                        tmpf.seek(0)
                        tarinfo = tarfile.TarInfo(name=f"{sha2hex}.blob")
                        tarinfo.size = size
                        tar.addfile(tarinfo, tmpf)
                        tar_size += size

                        if tar_size >= rotate_size:
                            outp.printf(f'Rotating to new .tar.gz file at offset {offs + 1}')
                            tar.close()
                            final_name = os.path.join(opts.outdir, getTarName(celliden, file_start, offs + 1))
                            os.rename(tar_path, final_name)
                            tar = None
                            tar_path = None
                            for_open = True

                if tar is not None:
                    tar.close()
                    final_name = os.path.join(opts.outdir, getTarName(celliden, file_start, last_offset + 1))
                    os.rename(tar_path, final_name)
                    tar = None
                    tar_path = None

                state['offset:next'] = last_offset + 1
                s_common.yamlsave(state, statefile_path)

            finally:
                if tar is not None:
                    tar.close()
                    if tar_path and os.path.isfile(tar_path):
                        os.remove(tar_path)

    except s_exc.SynErr as exc:
        mesg = exc.get('mesg')
        return (False, mesg)

    except Exception as e:
        mesg = f'Error {e} dumping blobs from Axon url: {opts.url}'
        return (False, mesg)

    return (True, None)

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='synapse.tools.axon.dump', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='Telepath URL for the Axon.')
    pars.add_argument('--offset', type=int, default=None, help='Starting offset in the Axon.')
    pars.add_argument('--rotate-size', type=int, default=DEFAULT_ROTATE_SIZE,
                      help='Rotate to a new .blobs file after the current file exceeds this size in bytes (default: 4GB). '
                           'Note: files may exceed this size if a single blob is larger than the remaining space.')
    pars.add_argument('--statefile', type=str, default=None,
                      help='Path to the state tracking file for the Axon dump.')
    pars.add_argument('outdir', help='Directory to dump tar.gz files (required).')

    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():
        (ok, mesg) = await dumpBlobs(opts, outp)
        if not ok:
            outp.printf(f'ERROR: {mesg}')
            return 1

    outp.printf('Successfully dumped blobs.')

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
