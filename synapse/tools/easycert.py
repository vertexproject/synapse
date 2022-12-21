
import sys
import argparse


import synapse.exc as s_exc
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir

descr = '''
Command line tool to generate simple x509 certs
'''

def main(argv, outp=None):

    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='easycert', description=descr)
    pars.add_argument('--certdir', default='~/.syn/certs', help='Directory for certs/keys')
    pars.add_argument('--importfile', choices=('cas', 'hosts', 'users'), help='import certs and/or keys into local certdir')

    pars.add_argument('--ca', default=False, action='store_true', help='mark the certificate as a CA/CRL signer')
    pars.add_argument('--crl', default=False, action='store_true', help='Generate a new CRL for the given CA name.')
    pars.add_argument('--p12', default=False, action='store_true', help='mark the certificate as a p12 archive')
    pars.add_argument('--code', default=False, action='store_true', help='mark the certificate for use in code signing.')
    pars.add_argument('--server', default=False, action='store_true', help='mark the certificate as a server')
    pars.add_argument('--server-sans', help='server cert subject alternate names')

    pars.add_argument('--csr', default=False, action='store_true', help='generate a cert signing request')
    pars.add_argument('--sign-csr', default=False, action='store_true', help='sign a cert signing request')
    pars.add_argument('--signas', help='sign the new cert with the given cert name')
    pars.add_argument('--revokeas', help='Revoke a cert as the given CA and add it to the CSR.')

    pars.add_argument('name', help='common name for the certificate (or filename for CSR signing)')

    opts = pars.parse_args(argv)

    cdir = s_certdir.CertDir(path=opts.certdir)

    try:

        if opts.crl:

            crl = cdir.genCaCrl(opts.name)
            crl._save()

            outp.printf(f'CRL saved: {crl.path}')

            return 0

        if opts.revokeas:

            if opts.code:
                cert = cdir.getCodeCert(opts.name)

            elif opts.server:
                cert = cdir.getHostCert(opts.name)

            elif opts.ca:
                cert = cdir.getCaCert(opts.name)

            else:
                cert = cdir.getUserCert(opts.name)

            if cert is None:
                outp.printf(f'Certificate not found: {opts.name}')
                return 1

            crl = cdir.genCaCrl(opts.revokeas)
            try:
                crl.revoke(cert)
            except s_exc.SynErr as e:
                outp.printf(f'Failed to revoke certificate: {e.get("mesg")}')
                return 1

            outp.printf(f'Certificate revoked: {opts.name}')
            outp.printf(f'CRL updated: {opts.revokeas}')

            return 0

        if opts.importfile:
            cdir.importFile(opts.name, opts.importfile, outp=outp)
            return 0

        if opts.p12:

            cdir.genClientCert(opts.name, outp=outp)
            return 0

        if opts.sign_csr:

            if opts.signas is None:
                outp.printf('--sign-csr requires --signas')
                return -1

            xcsr = cdir._loadCsrPath(opts.name)
            if xcsr is None:
                outp.printf('csr not found: %s' % (opts.name,))
                return -1

            if opts.server:
                cdir.signHostCsr(xcsr, opts.signas, outp=outp)
                return 0

            cdir.signUserCsr(xcsr, opts.signas, outp=outp)
            return 0

        if opts.csr:

            if opts.ca:
                raise NotImplementedError('CSR for CA cert not supported (yet)')

            if opts.server:
                cdir.genHostCsr(opts.name, outp=outp)
                return 0

            cdir.genUserCsr(opts.name, outp=outp)
            return 0

        if opts.ca:
            cdir.genCaCert(opts.name, signas=opts.signas, outp=outp)
            return 0

        if opts.server:
            cdir.genHostCert(opts.name, signas=opts.signas, outp=outp, sans=opts.server_sans)
            return 0

        if opts.code:
            cdir.genCodeCert(opts.name, signas=opts.signas, outp=outp)
            return 0

        cdir.genUserCert(opts.name, signas=opts.signas, outp=outp)
        return 0

    except s_exc.DupFileName as e:
        outp.printf('file exists: %s' % (e.errinfo.get('path'),))
        return -1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
