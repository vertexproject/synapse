import os
import re
import sys
import asyncio
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

descr = '''
Load blobs into a Synapse Axon.
'''

async def loadBlobs(opts, outp, blobsfiles):
    try:
        async with await s_telepath.openurl(opts.url) as axon:

            cellinfo = await axon.getCellInfo()
            celltype = cellinfo['cell']['type']
            if "axon" not in celltype.lower():
                mesg = f'Axon load tool only works on axons, not {celltype}'
                raise s_exc.TypeMismatch(mesg=mesg)

            for blobsfile in blobsfiles:
                outp.printf(f'Processing blobs file: {blobsfile}')
                with open(blobsfile, 'rb') as fd:
                    msgit = s_msgpack.iterfd(fd)
                    for mesg in msgit:
                        match mesg:
                            case ("blob:init", meta):
                                outp.printf(f"Loading blobs file: {meta}")
                                continue
                            case ("blob:fini", meta):
                                outp.printf(f"Finished loading: {meta}")
                                break
                            case ("blob", meta):
                                sha2hex = meta['sha256']
                                size = meta['size']
                                sha256 = s_common.uhex(sha2hex)
                                hasher = hashlib.sha256()
                                total = 0
                                bytelist = []
                                while True:
                                    try:
                                        byts = next(msgit)
                                    except StopIteration:
                                        mesg = f'Unexpected end of file while reading blob {sha2hex}'
                                        raise s_exc.BadDataValu(mesg=mesg)
                                    if type(byts) is tuple:
                                        msgit = (i for i in [byts] + list(msgit))
                                        break
                                    hasher.update(byts)
                                    total += len(byts)
                                    bytelist.append(byts)
                                    if total >= size:
                                        break
                                if total != size:
                                    mesg = f'Blob size mismatch for {sha2hex}: expected {size}, got {total}'
                                    raise s_exc.BadDataValu(mesg=mesg)
                                if hasher.digest() != sha256:
                                    mesg = f'SHA256 mismatch for {sha2hex}'
                                    raise s_exc.BadDataValu(mesg=mesg)
                                outp.printf(f'Loading blob {sha2hex} (size={size})')
                                async with await axon.upload() as upfd:
                                    for byts in bytelist:
                                        await upfd.write(byts)
                                    await upfd.save()
                            case _:
                                mtype = mesg[0]
                                mesg = f'Unexpected message type: {mtype}.'
                                raise s_exc.BadMesgFormat(mesg=mesg)

    except s_exc.SynErr as exc:
        mesg = exc.get('mesg')
        return (False, mesg)

    except Exception as e:
        mesg = f'Error {e} loading blobs into Axon url: {opts.url}'
        return (False, mesg)

    return (True, None)

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='synapse.tools.axon.load', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='Telepath URL for the Axon.')
    pars.add_argument('files', nargs='+', help='List of .blobs files to import from.')

    try:
        opts = pars.parse_args(argv)
    except Exception:
        return 1

    blobsfiles = opts.files

    async with s_telepath.withTeleEnv():
        (ok, mesg) = await loadBlobs(opts, outp, blobsfiles)
        if not ok:
            outp.printf(f'ERROR: {mesg}')
            return 1

    outp.printf('Successfully loaded blobs.')

    return 0

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))
