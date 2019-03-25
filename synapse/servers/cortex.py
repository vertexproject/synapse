import os
import sys
import asyncio
import logging
import argparse

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.output as s_output

import synapse.servers.cell as s_s_cell

logger = logging.getLogger(__name__)

def parse(argv):

    https = os.getenv('SYN_CORTEX_HTTPS', '4443')
    telep = os.getenv('SYN_CORTEX_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_CORTEX_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cortex')
    pars.add_argument('--telepath', default=telep, help='The telepath URL to listen on.')
    pars.add_argument('--https', default=https, dest='port', type=int, help='The port to bind for the HTTPS/REST API.')
    pars.add_argument('--name', default=telen, help='The (optional) additional name to share the Cortex as.')
    pars.add_argument('coredir', help='The directory for the cortex to use for storage.')

    return pars.parse_args(argv)

async def main(argv, outp=s_output.stdout):

    opts = parse(argv)

    s_common.setlogging(logger)

    core = await s_s_cell.getCell(outp,
                                  opts.coredir,
                                  'synapse.cortex.Cortex',
                                  opts.port,
                                  opts.telepath,
                                  name=opts.name,
                                  desc='cortex'
                                  )

    return core


if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
