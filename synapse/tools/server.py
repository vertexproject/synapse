import sys
import argparse
import importlib

import synapse.link as s_link
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon

def main(argv):

    p = argparse.ArgumentParser(prog='server')
    p.add_argument('--initmod',help='python module name for daemon init callback')
    p.add_argument('--cortex', action='append', default=[], help='cortex name,url to share for RMI')
    p.add_argument('linkurl',nargs='+',help='link urls to bind/listen')

    opts = p.parse_args(argv)

    daemon = s_daemon.Daemon()

    for nameurl in opts.cortex:
        name,url = nameurl.split(',',1)
        core = s_cortex.openurl(url)
        daemon.addSharedObject(name,core)

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

    try:
        daemon.wait()
    except KeyboardInterrupt as e:
        print('ctrl-c caught: shutting down')
        daemon.fini()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
