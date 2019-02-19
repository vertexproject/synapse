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
import synapse.lib.certdir as s_certdir

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

def main(argv, outp=s_output.stdout): # pragma: no cover

    opts = parse(argv)

    s_common.setlogging(logger)

    return s_glob.sync(mainopts(opts, outp=outp)).main()

async def mainopts(opts, outp=s_output.stdout):

    lisn = f'tcp://{opts.host}:{opts.port}/cortex'

    core = await s_cortex.Cortex.anit(opts.coredir)
    core.insecure = opts.insecure

    if core.insecure:
        logger.warning('INSECURE MODE ENABLED')

    outp.printf('starting cortex at: %s' % (lisn,))

    await core.dmon.listen(lisn)

    # check for certs or gen self signed
    keypath = os.path.join(opts.coredir, 'sslkey.pem')
    certpath = os.path.join(opts.coredir, 'sslcert.pem')

    if not os.path.isfile(certpath):
        logger.warning('NO CERTIFICATE FOUND! generating self-signed certificate.')
        with s_common.getTempDir() as dirn:
            cdir = s_certdir.CertDir(dirn)
            pkey, cert = cdir.genHostCert('cortex')
            cdir.savePkeyPem(pkey, keypath)
            cdir.saveCertPem(cert, certpath)

    outp.printf(f'loading SSL key from: {keypath}')
    outp.printf(f'loading SSL cert from: {certpath}')

    sslctx = core.initSslCtx(certpath, keypath)

    await core.addHttpPort(int(opts.https_port), host=opts.https_host, ssl=sslctx)

    return core

if __name__ == '__main__': # pragma: no cover
    sys.exit(main(sys.argv[1:]))
