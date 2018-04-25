import os
import sys
import json
import logging
import argparse
import subprocess

import synapse.common as s_common
import synapse.daemon as s_daemon

import synapse.lib.output as s_output
import synapse.lib.thishost as s_thishost

logger = logging.getLogger(__name__)

LOG_LEVEL_CHOICES = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

dmonyaml = '''
listen:

    # default to localhost on an ephemeral port
    url: tcp://localhost:0/

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
    p.add_argument('dir', help='The daemon directory for services and configuration')
    return p

def main(argv, outp=s_output.stdout):

    argp = getArgParser()
    opts = argp.parse_args(argv)

    s_common.setlogging(logger, opts.log_level)

    dirn = s_common.gendir(opts.dir)

    path = os.path.join(dirn, 'dmon.yaml')
    if not os.path.isfile(path):

        with open(path, 'wb') as fd:
            fd.write(dmonyaml.encode('utf8'))

    with s_daemon.Daemon(opts.dir) as dmon:
        dmon.main()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
