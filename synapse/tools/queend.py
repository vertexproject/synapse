import sys
import argparse

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.hivemind as s_hivemind

def main(argv):

    p = argparse.ArgumentParser()
    #p.add_argument('--debug', default=False)
    p.add_argument('--listen', default='tcp://0.0.0.0:30056')

    opts = p.parse_args(argv)

    queen = s_hivemind.Queen()

    dmon = s_daemon.Daemon()

    dmon.share('syn.queen', queen)
    dmon.listen(opts.listen)

    dmon.main()
    queen.fini()

if __name__ == '__main__':
    sys.exit( main(sys.argv[1:]) )
