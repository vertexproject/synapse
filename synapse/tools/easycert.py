import os
import sys
import time
import argparse

from OpenSSL import crypto

from synapse.common import gendir,genfile

descr = '''
Command line tool to generate simple x509 certs
'''

def main(argv):

    pars = argparse.ArgumentParser(prog='easycert', description=descr)

    pars.add_argument('--certdir', default='~/.syn/certs', help='Directory for certs/keys')
    pars.add_argument('--signas', help='sign the new cert with the given cert name')
    pars.add_argument('--ca', default=False, action='store_true', help='mark the certificate as a CA/CRL signer')
    pars.add_argument('--server', default=False, action='store_true', help='mark the certificate as a server')
    pars.add_argument('name', help='common name for the certificate')

    opts = pars.parse_args(argv)

    certdir = gendir(opts.certdir)

    pkeypath = os.path.join(certdir,'%s.key' % opts.name)
    certpath = os.path.join(certdir,'%s.crt' % opts.name)

    if os.path.exists(pkeypath):
        print('key exists: %s' % (pkeypath,))
        return(-1)

    if os.path.exists(certpath):
        print('cert exists: %s' % (certpath,))
        return(-1)

    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 2048)

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
    subj.CN = opts.name

    signcert = cert
    signpkey = pkey

    if opts.signas:
        path = os.path.join(certdir,'%s.key' % (opts.signas,))
        byts = open(path,'rb').read()
        signpkey = crypto.load_privatekey(crypto.FILETYPE_PEM, byts)

        path = os.path.join(certdir,'%s.crt' % (opts.signas,))
        byts = open(path,'rb').read()
        signcert = crypto.load_certificate(crypto.FILETYPE_PEM, byts)

    cert.set_issuer( signcert.get_subject() )
    cert.sign( signpkey, 'sha1' )

    byts = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

    with genfile(pkeypath) as fd:
        fd.write(byts)

    print('pkey saved: %s' % (pkeypath,))

    byts = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    with genfile(certpath) as fd:
        fd.write(byts)

    print('cert saved: %s' % (certpath,))

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
