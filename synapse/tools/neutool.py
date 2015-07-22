import os
import sys
import argparse

import synapse.neuron as s_neuron

def statefd(path):
    fd = open(path,'a+b')
    fd.seek(0)
    return fd

def main(argv):
    '''
    A tool for inititializing neuron options.
    '''
    p = argparse.ArgumentParser(prog='neutool')

    p.add_argument('--init-peer', default=False, action='store_true', help='Init a Peer Neuron')
    p.add_argument('--init-master', default=False, action='store_true', help='Init a Master Neuron')
    p.add_argument('--sign-with', metavar='<file>', default=None, help='Sign with another neuron.mpk')
    p.add_argument('--show-info', default=False, action='store_true')

    p.add_argument('--add-peer', default=[], action='append', help='Add a Peer URL')
    p.add_argument('--add-server', default=[], action='append', help='Add a Server URL')

    p.add_argument('filename')

    opts = p.parse_args(argv)

    fd = statefd(opts.filename)
    neu = s_neuron.Daemon(statefd=fd)

    if opts.init_peer:
        neu.genRsaKey()
        neu.genPeerCert()

    elif opts.init_master:
        neu.genRsaKey()
        neu.genPeerCert(signer=True,master=True)

    if opts.sign_with:
        neu1 = s_neuron.Daemon(statefd=statefd( opts.sign_with ))

        cert = neu.getNeuInfo('peercert')
        cert = neu1.signPeerCert(cert)

        neu.setNeuInfo('peercert',cert)
        neu.addPeerCert( neu1.getNeuInfo('peercert') )

    for servurl in opts.add_server:
        neu.addServerUrl(servurl)

    if opts.show_info:
        keys = neu.neuinfo.keys()
        for key in sorted(keys):
            print('%s: %r' % (key,neu.getNeuInfo(key)))

    neu.fini()
    fd.close()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
