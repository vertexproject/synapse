import os
import sys
import asyncio
import logging
import argparse

import synapse.axon as s_axon
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def parse(argv):

    https = os.getenv('SYN_AXON_HTTPS', '4443')
    telep = os.getenv('SYN_AXON_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_AXON_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.axon')
    pars.add_argument('--telepath', default=telep, help='The telepath URL to listen on.')
    pars.add_argument('--https', default=https, dest='port', type=int, help='The port to bind for the HTTPS/REST API.')
    pars.add_argument('--name', default=telen, help='The (optional) additional name to share the Axon as.')
    pars.add_argument('axondir', help='The directory for the axon to use for storage.')

    return pars.parse_args(argv)

async def main(argv, outp=s_output.stdout, axonctor=None):

    opts = parse(argv)

    if axonctor is None:
        axonctor = s_axon.Axon.anit

    s_common.setlogging(logger)

    outp.printf('starting axon: %s' % (opts.axondir,))

    axon = await axonctor(opts.axondir)

    try:

        outp.printf('...axon API (telepath): %s' % (opts.telepath,))
        await axon.dmon.listen(opts.telepath)

        outp.printf('...axon API (https): %s' % (opts.port,))
        await axon.addHttpsPort(opts.port)

        if opts.name:
            outp.printf(f'...axon additional share name: {opts.name}')
            axon.dmon.share(opts.name, axon)

        return axon

    except Exception:
        await axon.fini()
        raise

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
