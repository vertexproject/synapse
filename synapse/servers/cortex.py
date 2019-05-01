import os
import sys
import asyncio
import logging
import argparse

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def parse(argv):

    https = os.getenv('SYN_CORTEX_HTTPS', '4443')
    telep = os.getenv('SYN_CORTEX_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_CORTEX_NAME', None)
    mirror = os.getenv('SYN_CORTEX_MIRROR', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cortex')
    pars.add_argument('--telepath', default=telep, help='The telepath URL to listen on.')
    pars.add_argument('--https', default=https, dest='port', type=int, help='The port to bind for the HTTPS/REST API.')
    pars.add_argument('--mirror', default=mirror, help='Mirror splices from the given cortex. (we must be a backup!)')
    pars.add_argument('--name', default=telen, help='The (optional) additional name to share the Cortex as.')
    pars.add_argument('coredir', help='The directory for the cortex to use for storage.')

    return pars.parse_args(argv)

async def main(argv, outp=s_output.stdout):

    opts = parse(argv)

    s_common.setlogging(logger)

    outp.printf('starting cortex: %s' % (opts.coredir,))

    core = await s_cortex.Cortex.anit(opts.coredir)

    try:

        outp.printf('...cortex API (telepath): %s' % (opts.telepath,))
        await core.dmon.listen(opts.telepath)

        outp.printf('...cortex API (https): %s' % (opts.port,))
        await core.addHttpsPort(opts.port)

        if opts.name:
            outp.printf(f'...cortex additional share name: {opts.name}')
            core.dmon.share(opts.name, core)

        if opts.mirror:
            outp.printf(f'initializing cortex mirror of: {opts.mirror}')
            await core.initCoreMirror(opts.mirror)

        return core

    except Exception:
        await core.fini()
        raise

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
