import sys
import argparse

import synapse.daemon as s_daemon
import synapse.lib.service as s_service

def getArgParser():
    p = argparse.ArgumentParser()
    p.add_argument('url', nargs='+', help='synapse urls to listen on')
    return p

def main(argv):

    p = getArgParser()
    opts = p.parse_args(argv)

    dmon = s_daemon.Daemon()
    sbus = s_service.SvcBus()

    dmon.share('syn.svcbus', sbus)
    for url in opts.url:
        dmon.listen(url)

    dmon.main()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
