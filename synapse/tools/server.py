import sys
import argparse
import importlib

import synapse.link as s_link
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon

def main(argv):

    p = argparse.ArgumentParser(prog='server')
    #p.add_argument('--initmod',help='python module name for daemon init callback')
    #p.add_argument('--cortex', action='append', default=[], help='cortex name,url to share for RMI')
    p.add_argument('linkurl',nargs='+',help='link urls to bind/listen')

    opts = p.parse_args(argv)

    dmon = s_daemon.Daemon()

    # fire up requested link servers
    for url in opts.linkurl:
        dmon.listen(url)

    dmon.main()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
