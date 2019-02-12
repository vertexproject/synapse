import os
import sys
import logging
import argparse

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.daemon as s_daemon

import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir

logger = logging.getLogger(__name__)

LOG_LEVEL_CHOICES = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

dmonpath = os.getenv('SYN_DMON_PATH')
if dmonpath is None:
    dmonpath = s_common.genpath('~/.syn/dmon')

dmonyaml = '''
listen: tcp://127.0.0.1:27429/

# load python modules on startup
# (allows extensions/modules to register)

#modules:
#   - foo.bar
#   - baz.faz

modules: []

    # default to localhost on an ephemeral port
    #url: tcp://localhost:0/

    # To generate SSL keys/certs check out:
    # python -m synapse.tools.easycert

    #url: ssl://<dnsname>:<port>/
    #opts:

        # Configure a CA cert to force client side certs for auth.
        #cacert: path/to/ca.crt

        # The SSL server cert and key
        #keyfile: path/to/server.key
        #certfile: path/to/server.crt
'''

def getArgParser():
    p = argparse.ArgumentParser()
    p.add_argument('--log-level', choices=LOG_LEVEL_CHOICES, help='specify the log level', type=str.upper)
    p.add_argument('dmonpath', nargs='?', default=dmonpath, help='The dmon directory path. Defaults to ~/.syn/dmon or SYN_DMON_PATH.')
    return p

def main(argv, outp=s_output.stdout):

    argp = getArgParser()
    opts = argp.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    dirn = s_common.gendir(opts.dmonpath)
    outp.printf(f'Beginning dmon from {dirn}')

    # since we're dmon main, register our certdir as global
    certdir = s_common.gendir(dirn, 'certs')

    # set the default certdir to the dmon certdir
    s_certdir.defdir = certdir

    path = os.path.join(dirn, 'dmon.yaml')
    if not os.path.isfile(path):

        with open(path, 'wb') as fd:
            fd.write(dmonyaml.encode('utf8'))

    dmon = None
    try:
        dmon = s_glob.sync(s_daemon.Daemon.anit(opts.dmonpath))
        host, port = dmon.addr
        outp.printf(f'dmon listening on: {host}:{port}')
        dmon.main()
    finally:
        if dmon is not None:
            s_glob.sync(dmon.fini())

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
