import os
import glob
import time
import shutil
import fnmatch
import zipfile
import logging
import argparse
import threading
import contextlib

import lmdb

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.urlhelp as s_urlhelp

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
            txn = env.begin()
            # register abort() (idempotent) rather than the context-manager exit
            # (which commits) so callers may abort a read txn early to release its
            # snapshot without a later double-close crash.
            stack.callback(txn.abort)
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

    logger.debug(f'Backup complete. Took [{tock - tick:.2f}] for [{srcdir}]')
    return

def backup_lmdb(env: lmdb.Environment, dstdir: str, txn=None):

    tick = time.time()

    s_common.gendir(dstdir)

    env.copy(dstdir, compact=True, txn=txn)

    tock = time.time()
    logger.info(f'backup of: {env.path()} took: {tock - tick:.2f} seconds')

def iterslabzip(lmdbinfo, srcdir, fileobj, arcbase='backup', skipdirs=None):
    '''
    Stream a consistent Synapse backup as a zip archive into ``fileobj`` using the
    pinned lmdb read transactions in ``lmdbinfo``.

    Each captured ``data.mdb`` is streamed via a compacting ``env.copyfd()`` into a
    zip entry written with a data descriptor, so the member size need not be known
    up front. Plain files are copied verbatim. The archive contains a single root
    directory with all backup members below it.

    Args:
        lmdbinfo (dict): Maps slab dir path to ``(env, txn)`` (see ``capturelmdbs``).
        srcdir (str): The service directory being backed up.
        fileobj: A writable binary file object to receive the zip bytes.
        arcbase (str): The archive root directory name.
        skipdirs (list or None): Additional relative dir glob patterns to skip.

    Returns:
        int: The total uncompressed size of the archive members (the on-disk
        footprint of the backup once extracted).
    '''
    srcdir = s_common.reqdir(srcdir)

    if skipdirs is None:
        skipdirs = []

    # Always avoid backing up temporary and backup directories
    skipdirs.append('**/tmp')
    skipdirs.append('**/backups')

    with zipfile.ZipFile(fileobj, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:

        for root, dnames, fnames in os.walk(srcdir, topdown=True):

            relpath = os.path.relpath(root, start=srcdir)

            for name in list(dnames):

                srcpath = s_common.genpath(root, name)
                # keep the './' form (os.path.join with a '.' relpath) so the
                # '**/tmp' and '**/backups' globs match top-level dirs too.
                relname = os.path.join(relpath, name)

                if any(fnmatch.fnmatch(relname, pattern) for pattern in skipdirs):
                    dnames.remove(name)
                    continue

                info = lmdbinfo.get(os.path.abspath(srcpath))
                if info is not None:
                    dnames.remove(name)
                    env, txn = info
                    # normpath collapses the leading './' for top-level entries so
                    # the archive members are clean 'backup/<rel>'.
                    arcname = os.path.normpath(os.path.join(arcbase, relname, 'data.mdb'))
                    _copyslabzip(zf, env, txn, arcname)
                    # release this snapshot now that its copy is complete so the
                    # live writer can reclaim its freed pages.
                    txn.abort()
                    continue

                if name.endswith('.lmdb'):
                    logger.warning('lmdb file %s not copied', srcpath)
                    dnames.remove(name)
                    continue

            for name in fnames:

                srcpath = s_common.genpath(root, name)
                # skip unix sockets etc...
                if not os.path.isfile(srcpath):
                    continue

                relname = os.path.join(relpath, name)
                zf.write(srcpath, arcname=os.path.normpath(os.path.join(arcbase, relname)))

    return sum(zinfo.file_size for zinfo in zf.infolist())

def _copyslabzip(zf, env, txn, arcname):

    rfd, wfd = os.pipe()
    exc = []

    def _copy():
        try:
            env.copyfd(wfd, compact=True, txn=txn)
        except BaseException as e:
            exc.append(e)
        finally:
            os.close(wfd)

    thread = threading.Thread(target=_copy, daemon=True)
    thread.start()

    zinfo = zipfile.ZipInfo(arcname)
    zinfo.compress_type = zipfile.ZIP_DEFLATED

    try:
        with zf.open(zinfo, mode='w', force_zip64=True) as dest:
            while True:
                chunk = os.read(rfd, 1024 * 1024)
                if not chunk:
                    break

                dest.write(chunk)

        thread.join()
        if exc:
            raise exc[0]

    finally:
        os.close(rfd)
        thread.join()

async def _urlBackup(url, dstpath, outp):
    sanitized = s_urlhelp.sanitizeUrl(url)
    async with s_telepath.withTeleEnv():
        async with await s_telepath.openurl(url) as cell:
            outp.printf(f'Running backup of: {sanitized}')
            with s_common.genfile(dstpath) as fd:
                async for mtyp, minfo in cell.initBackupStream():
                    if mtyp == 'data':
                        fd.write(minfo)
                        continue

                    if mtyp == 'init':
                        outp.printf(f'...backup nexus offset: {minfo.get("nexsoffs")}')
                        continue

                    if mtyp == 'fini':
                        outp.printf(f'...backup created: {dstpath} '
                                    f'(size={minfo.get("size")}, sha256={minfo.get("sha256")})')
                        continue

                    if mtyp == 'err':
                        mesg = minfo.get('errmsg', 'backup stream error')
                        outp.printf(f'ERROR: backup of {sanitized} failed: {mesg}')
                        return 1

    return 0

async def main(argv, outp=s_output.stdout):
    args = parse_args(argv)

    # a telepath URL contains a scheme separator; a filesystem path does not.
    if '://' in args.source:
        return await _urlBackup(args.source, args.dstdir, outp)

    backup(args.source, args.dstdir, args.skipdirs)
    return 0

def parse_args(argv):
    desc = 'Create an optimized backup of a Synapse service, from a local directory or a running service URL.'
    parser = argparse.ArgumentParser('synapse.tools.service.backup', description=desc)
    parser.add_argument('source', help='Path to a Synapse directory, or a telepath URL of a running Synapse service.')
    parser.add_argument('dstdir', help='Backup target: a directory when backing up a local path, '
                                       'or a .zip file path when backing up a service URL.')
    parser.add_argument('--skipdirs', nargs='+',
                        help='Glob patterns of relative directory names to exclude from the backup (local path only).')
    args = parser.parse_args(argv)
    return args

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
