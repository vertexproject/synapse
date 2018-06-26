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

def backup(srcdir, backupdir):
    tick = s_common.now()
    srcdir = s_common.reqdir(srcdir)
    backupdir = s_common.reqdir(backupdir)
    logger.info(f'Starting backup of [{srcdir}]')
    logger.info(f'Destination dir: [{backupdir}]')

    srcbase = os.path.dirname(srcdir)

    lmdb_dirs = []
    for root, dnames, fnames in os.walk(srcdir, topdown=True):
        relroot = root[len(srcbase) + 1:]

        filter_dirs = []
        for i, dname in enumerate(dnames):
            if dname.endswith('.lmdb'):
                filter_dirs.append(dname)
                continue

        # separate the lmdb directories
        for fname in filter_dirs:
            dnames.remove(fname)
            src = s_common.genpath(root, fname)
            dst = s_common.genpath(backupdir, relroot, fname)
            lmdb_dirs.append((src, dst))

        # make regular directories
        for dname in dnames:
            src = s_common.genpath(root, dname)
            dst = s_common.genpath(backupdir, relroot, dname)
            logger.info(f'making dir:{dst}')
            os.makedirs(dst)

        # copy regular files
        for fname in fnames:
            src = s_common.genpath(root, fname)
            dst = s_common.genpath(backupdir, relroot, fname)
            logger.info(f'copying: {src} -> {dst}')
            shutil.copy(src, dst)

    # backup each lmdb directory
    for src, dst in lmdb_dirs:
        logger.info(f'lmdb backup: {src} -> {dst}')
        backup_lmdb(src, dst)
    tock = s_common.now()
    logger.info(f'Backup complete. Took [{tock-tick:.2f}] for [{srcdir}]')
    return
def blob_00x_check(envpath, backupdir):
    if 'blobs.lmdb' in os.listdir(envpath):
        # Make a another blobs.lmdb on backupdir, then call backup_lmdb and return True
        src = s_common.genpath(envpath, 'blobs.lmdb')
        dst = s_common.genpath(backupdir, 'blobs.lmdb')
        backup_lmdb(src, dst)
        return True
    return False

def backup_lmdb(envpath, backupdir):
    if blob_00x_check(envpath, backupdir):
        return None
    datafile = os.path.join(envpath, 'data.mdb')
    stat = os.stat(datafile)
    map_size = stat.st_size

    parser = lmdb.tool.make_parser()
    opts, args = parser.parse_args(['copy', '--compact', '-e', envpath, backupdir])

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

def main(args):
    if not args.suffix:
        args.suffix = os.path.basename(args.backupdir)

    now_epoch = datetime.datetime.now()
    now = now_epoch.strftime('%Y%m%d%H%M')
    s_common.reqdir(args.backupdir)
    args.outpath = s_common.gendir(args.backupdir, f'backup_{now}_{args.suffix}')

    backup(args.srcdir, args.outpath)
    return 0

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('srcdir', help='Top level directory structure to backup(probably a dmon directory structure)')
    parser.add_argument('backupdir', help='Top level directory to backups in')
    parser.add_argument('--suffix', default=None, help='name to include in the backup directory name')

    args = parser.parse_args(argv)

    return args

def _main(argv):  # pragma: no cover
    args = parse_args(argv)
    s_common.setlogging(logger, defval='DEBUG')
    main(args)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
