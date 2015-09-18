import sys
import argparse

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.hivemind as s_hivemind

def main(argv):

    p = argparse.ArgumentParser()
    p.add_argument('linkurl', nargs='+', help='synapse link URLs to listen on')

    args = p.parse_args(argv)

    dmon = s_daemon.Daemon()
    for linkurl in args.linkurl:
        link = s_link.chopLinkUrl(linkurl)
        dmon.runLinkServer(link)

    queen = s_hivemind.Queen( dmon )
    dmon.addSharedObject('queen', queen)

    try:
        queen.wait()
    finally:
        dmon.fini()
        queen.fini()

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:]) )
