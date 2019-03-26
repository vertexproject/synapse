import os
import sys
import asyncio
import logging
import argparse

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

logger = logging.getLogger(__name__)


async def getCell(outp,
                  celldir,
                  ctorpath,
                  httpport,
                  telepath,
                  name=None,
                  ):

    outp.printf(f'Resolving cellpath: {ctorpath}')

    ctor = s_dyndeps.getDynLocal(ctorpath)
    if ctor is None:
        raise s_exc.NoSuchCtor(name=ctorpath,
                               mesg='No Cell ctor found.')

    outp.printf(f'starting cell: {celldir}')

    cell = await ctor.anit(celldir)

    try:

        outp.printf(f'...cell API (telepath): {telepath}')
        await cell.dmon.listen(telepath)

        outp.printf(f'...cell API (https): {httpport}')
        await cell.addHttpsPort(httpport)

        if name:
            outp.printf(f'...cell additional share name: {name}')
            cell.dmon.share(name, cell)

        return cell

    except Exception:
        await cell.fini()
        raise


def parse(argv):
    https = os.getenv('SYN_UNIV_HTTPS', '4443')
    telep = os.getenv('SYN_UNIV_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_UNIV_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.cell',
                                   description='A universal Synapse Cell loader.')
    pars.add_argument('--telepath', default=telep, help='The telepath URL to listen on.')
    pars.add_argument('--https', default=https, dest='port', type=int, help='The port to bind for the HTTPS/REST API.')
    pars.add_argument('--name', default=telen, help='The (optional) additional name to share the Cell as.')
    pars.add_argument('cellctor', help='Python class path to use to load the Cell.')
    pars.add_argument('celldir', help='The directory for the Cell to use for storage.')

    return pars.parse_args(argv)


async def main(argv, outp=s_output.stdout):
    opts = parse(argv)

    s_common.setlogging(logger)

    cell = await getCell(outp,
                         opts.celldir,
                         opts.cellctor,
                         opts.port,
                         opts.telepath,
                         name=opts.name,
                         )

    return cell


if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
