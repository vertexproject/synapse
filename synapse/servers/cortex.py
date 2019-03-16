import os
import sys
import json
import asyncio
import logging
import argparse


import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def parse(argv):

    httpsport = os.getenv('SYN_CORTEX_HTTPS_PORT', '56443')
    httpshost = os.getenv('SYN_CORTEX_HTTPS_HOST', '0.0.0.0')

    insecure = json.loads(os.getenv('SYN_CORTEX_INSECURE', 'false').lower())

    teleport = os.getenv('SYN_CORTEX_PORT', '27492')
    telehost = os.getenv('SYN_CORTEX_HOST', '127.0.0.1')

    pars = argparse.ArgumentParser(prog='synapse.servers.cortex')
    pars.add_argument('--port', default=teleport, help='The TCP port to bind for telepath.')
    pars.add_argument('--host', default=telehost, help='The host address to bind telepath.')

    pars.add_argument('--https-host', default=httpshost, help='Set the host/addr to bind for the HTTPS API.')
    pars.add_argument('--https-port', default=httpsport, help='Set port to bind for the HTTPS API.')

    pars.add_argument('--insecure', default=insecure, action='store_true',
                      help='Start the cortex with all auth bypassed (DANGER!).')

    pars.add_argument('coredir', help='The directory for the cortex to use for storage.')

    return pars.parse_args(argv)

async def main(argv, outp=s_output.stdout):

    opts = parse(argv)

    s_common.setlogging(logger)

    lisn = f'tcp://{opts.host}:{opts.port}/cortex'

    core = await s_cortex.Cortex.anit(opts.coredir)

    try:

        core.insecure = opts.insecure

        if core.insecure:
            logger.warning('INSECURE MODE ENABLED')

        outp.printf('starting cortex at: %s' % (lisn,))

        await core.dmon.listen(lisn)

        await core.addHttpsPort(opts.https_port)

        return core

    except Exception:
        await core.fini()
        raise

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
