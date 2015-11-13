import sys
import argparse
import multiprocessing as mproc

import synapse.link as s_link
import synapse.hivemind as s_hivemind
import synapse.telepath as s_telepath

def main(argv):

    p = argparse.ArgumentParser()
    p.add_argument('--size', default=mproc.cpu_count(), type=int, help='Number of parallel work units to run')
    p.add_argument('queenurl', help='synapse link URL to connect to queen')

    args = p.parse_args(argv)

    queen = s_telepath.openurl(args.queenurl)
    worker = s_hivemind.Worker(queen, size=args.size)

    try:
        worker.wait()
    finally:
        worker.fini()

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:]) )
