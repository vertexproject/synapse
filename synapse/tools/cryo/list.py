import sys
import logging
import asyncio
import argparse

import synapse.telepath as s_telepath

import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='cryo.list', description='List tanks within a cryo cell.')
    pars.add_argument('cryocell', nargs='+', help='Telepath URLs to cryo cells.')

    opts = pars.parse_args(argv)

    for url in opts.cryocell:

        outp.printf(url)

        async with s_telepath.withTeleEnv():

            async with await s_telepath.openurl(url) as cryo:

                for name, info in await cryo.list():
                    outp.printf(f'    {name}: {info}')

    return 0

if __name__ == '__main__':  # pragma: no cover
    logging.basicConfig()
    sys.exit(asyncio.run(main(sys.argv[1:])))
