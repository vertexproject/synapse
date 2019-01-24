import sys
import argparse
import binascii

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output


def main(argv, outp=None):
    pars = setup()
    opts = pars.parse_args(argv)

    if outp is None:
        outp = s_output.OutPut()

    if opts.output is None:
        opts.output = '.'

    s_common.gendir(opts.output)

    with s_telepath.openurl(opts.axon) as axon:
        if not axon:
            raise s_exc.SynErr(mesg='Failed to connect to Axon')

        # reminder: these are the hashes *not* available
        awants = axon.wants([binascii.unhexlify(h) for h in opts.hashes])
        for a in awants:
            outp.printf(f'{binascii.hexlify(a)} not in axon store')

        exists = [h for h in opts.hashes if binascii.unhexlify(h) not in awants]

        for h in exists:

            try:
                outp.printf(f'Fetching {h} to file')
                with open(f'{opts.output}/{h}', 'wb') as fd:
                    for b in axon.get(binascii.unhexlify(h)):
                        fd.write(b)
                outp.printf(f'Fetched {h} to file')
            except Exception as e:
                outp.printf('Error: Hit Exception: %s' % (str(e),))
                continue

    return 0


def setup():
    desc = 'Fetches file from the given axon'
    pars = argparse.ArgumentParser('pullfile', description=desc)
    pars.add_argument('-a', '--axon', type=str, dest='axon', required=True,
                      help='URL to the axon blob store')
    pars.add_argument('-o', '--output', type=str, dest='output',
                      help='Directory to output files to')
    pars.add_argument('-l', '--list-hashes', dest='hashes',
                      help='List of hashes to pull from axon')

    return pars


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
