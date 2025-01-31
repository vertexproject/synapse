import os
import sys
import glob
import time
import shutil
import fnmatch
import logging
import argparse
import contextlib

import lmdb

import synapse.common as s_common

logger = logging.getLogger(__name__)

def backup(srcdir, dstdir, skipdirs=None):
    '''
    Create a backup of a Synapse application.

    Args:
        srcdir (str): Path to the directory to backup.
        dstdir (str): Path to backup target directory.
        skipdirs (list or None): Optional list of relative directory name glob patterns to exclude from the backup.

    Note:
        Running this method from the same process as a running user of the directory may lead to a segmentation fault
    '''
    with capturelmdbs(srcdir, skipdirs=skipdirs) as lmdbinfo:
        txnbackup(lmdbinfo, srcdir, dstdir, skipdirs=skipdirs)

@contextlib.contextmanager
def capturelmdbs(srcdir, skipdirs=None, onlydirs=None):
    '''
    A context manager that opens all the lmdb files under a srcdir and makes a read transaction.  All transactions are
    aborted and environments closed when the context is exited.

    Yields:
        Dict[str, Tuple[lmdb.Environment, lmdb.Transaction]]: Maps path to environment, transaction
    '''
    if onlydirs:
        lmdbpaths = onlydirs

    else:
        if skipdirs is None:
            skipdirs = []

        srcdir = glob.escape(os.path.abspath(srcdir))
        skipdirs.append(os.path.join(srcdir, 'tmp/*'))
        skipdirs.append(os.path.join(srcdir, '*/tmp/*'))

        srcdirglob = s_common.genpath(srcdir, '**/data.mdb')
        fniter = glob.iglob(srcdirglob, recursive=True)
        lmdbpaths = [os.path.dirname(fn) for fn in fniter if not
                     any([fnmatch.fnmatch(fn, pattern) for pattern in skipdirs])]

    lmdbinfo = {}

    with contextlib.ExitStack() as stack:
        for path in lmdbpaths:
            logger.debug(f'Capturing txn for {path}')
            datafile = os.path.join(path, 'data.mdb')
            stat = os.stat(datafile)
            map_size = stat.st_size
            env = stack.enter_context(
                lmdb.open(path, map_size=map_size, max_dbs=16384, create=False, readonly=True))
            txn = stack.enter_context(env.begin())
            assert path not in lmdbinfo
            lmdbinfo[path] = (env, txn)

        yield lmdbinfo

def txnbackup(lmdbinfo, srcdir, dstdir, skipdirs=None):
    '''
    Create a backup of a Synapse application under a (hopefully consistent) set of transactions.

    Args:
        lmdbinfo(Dict[str, Tuple[lmdb.Environment, lmdb.Transaction]]): Maps of path to environment, transaction
        srcdir (str): Path to the directory to backup.
        dstdir (str): Path to backup target directory.
        skipdirs (list or None): Optional list of relative directory name glob patterns to exclude from the backup.

    Note:
        Running this method from the same process as a running user of the directory may lead to a segmentation fault
    '''
    tick = s_common.now()

    srcdir = s_common.reqdir(srcdir)
    dstdir = s_common.gendir(dstdir)

    if skipdirs is None:
        skipdirs = []

    # Always avoid backing up temporary and backup directories
    skipdirs.append('**/tmp')
    skipdirs.append('**/backups')

    logger.debug(f'Starting backup of [{srcdir}]')
    logger.debug(f'Destination dir: [{dstdir}]')

    for root, dnames, fnames in os.walk(srcdir, topdown=True):

        relpath = os.path.relpath(root, start=srcdir)

        for name in list(dnames):

            srcpath = s_common.genpath(root, name)

            relname = os.path.join(relpath, name)

            if any([fnmatch.fnmatch(relname, pattern) for pattern in skipdirs]):
                logger.debug(f'skipping dir:{srcpath}')
                dnames.remove(name)
                continue

            dstpath = s_common.genpath(dstdir, relname)

            info = lmdbinfo.get(os.path.abspath(srcpath))

            if info is not None:
                logger.debug('backing up lmdb file: %s', srcpath)
                dnames.remove(name)
                env, txn = info
                backup_lmdb(env, dstpath, txn=txn)
                continue

            if name.endswith('.lmdb'):
                logger.warning('lmdb file %s not copied', srcpath)
                dnames.remove(name)
                continue

            logger.debug(f'making dir:{dstpath}')
            s_common.gendir(dstpath)

        for name in fnames:

            srcpath = s_common.genpath(root, name)
            # skip unix sockets etc...
            if not os.path.isfile(srcpath):
                continue

            dstpath = s_common.genpath(dstdir, relpath, name)
            logger.debug(f'copying: {srcpath} -> {dstpath}')
            shutil.copy(srcpath, dstpath)

    tock = s_common.now()

    logger.debug(f'Backup complete. Took [{tock-tick:.2f}] for [{srcdir}]')
    return

def backup_lmdb(env: lmdb.Environment, dstdir: str, txn=None):

    tick = time.time()

    s_common.gendir(dstdir)

    env.copy(dstdir, compact=True, txn=txn)

    tock = time.time()
    logger.info(f'backup of: {env.path()} took: {tock-tick:.2f} seconds')

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
