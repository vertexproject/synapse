'''
A multi-purpose Daemon runner with optional senses.

Additionally, users may specify a python module

'''
import sys
import argparse
import importlib
import traceback

import synapse.daemon as s_daemon

desc = 'Run a synapse daemon'

def main(argv):

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--initmod',default=[],action='append',help='Specify initSynDaemon(daemon) modules')
    #parser.add_argument('--initfile',default=[],action='append',help='Specify initSynDaemon(daemon) modules')
    #parser.add_arguemtn('--statefile
    parser.add_argument('--link',default=[],action='append',help='Specify synapse link URI to maintain')
    #parser.add_argument('--sense',default=[],action='append',help='Specify synapse sense URI to run')

    args = parser.parse_args(argv)

    daemon = s_daemon.Daemon()
    if len(args.link) == 0:
        print('no links specified! (ex: --link tcpd://0.0.0.0:999/ )')
        return

    # FIXME maybe make this built in?
    for modname in args.initmod:
        mod = importlib.import_module(modname)
        meth = getattr(mod,'initSynDaemon',None)
        if meth == None:
            print('initmod %s must implement initSynDaemon(daemon)' % modname)
            return

        try:
            meth(daemon)
        except Exception as e:
            traceback.print_exc()
            print('initmod %s error: %s' % (modname,e))
            return

    for link in args.link:
        daemon.runLinkUri(link)

    daemon.synWait()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
