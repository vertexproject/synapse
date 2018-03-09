import os
import sys
import socket
import getpass
import argparse

import synapse.common as s_common
import synapse.neuron as s_neuron

import synapse.lib.cell as s_cell
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

def genauth(opts, outp=s_output.stdout):

    authpath = s_common.genpath(opts.authfile)
    savepath = s_common.genpath(opts.savepath)

    if not os.path.isfile(authpath):
        outp.printf('auth file not found: %s' % (authpath,))
        return

    auth = s_msgpack.loadfile(authpath)

    addr = auth[1].get('neuron')
    if addr is None:
        outp.printf('auth file has no neuron info: %s' % (authpath, ))
        return

    celluser = s_cell.CellUser(auth)

    with celluser.open(addr, timeout=20) as sess:

        nuro = s_neuron.NeuronClient(sess)
        auth = nuro.genCellAuth(opts.cellname, timeout=20)

        s_msgpack.dumpfile(auth, savepath)

        outp.printf('saved %s: %s' % (opts.cellname, savepath))

def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser('synapse.tools.neuron', description='Various commands and tools for neuron administration.')

    subs = pars.add_subparsers(title='subcommands', dest='subcmd')

    gena = subs.add_parser('genauth', description='Generate an auth file for a neuron cell.')
    gena.add_argument('authfile', help='Specify the path to an auth file used to connect to the neuron.')
    gena.add_argument('cellname', help='The cell name you wish to provision.  Ex. axon00@cells.vertex.link')
    gena.add_argument('savepath', help='The file path used to save the generated auth data.')
    gena.set_defaults(func=genauth)

    opts = pars.parse_args(argv)
    if opts.subcmd is None:
        outp.printf(pars.format_help())
        return

    opts.func(opts, outp=outp)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
