import os
import sys
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

logger = logging.getLogger(__name__)


async def getCell(outp, opts):

    outp.printf(f'Resolving cellpath: {opts.cellctor}')

    ctor = s_dyndeps.getDynLocal(opts.cellctor)
    if ctor is None:
        raise s_exc.NoSuchCtor(name=opts.cellctor,
                               mesg='No Cell ctor found.')

    outp.printf(f'Resolving configuration data via envars')
    conf = s_config.Config.getConfFromCell(ctor)
    conf.setConfFromEnvs()

    outp.printf(f'starting cell: {opts.celldir}')

    cell = await ctor.anit(opts.celldir, conf=conf)

    try:

        await s_config.common_cb(cell, opts, outp)

    except Exception:
        await cell.fini()
        raise

    return cell

def parse(argv):
    https = os.getenv('SYN_UNIV_HTTPS', '4443')
    telep = os.getenv('SYN_UNIV_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_UNIV_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cell',
                                   description='A universal Synapse Cell loader.')
    s_config.common_argparse(pars, https=https, telep=telep, telen=telen)
    pars.add_argument('cellctor', help='Python class path to use to load the Cell.')
    pars.add_argument('celldir', help='The directory for the Cell to use for storage.')

    return pars.parse_args(argv)


async def main(argv, outp=s_output.stdout):
    opts = parse(argv)

    s_common.setlogging(logger)

    cell = await getCell(outp, opts)

    return cell


if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
