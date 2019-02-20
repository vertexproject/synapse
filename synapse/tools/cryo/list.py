import sys
import logging
import argparse

import synapse.telepath as s_telepath

import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='cryo.list', description='List tanks within a cryo cell.')
    pars.add_argument('cryocell', nargs='+', help='Telepath URLs to cryo cells.')

    opts = pars.parse_args(argv)

    for url in opts.cryocell:

        outp.printf(url)

        with s_telepath.openurl(url) as cryo:

            for name, info in cryo.list():

                outp.printf(f'    {name}: {info}')

if __name__ == '__main__':  # pragma: no cover
    logging.basicConfig()
    sys.exit(main(sys.argv[1:]))
