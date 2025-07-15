import cryptography.x509 as c_x509

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir


async def main(argv, outp=s_output.stdout):
    pars = getArgParser(outp)
    opts = pars.parse_args(argv)

    if opts.network:
        s_common.deprecated('--network option.', curv='v2.206.0')

    cdir = s_certdir.CertDir(path=opts.certdir)
    async with s_telepath.withTeleEnv():
        async with await s_telepath.openurl(opts.aha) as prox:

            name = opts.name

            if opts.ca:
                # A User may only have get permissions; so try get first
                # before attempting to generate a new CA.
                certbyts = await prox.getCaCert(name)
                if not certbyts:
                    s_common.deprecated('AHA CA certificate generation.', curv='v2.206.0')
                    certbyts = await prox.genCaCert(name)
                cert = c_x509.load_pem_x509_certificate(certbyts.encode())
                path = cdir._saveCertTo(cert, 'cas', f'{name}.crt')
                outp.printf(f'Saved CA cert to {path}')
                return 0
            elif opts.server:
                csr = cdir.genHostCsr(name, outp=outp)
                certbyts = await prox.signHostCsr(csr.decode(), signas=opts.network, sans=opts.server_sans)
                cert = c_x509.load_pem_x509_certificate(certbyts.encode())
                path = cdir._saveCertTo(cert, 'hosts', f'{name}.crt')
                outp.printf(f'crt saved: {path}')
                cdir.delHostCsr(name, outp=outp)
                return 0
            else:
                csr = cdir.genUserCsr(name, outp=outp)
                certbyts = await prox.signUserCsr(csr.decode(), signas=opts.network)
                cert = c_x509.load_pem_x509_certificate(certbyts.encode())
                path = cdir._saveCertTo(cert, 'users', f'{name}.crt')
                outp.printf(f'crt saved: {path}')
                cdir.delUserCsr(name, outp=outp)
                return 0

def getArgParser(outp):
    desc = 'CLI tool to generate simple x509 certificates from an Aha server.'
    pars = s_cmd.Parser(prog='synapse.tools.aha.easycert', outp=outp, description=desc)

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

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
