import os
import sys
import argparse
import threading

import synapse.cortex as s_cortex
import synapse.neuron as s_neuron

def main(argv):
    '''
    A tool for inititializing neuron options.
    '''
    p = argparse.ArgumentParser(prog='neutool')
    p.add_argument('cortex', default='ram:///', help='Cortex URL for the neuron local storage')

    #p.add_argument('--init-root', default=False, action='store_true', help='Initialize neuron root user')
    #p.add_argument('--init-share', default=None, help='Initialize a shared object in the neuron')
    p.add_argument('--init-name', default=None, help='Initialize the name for the neuron')
    p.add_argument('--init-listen', default=None, help='Initialize a listening server in the neuron')
    p.add_argument('--init-connect', default=None, help='Initialize a connect link in the neuron')

    opts = p.parse_args(argv)

    core = s_cortex.openurl(opts.cortex)
    neuron = s_neuron.Neuron(core=core)

    if opts.init_name:
        neuron.setNeuProp('name', opts.init_name)

    if opts.init_listen:
        print('init listen: %s' % (opts.init_listen,))
        neuron.addNeuListen(opts.init_listen)

    if opts.init_connect:
        print('init connect: %s' % (opts.init_connect,))
        neuron.addNeuConnect(opts.init_connect)

    evt = threading.Event()
    def onfini():
        evt.set()

    neuron.onfini(onfini)

    try:
        evt.wait()
    finally:
        neuron.fini()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
