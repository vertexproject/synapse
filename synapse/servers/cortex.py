import os
import sys
import json
import socket
import logging
import argparse

import synapse.glob as s_glob

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def parse(argv):

    httpport = os.getenv('SYN_CORTEX_HTTP_PORT')
    httphost = os.getenv('SYN_CORTEX_HTTP_HOST', '0.0.0.0')

    httpsport = os.getenv('SYN_CORTEX_HTTPS_PORT')
    httpshost = os.getenv('SYN_CORTEX_HTTPS_HOST', socket.gethostname())

    insecure = json.loads(os.getenv('SYN_CORTEX_INSECURE', 'false').lower())

    teleport = os.getenv('SYN_CORTEX_PORT', '27492')
    telehost = os.getenv('SYN_CORTEX_HOST', '127.0.0.1')

    insecure = json.loads(os.getenv('SYN_CORTEX_INSECURE', 'false').lower())
    teleport = os.getenv('SYN_CORTEX_PORT', '27492')
    telehost = os.getenv('SYN_CORTEX_HOST', '127.0.0.1')

    pars = argparse.ArgumentParser(prog='synapse.servers.cortex')
    pars.add_argument('--port', default=teleport, help='The TCP port to bind for telepath.')
    pars.add_argument('--host', default=telehost, help='The host address to bind telepath.')

    pars.add_argument('--http-port', default=httpport, help='Set port to bind for the HTTP API.')
    pars.add_argument('--http-host', default=httphost, help='Set the host/addr to bind for the HTTP API.')

    pars.add_argument('--https-host', default=httpshost, help='Set the host/addr to bind for the HTTPS API.')
    pars.add_argument('--https-port', default=httpsport, help='Set port to bind for the HTTPS API.')

    pars.add_argument('--insecure', default=insecure, action='store_true',
                      help='Start the cortex with all auth bypassed (DANGER!).')
    pars.add_argument('coredir', help='The directory for the cortex to use for storage.')

    return pars.parse_args(argv)

def main(argv, outp=s_output.stdout): # pragma: no cover

    opts = parse(argv)

    s_common.setlogging(logger)

    return s_glob.sync(mainopts(opts, outp=outp)).main()

async def mainopts(opts, outp=s_output.stdout):

    lisn = f'tcp://{opts.host}:{opts.port}/cortex'

    outp.printf('starting cortex at: %s' % (lisn,))

    core = await s_cortex.Cortex.anit(opts.coredir)
    core.insecure = opts.insecure

    if core.insecure:
        logger.warning('INSECURE MODE ENABLED')

    await core.dmon.listen(lisn)

    if opts.http_port:
        await core.addHttpPort(int(opts.http_port), host=opts.http_host)

    await core.dmon.listen(lisn)

    return core

if __name__ == '__main__': # pragma: no cover
    sys.exit(main(sys.argv[1:]))
