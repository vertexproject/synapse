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

def gencsr(opts,outp):

    certdir = gendir(opts.certdir)

    csrpath = os.path.join(certdir,'%s.csr' % opts.name)
    pkeypath = os.path.join(certdir,'%s.key' % opts.name)

    if os.path.exists(csrpath):
        outp.printf('csr exists: %s' % (csrpath,))
        return(-1)

    if os.path.exists(pkeypath):
        outp.printf('key exists: %s' % (pkeypath,))
        return(-1)

    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 2048)


    xcsr = crypto.X509Req()
    subj = xcsr.get_subject()

    subj.CN = opts.name

    xcsr.set_pubkey(pkey)
    xcsr.sign(pkey,'sha256')

    byts = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

    with genfile(pkeypath) as fd:
        fd.write(byts)

    outp.printf('pkey saved: %s' % (pkeypath,))

    byts = crypto.dump_certificate_request(crypto.FILETYPE_PEM, xcsr)

    with genfile(csrpath) as fd:
        fd.write(byts)

    outp.printf('csr saved: %s' % (csrpath,))

    return 0

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

            byts = reqbytes(opts.name)
            xcsr = crypto.load_certificate_request(crypto.FILETYPE_PEM,byts)

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

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
