import sys
import shlex
import argparse

import synapse.cortex as s_cortex

import synapse.lib.cli as s_cli
import synapse.lib.pki as s_pki

from synapse.common import *

def reprtok(token):
    root = token[1].get('root')

    canstr = ','.join( token[1].get('can',()) )
    if not canstr:
        canstr = '(empty)'

    user = token[1].get('user')
    if user != None:
        return 'user: %s (%s) root: %r can: %s' % (user,token[0],root,canstr)

    host = token[1].get('host')
    if host != None:
        return 'host: %s (%s) root: %r can: %s' % (host,token[0],root,canstr)

class PkiCli(s_cli.Cli):

    def __init__(self, pki):
        s_cli.Cli.__init__(self)

        self.pki = pki
        self.cmdprompt = 'pki> '

    def cmd_export(self, cli, line):
        '''
        Exports certs / tokens / keys from the PkiStor.
        '''
        pars = self.getArgParser('export')
        pars.add_argument('--cert', metavar='iden', help='export cert by iden')
        pars.add_argument('--token', metavar='iden', help='export token by iden')

        opts = pars.parse_args( cli.getLineArgv(line) )

        if opts.cert:

            cert = self.pki.getTokenCert(opts.cert)
            if cert == None:
                cli.vprint('cert not found: %s' % (opts.cert,))
                return

            path = '%s.crt.mpk' % (opts.cert,)
            with open(path,'wb') as fd:
                fd.write(msgenpack(cert))

            cli.vprint('exported: %s' % (path,))

        if opts.token:

            tokn = self.pki.getTokenTufo(opts.token)
            if tokn == None:
                cli.vprint('token not found: %s' % (opts.token,))
                return

            path = '%s.tok.mpk' % (opts.token,)
            with open(path,'wb') as fd:
                fd.write(msgenpack(tokn))

            cli.vprint('exported: %s' % (path,))

    def cmd_import(self, cli, line):
        '''
        Import certs / tokens / keys into the PkiStor.
        '''
        pars = self.getArgParser('import')
        pars.add_argument('--cert', metavar='filename', help='import a cert from file')
        pars.add_argument('--token', metavar='filename', help='import a token from file (danger!)')
        #pars.add_argument('--token', metavar='filename', help='import a token from file (danger!)')

        opts = pars.parse_args( cli.getLineArgv(line) )

        if opts.cert:

            if not os.path.isfile(opts.cert):
                cli.vprint('no such file: %s' % (opts.cert,))
                return

            byts = open(opts.cert,'rb').read()
            cert = msgunpack(byts)
            tokn = self.pki.loadCertToken(cert, save=True)
            if tokn == None:
                cli.vprint('cert trust failed: %s' % (opts.cert,))
            else:
                cli.vprint('loaded %s' % (reprtok(tokn),))

        if opts.token:

            if not os.path.isfile(opts.token):
                cli.vprint('no such file: %s' % (opts.token,))
                return

            byts = open(opts.token,'rb').read()
            tokn = msgunpack(byts)
            self.pki.setTokenTufo(tokn,save=True)
            cli.vprint('loaded %s' % (reprtok(tokn),))

    def cmd_tokgen(self, cli, line):
        '''
        Generate a new token.
        '''
        pars = self.getArgParser('tokgen')

        pars.add_argument('name', help='The humon readable name for the token')
        pars.add_argument('--bits', type=int, default=4096, help='RSA key size in bits')
        pars.add_argument('--can', metavar='tags', help='Comma separated list of "can" rights')
        pars.add_argument('--root', action='store_true', default=False, help='Specify this is a root token')

        opts = pars.parse_args( cli.getLineArgv(line) )

        can = ()
        if opts.can:
            can = opts.can.split(',')

        token = self.pki.genUserToken(opts.name, root=opts.root, can=can, bits=opts.bits, save=True)

        cli.vprint( reprtok(token) )

        return token

    #def do_tokmod(self, line):
        #'''
        #Modify a token in the token store.
        #'''

    def cmd_toklist(self, cli, line):
        '''
        List tokens currently stored.
        '''
        reprs = [ reprtok(t) for t in self.pki.iterTokenTufos() ]
        reprs.sort()

        for r in reprs:
            self.vprint(r)

        self.vprint('(%d tokens)' % (len(reprs),))

    def cmd_useradd(self, cli, line):
        '''
        Create and store a new user token.
        '''
        pars = self.getArgParser('useradd')

        pars.add_argument('user')

        pars.add_argument('--bits', type=int, default=4096, help='RSA key size in bits')
        pars.add_argument('--can', metavar='tags', help='Comma separated list of "can" rights')
        pars.add_argument('--root', action='store_true', default=False, help='Specify this is a root token')

        opts = pars.parse_args( cli.getLineArgv(line) )

        can = ()
        if opts.can:
            can = opts.can.split(',')

        token = self.pki.genUserToken(opts.user, root=opts.root, can=can, bits=opts.bits, save=True)

        cli.vprint( reprtok(token) )

        return token

    def cmd_hostadd(self, cli, line):
        '''
        Create and stor a new host token.
        '''
        pars = self.getArgParser('hostadd')

        pars.add_argument('host')

        pars.add_argument('--bits', type=int, default=4096, help='RSA key size in bits')
        pars.add_argument('--can', metavar='tags', help='Comma separated list of "can" rights')

        opts = pars.parse_args( cli.getLineArgv(line) )

        can = ()
        if opts.can:
            can = opts.can.split(',')

        token = self.pki.genHostToken(opts.host, bits=opts.bits, save=True)

        cli.vprint( reprtok(token) )

        return token

    #def cmd_revoke(self, cli, line):

    #def do_keylist(self, line):

    #def cmd_certgen(self, cli, line):
        #'''
        #Generate a new certificate for an existing token.
        #'''
        #pars = self.getArgParser('certgen')
        #pars.add_argument('--signas', metavar='iden', help='sign cert as the specified iden')
        #pars.add_argument('--file', metavar='filename', help='Specify a save file for the cert bytes')

    #def do_certload(self, line):
        #'''
        #Load a certificate into the Pki from file.
        #'''
        #pars = self.getArgParser('certload')
        #pars.add_argument('filename', help='File name of serialized certificate')
        #pars.add_argument('--dangerzone', action='store_true', default=False, help='Force loading even if cert fails trust (danger zone!)')

        #opts = pars.parse_args( self.getLineArgv(line) )

        #cert = msgunpack( open(opts.filename,'rb').read() )

    #def do_certsave(self, line):
        #'''
        #Save a certificate to file.
        #'''
        #p.add_argument('filename', help='File name of serialized certificate')

def main(argv):
    '''
    Command line tool for Pki management.
    '''
    p = argparse.ArgumentParser(prog='pkitool')
    #p.add_argument('--cortex', metavar='url', default=pkicore, help='Cortex URL for Pki')
    p.add_argument('--onecmd', metavar='cmdline', default=None, help='Issue one command and exit')

    opts = p.parse_args(argv)

    pki = s_pki.getUserPki()

    cli = PkiCli(pki)
    cli.addStdPrint()

    try:

        if opts.onecmd:
            cli.runCmdLine( opts.onecmd )
            return

        cli.runCmdLoop()

    finally:

        cli.fini()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
