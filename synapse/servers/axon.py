import os
import sys
import asyncio
import logging
import argparse

import synapse.axon as s_axon
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def getParser():

    https = os.getenv('SYN_AXON_HTTPS', '4443')
    telep = os.getenv('SYN_AXON_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_AXON_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.servers.axon')
    s_config.common_argparse(pars, https=https, telep=telep, telen=telen, cellname='Axon')
    return pars

async def main(argv, outp=s_output.stdout, axonctor=None):

    if axonctor is None:
        axonctor = s_axon.Axon

    pars = getParser()
    axon = await s_config.main(axonctor,
                               argv,
                               pars=pars,
                               cb=s_config.common_cb,
                               outp=outp,
                               )
    return axon

if __name__ == '__main__': # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))
