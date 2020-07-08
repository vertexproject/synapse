import os
import sys
import time
import shutil
import fnmatch
import logging
import argparse

import lmdb

import synapse.common as s_common

logger = logging.getLogger(__name__)

def backup(srcdir, dstdir, skipdirs=None, compact=True):
    '''
    Create a backup of a Synapse application.

    Args:
        srcdir (str): Path to the directory to backup.
        dstdir (str): Path to backup target directory.
        skipdirs (list or None): Optional list of relative directory name glob patterns to exclude from the backup.
        compact (bool): Whether to optimize storage while copying to the destination.
    '''
    tick = s_common.now()

    srcdir = s_common.reqdir(srcdir)
    dstdir = s_common.gendir(dstdir)

    if skipdirs is None:
        skipdirs = []

    # Always avoid backing up temporary directories
    skipdirs.append('**/tmp')

    logger.info(f'Starting backup of [{srcdir}]')
    logger.info(f'Destination dir: [{dstdir}]')

    for root, dnames, fnames in os.walk(srcdir, topdown=True):

        relpath = os.path.relpath(root, start=srcdir)

        for name in list(dnames):

            srcpath = s_common.genpath(root, name)

            relname = os.path.join(relpath, name)

            if any([fnmatch.fnmatch(relname, pattern) for pattern in skipdirs]):
                logger.info(f'skipping dir:{srcpath}')
                dnames.remove(name)
                continue

            dstpath = s_common.genpath(dstdir, relname)

            if name.endswith('.lmdb'):
                dnames.remove(name)
                backup_lmdb(srcpath, dstpath, compact)
                continue

            logger.info(f'making dir:{dstpath}')
            s_common.gendir(dstpath)

        for name in fnames:

            srcpath = s_common.genpath(root, name)
            # skip unix sockets etc...
            if not os.path.isfile(srcpath):
                continue

            dstpath = s_common.genpath(dstdir, relpath, name)
            logger.info(f'copying: {srcpath} -> {dstpath}')
            shutil.copy(srcpath, dstpath)

    tock = s_common.now()

    logger.info(f'Backup complete. Took [{tock-tick:.2f}] for [{srcdir}]')
    return

def backup_lmdb(envpath, dstdir, compact=True):

    datafile = os.path.join(envpath, 'data.mdb')
    stat = os.stat(datafile)
    map_size = stat.st_size

    env = lmdb.open(
        envpath,
        map_size=map_size,
        subdir=True,
        max_dbs=256,
        create=False,
        readonly='READ'
    )

    tick = time.time()

    s_common.gendir(dstdir)

    env.copy(dstdir, compact=compact)

    tock = time.time()
    logger.info(f'backup took: {tock-tick:.2f} seconds')
    env.close()

def main(argv):
    args = parse_args(argv)
    backup(args.srcdir, args.dstdir, args.skipdirs)
    return 0

def parse_args(argv):
    desc = 'Create an optimized backup of a Synapse directory.'
    parser = argparse.ArgumentParser('synapse.tools.backup', description=desc)
    parser.add_argument('srcdir', help='Path to the Synapse directory to backup.')
    parser.add_argument('dstdir', help='Path to the backup target directory.')
    parser.add_argument('--skipdirs', nargs='+',
                        help='Glob patterns of relative directory names to exclude from the backup.')
    args = parser.parse_args(argv)
    return args

def _main(argv):  # pragma: no cover
    s_common.setlogging(logger, defval='DEBUG')
    return main(argv)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
