import os
import pathlib
import tempfile

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output


async def main(argv, outp=s_output.stdout):
    pars = getArgParser(outp)
    opts = pars.parse_args(argv)

    if opts.output is None:
        opts.output = '.'

    outdir = pathlib.Path(opts.output)

    s_common.gendir(opts.output)

    async with s_telepath.withTeleEnv():

        async with await s_telepath.openurl(opts.axon) as axon:

            # reminder: these are the hashes *not* available

            awants = await axon.wants([s_common.uhex(h) for h in opts.hashes])
            for a in awants:
                outp.printf(f'{s_common.ehex(a)} not in axon store')

            exists = [h for h in opts.hashes if s_common.uhex(h) not in awants]

            for h in exists:

                outp.printf(f'Fetching {h} to file')

                # Fetch into a temp file and atomically move it into place on
                # success so a failed or partial fetch never leaves a file behind.
                tmp = None
                try:
                    fd, tmp = tempfile.mkstemp(dir=outdir, prefix=f'{h}.', suffix='.tmp')
                    with os.fdopen(fd, 'wb') as fobj:
                        async for b in axon.get(s_common.uhex(h)):
                            fobj.write(b)

                    os.replace(tmp, outdir.joinpath(h))
                    tmp = None

                    outp.printf(f'Fetched {h} to file')

                except Exception as e:
                    outp.printf('Error: Hit Exception: %s' % (str(e),))

                finally:
                    if tmp is not None:
                        os.unlink(tmp)

    return 0


def getArgParser(outp):
    desc = 'Fetches file from the given axon'
    pars = s_cmd.Parser(prog='synapse.tools.axon.get', outp=outp, description=desc)
    pars.add_argument('-a', '--axon', type=str, dest='axon', required=True,
                      help='URL to the axon blob store')
    pars.add_argument('-o', '--output', type=str, dest='output',
                      help='Directory to output files to')
    pars.add_argument('-l', '--list-hashes', dest='hashes', action='append', default=[],
                      help='List of hashes to pull from axon')

    return pars

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
