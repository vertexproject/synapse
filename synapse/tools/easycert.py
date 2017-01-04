import os
import sys
import time
import argparse

from OpenSSL import crypto

import synapse.lib.output as s_output

from synapse.common import gendir,genfile,reqbytes

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
    pars.add_argument('--gen-csr', default=False, action='store_true', help='generate a cert signing request')
    pars.add_argument('--sign-csr', default=False, action='store_true', help='sign a cert signing request')
    pars.add_argument('name', help='common name for the certificate (or filename for CSR signing)')

    opts = pars.parse_args(argv)

    cname = opts.name

    pkey = None
    savepkey = True

    if opts.gen_csr:
        return gencsr(opts,outp)

    if opts.sign_csr:

        if opts.signas == None:
            outp.printf('--sign-csr requires --signas')
            return -1

        savepkey = False

        byts = reqbytes(opts.name)
        xcsr = crypto.load_certificate_request(crypto.FILETYPE_PEM,byts)

        cname = xcsr.get_subject().CN
        pkey = xcsr.get_pubkey()


    if pkey == None:
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 2048)

    certdir = gendir(opts.certdir)

    pkeypath = os.path.join(certdir,'%s.key' % cname)
    certpath = os.path.join(certdir,'%s.crt' % cname)

    if savepkey and os.path.exists(pkeypath):
        outp.printf('key exists: %s' % (pkeypath,))
        return(-1)

    if os.path.exists(certpath):
        outp.printf('cert exists: %s' % (certpath,))
        return(-1)

    cert = crypto.X509()
    cert.set_pubkey(pkey)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_serial_number( int(time.time()) )

    if opts.ca:

        ext0 = crypto.X509Extension(b'basicConstraints',False,b'CA:TRUE')
        cert.add_extensions([ext0])

    else:

        keyuse = [b'digitalSignature']
        extuse = [b'clientAuth']
        certtype = b'client'


        if opts.server:
            certtype = b'server'
            extuse = [b'serverAuth']
            keyuse.append(b'keyEncipherment')

        ext0 = crypto.X509Extension(b'nsCertType',False,certtype)
        ext1 = crypto.X509Extension(b'keyUsage',False,b','.join(keyuse))

        extuse = b','.join(extuse)
        ext2 = crypto.X509Extension(b'extendedKeyUsage',False,extuse)
        ext3 = crypto.X509Extension(b'basicConstraints',False,b'CA:FALSE')

        cert.add_extensions([ext0,ext1,ext2,ext3])

    subj = cert.get_subject()
    subj.CN = cname

    signcert = cert
    signpkey = pkey

    if opts.signas:
        byts = reqbytes(certdir,'%s.key' % (opts.signas,))
        signpkey = crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

        byts = reqbytes(certdir,'%s.crt' % (opts.signas,))
        signcert = crypto.load_certificate(crypto.FILETYPE_PEM, byts)

    cert.set_issuer( signcert.get_subject() )
    cert.sign( signpkey, 'sha256' )

    if savepkey:

        byts = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

        with genfile(pkeypath) as fd:
            fd.write(byts)

        outp.printf('pkey saved: %s' % (pkeypath,))

    byts = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    with genfile(certpath) as fd:
        fd.write(byts)

    outp.printf('cert saved: %s' % (certpath,))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
