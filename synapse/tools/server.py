import sys
import argparse
import importlib

import synapse.link as s_link
import synapse.telepath as s_telepath

def main(argv):

    p = argparse.ArgumentParser(prog='server')
    p.add_argument('--initmod',help='python module name for daemon init callback')
    p.add_argument('linkurl',nargs='+',help='link urls to bind/listen')

    opts = p.parse_args(argv)

    daemon = s_telepath.Daemon()
    for url in opts.linkurl:
        link = s_link.chopLinkUrl(url)
        daemon.runLinkServer(link)

    if opts.initmod:
        mod = importlib.import_module(opts.initmod)
        meth = getattr(mod,'initDaemon',None)
        if meth == None:
            print('error: initmod (%s) has no initDaemon() function!')
            return

        # call back the daemon init module
        meth(daemon)

    daemon.wait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
