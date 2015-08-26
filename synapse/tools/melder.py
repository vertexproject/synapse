import sys
import msgpack
import argparse

import synapse.mindmeld as s_mindmeld

from synapse.common import *

def main(argv):
    '''
    Command line tool for MindMeld construction/manipulation.
    '''

    p = argparse.ArgumentParser(prog='melder')
    p.add_argument('meldfile',help='meld file path')

    p.add_argument('--add-pypath', dest='pypaths', default=[], action='append', help='add a python path to the meld')
    p.add_argument('--add-datfiles', dest='datfiles', action='store_true', help='when adding pypath, include datfiles')

    p.add_argument('--dump-info', dest='dumpinfo', action='store_true', help='dump the entire meld info dictionary to stdout')

    p.add_argument('--set-name', dest='name', default=None, help='set meld name (ie, "foolib")')
    p.add_argument('--set-version', dest='version', default=None, help='set meld version (ie, 8.2.30)')

    opts = p.parse_args(argv)

    meldinfo = {}
    if os.path.isfile(opts.meldfile):
        with open(opts.meldfile,'rb') as fd:
            meldinfo = msgpack.load(fd,encoding='utf8')

    meld = s_mindmeld.MindMeld(**meldinfo)

    if opts.version:
        meld.setVersion(vertup(opts.version))

    if opts.name:
        meld.setName(opts.name)

    for pypath in opts.pypaths:
        meld.addPyPath(pypath,datfiles=opts.datfiles)

    meldinfo = meld.getMeldDict()
    if opts.dumpinfo:
        print(repr(meldinfo))

    meldbyts = msgpack.dumps( meld.getMeldDict(), encoding='utf8', use_bin_type=True )
    with open(opts.meldfile,'wb') as fd:
        fd.write(meldbyts)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
