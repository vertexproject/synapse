import os
import sys
import asyncio
import logging
import argparse

import synapse.common as s_common
import synapse.cryotank as s_cryotank

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def getParser():

    https = os.getenv('SYN_CRYOTANK_HTTPS', '4443')
    telep = os.getenv('SYN_CRYOTANK_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_CRYOTANK_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cryotank')
    pars.add_argument('--telepath', default=telep, help='The telepath URL to listen on.')
    pars.add_argument('--https', default=https, dest='port', type=int, help='The port to bind for the HTTPS/REST API.')
    pars.add_argument('--name', default=telen, help='The (optional) additional name to share the Cryotank as.')
    pars.add_argument('cryodir', help='The directory for the cryotank server to use for storage.')

    return pars

async def main(argv, outp=s_output.stdout):

    s_common.setlogging(logger)

    pars = getParser()

    conf = s_config.Config.getConfFromCell(s_cryotank.CryoCell)
    conf.getArgparser(pars=pars)

    opts = pars.parse_args(argv)

    conf.setConfFromOpts(opts)
    conf.setConfFromEnvs()

    outp.printf('starting cryotank server: %s' % (opts.cryodir,))

    cryo = await s_cryotank.CryoCell.anit(opts.cryodir, conf=conf)

    try:

        outp.printf('...cryotank API (telepath): %s' % (opts.telepath,))
        await cryo.dmon.listen(opts.telepath)

        outp.printf('...cryotank API (https): %s' % (opts.port,))
        await cryo.addHttpsPort(opts.port)

        if opts.name:
            outp.printf(f'...cryotank additional share name: {opts.name}')
            cryo.dmon.share(opts.name, cryo)

        return cryo

    except Exception:
        await cryo.fini()
        raise

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
