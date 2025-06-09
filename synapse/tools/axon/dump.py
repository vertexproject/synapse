import os
import sys
import asyncio
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.coro as s_coro
import synapse.lib.const as s_const
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

descr = '''
Dump blobs from a Synapse Axon.
'''

DEFAULT_ROTATE_SIZE = s_const.gigabyte * 4

def getOutfileName(celliden, start, end):
    return f'{celliden}.{start}-{end}.blobs'

def writeFooterAndClose(outfile, celliden, file_start, file_end, file_blobcount, outfile_path, outdir, outp):
    footer = s_msgpack.en(('blob:fini', {'celliden': celliden, 'start': file_start, 'end': file_end, 'count': file_blobcount}))
    outfile.write(footer)
    final_name = os.path.join(outdir, getOutfileName(celliden, file_start, file_end))
    outfile.close()
    os.rename(outfile_path, final_name)
    outp.printf(f'Wrote {file_blobcount} blobs to {final_name}')

async def dumpBlobs(opts, outp):

    try:
        async with await s_telepath.openurl(opts.url) as axon:

            classes = axon._getClasses()
            if 'synapse.axon.AxonApi' not in classes:
                mesg = f'Service at {opts.url} is not an Axon'
                raise s_exc.TypeMismatch(mesg=mesg)

            cellinfo = await axon.getCellInfo()
            celliden = cellinfo['cell']['iden']
            os.makedirs(opts.outdir, exist_ok=True)

            start = opts.offset
            end = opts.limit
            rotate_size = opts.rotate_size
            hashes_iter = axon.hashes(start)
            last_offset = start
            blobcount = 0
            outfile = None
            outfile_path = None
            file_start = start
            file_size = 0
            for_open = True

            try:
                async for (offs, (sha256, size)) in hashes_iter:
                    if end is not None and offs >= end:
                        break
                    if for_open:
                        outfile_path = os.path.join(opts.outdir, getOutfileName(celliden, offs, 'end'))
                        outfile = open(outfile_path, 'wb')
                        outfile.write(s_msgpack.en(('blob:init', {'celliden': celliden, 'start': offs})))
                        file_start = offs
                        file_size = 0
                        file_blobcount = 0
                        for_open = False
                    last_offset = offs
                    blobcount += 1
                    file_blobcount += 1
                    sha2hex = s_common.ehex(sha256)
                    outp.printf(f'Dumping blob {sha2hex} (size={size}, offs={offs})')
                    blob_header = s_msgpack.en(('blob', {'sha256': sha2hex, 'size': size}))
                    outfile.write(blob_header)
                    file_size += len(blob_header)
                    hasher = hashlib.sha256()
                    total = 0
                    async for byts in axon.get(sha256):
                        hasher.update(byts)
                        total += len(byts)
                        byts_msg = s_msgpack.en(byts)
                        outfile.write(byts_msg)
                        file_size += len(byts_msg)
                    if total != size:
                        mesg = f'Blob size mismatch for {sha2hex}: expected {size}, got {total}'
                        raise s_exc.BadDataValu(mesg=mesg)
                    if hasher.digest() != sha256:
                        mesg = f'SHA256 mismatch for {sha2hex}'
                        raise s_exc.BadDataValu(mesg=mesg)
                    if file_size >= rotate_size:
                        writeFooterAndClose(outfile, celliden, file_start, offs + 1, file_blobcount, outfile_path, opts.outdir, outp)
                        outfile = None
                        for_open = True
                if outfile is not None:
                    writeFooterAndClose(outfile, celliden, file_start, last_offset + 1, file_blobcount, outfile_path, opts.outdir, outp)
                    outfile = None
            finally:
                if outfile and not outfile.closed:
                    outfile.close()

    except s_exc.SynErr as exc:
        mesg = exc.get('mesg')
        return (False, mesg)

    except Exception as e:
        mesg = f'Error connecting to Axon url: {e}'
        return (False, mesg)

    return (True, None)

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='synapse.tools.axon.dump', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='Telepath URL for the Axon.')
    pars.add_argument('--offset', type=int, default=0, help='Starting offset in the Axon.')
    pars.add_argument('--limit', type=int, default=None, help='Optional ending offset (exclusive).')
    pars.add_argument('--rotate-size', type=int, default=DEFAULT_ROTATE_SIZE,
                      help='Rotate to a new .blobs file if the current file exceeds this size in bytes (default: 4GB).')
    pars.add_argument('outdir', nargs='?', default='.', help='Directory to dump blob files.')

    try:
        opts = pars.parse_args(argv)
    except Exception as e:
        return 1

    if os.path.exists(opts.outdir) and not os.path.isdir(opts.outdir):
        mesg = f'Specified output directory {opts.outdir} exists but is not a directory.'
        outp.printf(f'ERROR: {mesg}')
        return 1

    async with s_telepath.withTeleEnv():
        (ok, mesg) = await dumpBlobs(opts, outp)
        if not ok:
            outp.printf(f'ERROR: {mesg}')
            return 1

    outp.printf(f'Successfully dumped blobs.')

    return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
