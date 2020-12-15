import sys
import asyncio
import pathlib
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output


async def main(argv, outp=None):

    pars = setup()
    opts = pars.parse_args(argv)

    path = s_common.getSynPath('telepath.yaml')
    telefini = await s_telepath.loadTeleEnv(path)

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    if opts.output is None:
        opts.output = '.'

    outdir = pathlib.Path(opts.output)

    s_common.gendir(opts.output)

    async with await s_telepath.openurl(opts.axon) as axon:

        # reminder: these are the hashes *not* available

        awants = await axon.wants([s_common.uhex(h) for h in opts.hashes])
        for a in awants:
            outp.printf(f'{s_common.ehex(a)} not in axon store')

        exists = [h for h in opts.hashes if s_common.uhex(h) not in awants]

        for h in exists:

            try:
                outp.printf(f'Fetching {h} to file')

                with open(outdir.joinpath(h), 'wb') as fd:
                    async for b in axon.get(s_common.uhex(h)):
                        fd.write(b)

                outp.printf(f'Fetched {h} to file')

            except Exception as e:
                outp.printf('Error: Hit Exception: %s' % (str(e),))
                continue

    if telefini: # pragma: no cover
        await telefini()

    return 0


def setup():
    desc = 'Fetches file from the given axon'
    pars = argparse.ArgumentParser('synapse.tools.pullfile', description=desc)
    pars.add_argument('-a', '--axon', type=str, dest='axon', required=True,
                      help='URL to the axon blob store')
    pars.add_argument('-o', '--output', type=str, dest='output',
                      help='Directory to output files to')
    pars.add_argument('-l', '--list-hashes', dest='hashes', action='append', default=[],
                      help='List of hashes to pull from axon')

    return pars


if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
