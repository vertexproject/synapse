import tarfile

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.const as s_const
import synapse.lib.output as s_output

descr = '''
Load blobs into a Synapse Axon.
'''

DEFAULT_CHUNK_SIZE = s_const.mebibyte * 16

async def loadBlobs(opts, outp, tarfiles):

    try:
        async with await s_telepath.openurl(opts.url) as axon:

            cellinfo = await axon.getCellInfo()
            celltype = cellinfo['cell']['type']
            if "axon" not in celltype.lower():
                mesg = f'Axon load tool only works on axons, not {celltype}'
                raise s_exc.TypeMismatch(mesg=mesg)

            for tarfile_path in tarfiles:
                outp.printf(f'Processing tar archive: {tarfile_path}')
                with tarfile.open(tarfile_path, 'r:gz') as tar:
                    for member in tar:
                        if not member.name.endswith('.blob'):
                            continue
                        sha2hex = member.name[:-5]
                        try:
                            sha256 = s_common.uhex(sha2hex)
                        except Exception:
                            outp.printf(f"Skipping invalid blob filename: {member.name}")
                            continue
                        if await axon.has(sha256):
                            outp.printf(f"Skipping existing blob {sha2hex}")
                            continue
                        outp.printf(f"Loading blob {sha2hex} (size={member.size})")
                        try:
                            fobj = tar.extractfile(member)
                        except OSError as e:
                            outp.printf(f"WARNING: Error extracting {member.name}: {e}")
                            continue
                        if fobj is None:
                            outp.printf(f"Failed to extract {member.name} from tar archive.")
                            continue
                        async with await axon.upload() as upfd:
                            while True:
                                chunk = fobj.read(DEFAULT_CHUNK_SIZE)
                                if not chunk:
                                    break
                                await upfd.write(chunk)
                            await upfd.save()

    except s_exc.SynErr as exc:
        return (False, s_exc.reprexc(exc))

    except Exception as e:
        mesg = f'Error {e} loading blobs into Axon url: {opts.url}'
        return (False, mesg)

    return (True, None)

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='synapse.tools.axon.load', outp=outp, description=descr)
    pars.add_argument('--url', default='cell:///vertex/storage', help='Telepath URL for the Axon.')
    pars.add_argument('files', nargs='+', help='List of .tar.gz files to import from.')

    opts = pars.parse_args(argv)

    tarfiles = sorted([f for f in opts.files if f.endswith('.tar.gz')])

    async with s_telepath.withTeleEnv():
        (ok, mesg) = await loadBlobs(opts, outp, tarfiles)
        if not ok:
            outp.printf(f'ERROR: {mesg}')
            return 1

    outp.printf('Successfully loaded blobs.')

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
