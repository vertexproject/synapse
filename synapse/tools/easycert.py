import os
import sys
import time
import argparse

from OpenSSL import crypto

import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir

from synapse.common import *

descr = '''
Command line tool to generate simple x509 certs
'''

def main(argv, outp=None):

    if outp == None:
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='easycert', description=descr)

    pars.add_argument('--certdir', default='~/.syn/certs', help='Directory for certs/keys')
    pars.add_argument('--signas', help='sign the new cert with the given cert name')
    pars.add_argument('--ca', default=False, action='store_true', help='mark the certificate as a CA/CRL signer')
    pars.add_argument('--server', default=False, action='store_true', help='mark the certificate as a server')
    pars.add_argument('--csr', default=False, action='store_true', help='generate a cert signing request')
    pars.add_argument('--sign-csr', default=False, action='store_true', help='sign a cert signing request')
    pars.add_argument('name', help='common name for the certificate (or filename for CSR signing)')

    opts = pars.parse_args(argv)

    cdir = s_certdir.CertDir(path=opts.certdir)

    try:

        if opts.sign_csr:

            if opts.signas == None:
                outp.printf('--sign-csr requires --signas')
                return -1

            xcsr = cdir._loadCsrPath(opts.name)
            if xcsr == None:
                outp.printf('csr not found: %s' % (opts.name,))
                return -1

            if opts.server:
                cdir.signHostCsr(xcsr, opts.signas, outp=outp)
                return 0

            cdir.signUserCsr(xcsr, opts.signas, outp=outp)
            return 0

        if opts.csr:

            if opts.ca:
                cdir.genCaCsr(opts.name, outp=outp)
                raise Exception('CSR for CA cert not supporte (yet)')

            if opts.server:
                cdir.genHostCsr(opts.name, outp=outp)
                return 0

            cdir.genUserCsr(opts.name, outp=outp)
            return 0

        if opts.ca:
            cdir.genCaCert(opts.name, signas=opts.signas, outp=outp)
            return 0

        if opts.server:
            cdir.genHostCert(opts.name, signas=opts.signas, outp=outp)
            return 0

        cdir.genUserCert(opts.name, signas=opts.signas, outp=outp)
        return 0

    except DupFileName as e:
        outp.printf('file exists: %s' % (e.errinfo.get('path'),))
        return -1

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
