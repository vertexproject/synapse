import os
import cmd
import sys
import shlex
import pprint
import argparse

import synapse.neuron as s_neuron
import synapse.eventbus as s_eventbus
import synapse.datamodel as s_datamodel

class Cmd(cmd.Cmd,s_eventbus.EventBus):

    def __init__(self, neu):
        cmd.Cmd.__init__(self)
        self.prompt = 'neu> '

        s_eventbus.EventBus.__init__(self)

        self.neu = neu

        self._cmd_print = True

        moddef = self.neu.getModelDict()
        self.model = s_datamodel.DataModel(model=moddef)

    def getArgParser(self):
        return argparse.ArgumentParser()

    def banner(self):
        '''
        Print the initial hello/banner from the neuron.
        '''
        peer = self.neu.getPeerTufo()
        name = peer[1].get('neuron:name','<unnamed>')
        self.vprint('Connected To: %s (%s)' % (name,peer[0]))

    def vprint(self, msg):
        if self._cmd_print:
            print(msg)

        self.fire('cmd:print', msg=msg)

    def do_set(self, line):
        '''
        Set a property on the current neuron.

        Usage:

            neu> set [options] <prop> <valu>

        Options:

            --force     - Set an option which is *not* part of the data model

        Example:

            neu> set name "foo bar"

        '''
        pars = self.getArgParser()
        pars.add_argument('--force', default=False, action='store_true', help='Set a non-datamodel property')
        pars.add_argument('prop', help='property name')
        pars.add_argument('valu', help='property value')

        opts = pars.parse_args( shlex.split(line) )

        fullprop = 'neuron:%s' % opts.prop

        if self.model.getPropDef(fullprop) == None and not opts.force:
            self.vprint('unknown neuron property: %s' % (opts.prop,))
            return

        try:
            realvalu = self.model.getPropParse(fullprop,opts.valu)
        except Exception as e:
            self.vprint('Invalid Value: %s (%s)' % (opts.valu,e))

        self.neu.setNeuProp(opts.prop,realvalu)
        self.vprint('%s -> %s' % (opts.prop, opts.valu))

    def do_mesh(self, line):
        '''
        Pretty print the entire neuron mesh dictionary.

        Example:

        '''
        mesh = self.neu.getMeshDict()
        outp = pprint.pformat(mesh)
        self.vprint(outp)

    def do_peers(self, line):
        '''
        List the known neuron peers.

        Example:

            neu> list

        '''
        mesh = self.neu.getMeshDict()
        peers = list( mesh.get('peers',{}).values() )
        if len(peers) == 0:
            return self.vprint('no peers?!?!')

        for peer in peers:
            name = peer[1].get('neuron:name')
            self.vprint('%s: %s' % (peer[0],name))

    #def do_quit(self):

def main(argv):
    '''
    A tool for inititializing neuron options.
    '''
    p = argparse.ArgumentParser(prog='neutool')

    p.add_argument('url', help='Neuron telepath URL')

    opts = p.parse_args(argv)

    neu = s_neuron.openurl( opts.url )

    cli = Cmd(neu)

    cli.banner()
    cli.cmdloop()

    neu.fini()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
