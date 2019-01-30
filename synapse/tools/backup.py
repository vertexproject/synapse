import os
import sys
import time
import shutil
import logging
import argparse
import datetime

import lmdb
import lmdb.tool

import synapse.common as s_common

logger = logging.getLogger(__name__)

def backup(srcdir, dstdir):

    tick = s_common.now()

    srcdir = s_common.reqdir(srcdir)
    dstdir = s_common.gendir(dstdir)

    logger.info(f'Starting backup of [{srcdir}]')
    logger.info(f'Destination dir: [{dstdir}]')

    lmdb_dirs = []

    for root, dnames, fnames in os.walk(srcdir, topdown=True):

        relpath = os.path.relpath(root, start=srcdir)

        filter_dirs = []

        for name in list(dnames):

            srcpath = s_common.genpath(root, name)
            dstpath = s_common.genpath(dstdir, relpath, name)

            if name.endswith('.lmdb'):
                dnames.remove(name)
                backup_lmdb(srcpath, dstpath)
                continue

            logger.info(f'making dir:{dstpath}')
            s_common.gendir(dstpath)

        for name in fnames:
            srcpath = s_common.genpath(root, name)
            dstpath = s_common.genpath(dstdir, relpath, name)
            logger.info(f'copying: {srcpath} -> {dstpath}')
            shutil.copy(srcpath, dstpath)

    tock = s_common.now()

    logger.info(f'Backup complete. Took [{tock-tick:.2f}] for [{srcdir}]')
    return

def backup_lmdb(envpath, dstdir):

    datafile = os.path.join(envpath, 'data.mdb')
    stat = os.stat(datafile)
    map_size = stat.st_size

    parser = lmdb.tool.make_parser()
    opts, args = parser.parse_args(['copy', '--compact', '-e', envpath, dstdir])

    env = lmdb.open(
        opts.env,
        map_size=map_size,
        subdir=True,
        max_dbs=opts.max_dbs,
        create=False,
        readonly='READ'
    )

    lmdb.tool.ENV = env
    tick = time.time()

    # use the builtin lmdb command
    lmdb.tool.cmd_copy(opts, args[1:])

    tock = time.time()
    logger.info(f'backup took: {tock-tick:.2f} seconds')

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('srcdir', help='Path to the synapse directory to backup.')
    parser.add_argument('dstdir', help='Path to the backup target directory.')
    args = parser.parse_args(argv)
    return args

def main(argv):
    args = parse_args(argv)
    s_common.setlogging(logger, defval='DEBUG')
    return backup(args.srcdir, args.dstdir)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
