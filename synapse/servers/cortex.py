import os
import sys
import asyncio
import logging
import argparse

import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def getParser():

    https = os.getenv('SYN_CORTEX_HTTPS', '4443')
    telep = os.getenv('SYN_CORTEX_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_CORTEX_NAME', None)
    mirror = os.getenv('SYN_CORTEX_MIRROR', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cortex')
    s_config.common_argparse(pars, https=https, telep=telep, telen=telen, cellname='Cortex')
    pars.add_argument('--mirror', default=mirror, help='Mirror splices from the given cortex. (we must be a backup!)')

    return pars

async def cb(cell, opts, outp):

    await s_config.common_cb(cell, opts, outp)

    if opts.mirror:
        outp.printf(f'initializing cortex mirror of: {opts.mirror}')
        await cell.initCoreMirror(opts.mirror)

async def main(argv, outp=s_output.stdout):
    pars = getParser()
    core = await s_config.main(s_cortex.Cortex, argv,
                               pars=pars, cb=cb, outp=outp)
    return core

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
