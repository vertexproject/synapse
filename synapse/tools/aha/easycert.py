import sys
import asyncio
import logging
import argparse
import contextlib

from OpenSSL import crypto

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

# FIXME - set the correct version prior to release.
# reqver = '>=2.26.0,<3.0.0'

async def _main(argv, outp):
    pars = getArgParser()
    opts = pars.parse_args(argv)

    cdir = s_certdir.CertDir(path=opts.certdir)

    async with await s_telepath.openurl(opts.aha) as prox:

        # try:
        #     s_version.reqVersion(prox._getSynVers(), reqver)
        # except s_exc.BadVersion as e:  # pragma: no cover
        #     valu = s_version.fmtVersion(*e.get('valu'))
        #     outp.printf(f'Proxy version {valu} is outside of the aha supported range ({reqver}).')
        #     return 1

        name = opts.name

        if opts.ca:
            # A User may only have get permissions; so try get first
            # before attempting to generate a new CA.
            certbyts = await prox.getCaCert(name)
            if not certbyts:
                certbyts = await prox.genCaCert(name)
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, certbyts)
            path = cdir._saveCertTo(cert, 'cas', f'{name}.crt')
            outp.printf(f'Saved CA cert to {path}')
            return 0
        elif opts.server:
            csr = cdir.genHostCsr(name, outp=outp)
            certbyts = await prox.signHostCsr(csr.decode(), signas=opts.network, sans=opts.server_sans)
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, certbyts)
            path = cdir._saveCertTo(cert, 'hosts', f'{name}.crt')
            outp.printf(f'crt saved: {path}')
            return 0
        else:
            csr = cdir.genUserCsr(name, outp=outp)
            certbyts = await prox.signUserCsr(csr.decode(), signas=opts.network)
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, certbyts)
            path = cdir._saveCertTo(cert, 'users', f'{name}.crt')
            outp.printf(f'crt saved: {path}')
            return 0

def getArgParser():
    desc = 'CLI tool to generate simple x509 certificates from an Aha server.'
    pars = argparse.ArgumentParser(prog='aha.easycert', description=desc)

    pars.add_argument('-a', '--aha', required=True,  # type=str,
                      help='Aha server to connect too.')

    pars.add_argument('--certdir', default='~/.syn/certs', help='Directory for certs/keys')

    pars.add_argument('--ca', default=False, action='store_true',
                      help='Generate a new, or get a existing, CA certificate by name.')
    pars.add_argument('--server', default=False, action='store_true', help='mark the certificate as a server')
    pars.add_argument('--server-sans', help='server cert subject alternate names')

    pars.add_argument('--network', default=None, action='store', type=str,
                      help='Network name to use when signing a CSR')

    pars.add_argument('name', help='common name for the certificate (or filename for CSR signing)')

    return pars

async def main(argv, outp=None):  # pragma: no cover

    if outp is None:
        outp = s_output.stdout

    s_common.setlogging(logger, 'WARNING')

    path = s_common.getSynPath('telepath.yaml')
    async with contextlib.AsyncExitStack() as ctx:

        telefini = await s_telepath.loadTeleEnv(path)
        if telefini is not None:
            ctx.push_async_callback(telefini)

        await _main(argv, outp)

    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))
