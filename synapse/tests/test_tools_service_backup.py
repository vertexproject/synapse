import io
import os
import socket
import hashlib
import zipfile
import unittest.mock as mock

import synapse.common as s_common
import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

import synapse.tools.service.backup as s_backup

def _boomProc(datasock, srcdir, logconf, info):
    with datasock.makefile('wb') as fd:
        fd.write(s_msgpack.en(('init', info)))
        try:
            raise RuntimeError('boom')
        except RuntimeError as e:
            fd.write(s_msgpack.en(('err', s_common.excinfo(e))))
    datasock.close()

def _boomProcHandoff(ctrlsock, callersock, srcdir, logconf, info):
    with ctrlsock.makefile('wb') as fd:
        fd.write(s_msgpack.en(('captured', None)))
    with callersock.makefile('wb') as fd:
        fd.write(s_msgpack.en(('t2:yield', {'retn': (True, ('init', info))})))
        try:
            raise RuntimeError('boom')
        except RuntimeError as e:
            fd.write(s_msgpack.en(('t2:yield', {'retn': (True, ('err', s_common.excinfo(e)))})))
        fd.write(s_msgpack.en(('t2:yield', {'retn': None})))
    ctrlsock.close()
    callersock.close()

def _extractzip(zippath, dstdir):
    # extract a backup zip into dstdir, stripping the leading 'backup/' component
    with zipfile.ZipFile(zippath) as zf:
        for zinfo in zf.infolist():
            if zinfo.filename.find('/') == -1:
                continue

            zinfo.filename = zinfo.filename.split('/', 1)[1]
            zf.extract(zinfo, dstdir)

class BackupTest(s_t_utils.SynTest):

    def dirset(self, sdir, skipfns, skipdirs):
        ret = set()
        for fdir, dns, fns in os.walk(sdir):

            for dn in list(dns):
                if dn in skipdirs:
                    dns.remove(dn)

            for fn in fns:

                if fn in skipfns:
                    continue

                fp = os.path.join(fdir, fn)
                if not os.path.isfile(fp) and not os.path.isdir(fp):
                    continue

                fp = fp[len(sdir):]
                ret.add(fp)

        return ret

    def compare_dirs(self, dir1, dir2, skipfns=None, skipdirs=None):
        if skipfns is None:
            skipfns = set()

        if skipdirs is None:
            skipdirs = set()

        set1 = self.dirset(dir1, skipfns, skipdirs)
        set2 = self.dirset(dir2, skipfns, set())
        self.gt(len(set1), 1)
        self.gt(len(set2), 1)
        self.eq(set1, set2)
        return set1

    async def test_backup(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                layriden = core.getLayer().iden

                # For additional complication, open a Slab that shouldn't be backed up
                slabpath = s_common.gendir(dirn, 'tmp', 'test.lmdb')
                async with await s_lmdbslab.Slab.anit(slabpath) as slab:
                    foo = slab.initdb('foo')
                    await slab.put(b'\x00\x01', b'hehe', db=foo)

            with self.getTestDir() as dirn2:

                argv = (core.dirn, dirn2)

                self.eq(0, await s_backup.main(argv))

                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs={'tmp'})
                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))

                # We expect the data.mdb file to be in the fpset
                self.isin(f'/layers/{layriden}/layer_v2.lmdb/data.mdb', fpset)

            # Test corner case no-lmdbinfo
            with self.getTestDir() as dirn2:
                with self.getLoggerStream('synapse.tools.service.backup') as stream:
                    s_backup.txnbackup({}, core.dirn, dirn2)
                    stream.seek(0)
                    self.isin('not copied', stream.read())

    async def test_backup_url(self):

        # a telepath URL source streams a live backup via initBackupStream
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[inet:ip=1.2.3.4]'))
            url = core.getLocalUrl()

            with self.getTestDir() as dirn2:
                dstpath = s_common.genpath(dirn2, 'backup.zip')

                outp = self.getTestOutp()
                self.eq(0, await s_backup.main((url, dstpath), outp=outp))
                self.true(os.path.isfile(dstpath))

                outp.expect('backup nexus offset:')
                outp.expect('backup created:')

                # the streamed archive can boot a working cortex
                with self.getTestDir() as extdir:
                    _extractzip(dstpath, extdir)

                    async with self.getTestCore(dirn=extdir) as core2:
                        self.len(1, await core2.nodes('inet:ip=1.2.3.4'))

    async def test_backup_url_err(self):

        # a terminal err message from the stream makes the tool exit non-zero
        async with self.getTestCore() as core:
            url = core.getLocalUrl()

            with self.getTestDir() as dirn2:
                dstpath = s_common.genpath(dirn2, 'backup.zip')

                outp = self.getTestOutp()
                with mock.patch.object(s_cell.Cell, '_backupProcHandoff', staticmethod(_boomProcHandoff)):
                    self.eq(1, await s_backup.main((url, dstpath), outp=outp))

                outp.expect('ERROR: backup of')

    async def test_iterslabzip(self):
        # iterslabzip streams a zip directly from pinned read txns: it captures
        # real slabs, skips tmp/backups and stray .lmdb dirs, copies plain files,
        # and the captured slab restores from the streamed member.
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')

            slabdir = s_common.genpath(srcdir, 'slabs', 'foo.lmdb')
            async with await s_lmdbslab.Slab.anit(slabdir) as slab:
                db = slab.initdb('t')
                await slab.put(b'k', b'v', db=db)

            # a stray .lmdb dir (no data.mdb) that must be warned about and skipped
            s_common.gendir(srcdir, 'stray.lmdb')
            # a tmp dir that must be excluded from the archive
            s_common.gendir(srcdir, 'tmp', 'junk')
            with s_common.genfile(srcdir, 'cell.guid') as fd:
                fd.write(b'0' * 32)
            # a non-regular file (unix socket / fifo) that must be skipped
            os.mkfifo(s_common.genpath(srcdir, 'sock'))

            outpath = s_common.genpath(dirn, 'out.zip')
            with s_backup.capturelmdbs(srcdir) as lmdbinfo:
                with open(outpath, 'wb') as fd:
                    rawsize = s_backup.iterslabzip(lmdbinfo, srcdir, fd)

            with zipfile.ZipFile(outpath) as zf:
                names = zf.namelist()
                # the return value is the total uncompressed size of the members
                self.gt(rawsize, 0)
                self.eq(rawsize, sum(zinfo.file_size for zinfo in zf.infolist()))

            self.true(any(n.endswith('slabs/foo.lmdb/data.mdb') for n in names))
            self.true(any(n.endswith('cell.guid') for n in names))
            self.false(any('stray.lmdb' in n for n in names))
            self.false(any('tmp' in n.split('/') for n in names))

            # the captured slab restores from the streamed member
            with self.getTestDir() as extdir:
                _extractzip(outpath, extdir)
                async with await s_lmdbslab.Slab.anit(s_common.genpath(extdir, 'slabs', 'foo.lmdb')) as slab2:
                    self.len(1, list(slab2.scanByFull(db=slab2.initdb('t'))))

    async def test_iterslabzip_maxsize(self):
        # a slab with maxsize set restores cleanly from the streamed compact copy.
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')
            slabdir = s_common.genpath(srcdir, 'foo.lmdb')
            async with await s_lmdbslab.Slab.anit(slabdir, maxsize=1024 * 1024 * 1024) as slab:
                db = slab.initdb('t')
                for i in range(500):
                    await slab.put(f'k{i:04d}'.encode(), b'v' * 400, db=db)
                for i in range(0, 500, 2):
                    slab.pop(f'k{i:04d}'.encode(), db=db)
                await slab.sync()

            outpath = s_common.genpath(dirn, 'out.zip')
            with s_backup.capturelmdbs(srcdir) as lmdbinfo:
                with open(outpath, 'wb') as fd:
                    s_backup.iterslabzip(lmdbinfo, srcdir, fd)

            with self.getTestDir() as extdir:
                _extractzip(outpath, extdir)
                async with await s_lmdbslab.Slab.anit(s_common.genpath(extdir, 'foo.lmdb'),
                                                      maxsize=1024 * 1024 * 1024) as slab2:
                    self.len(250, list(slab2.scanByFull(db=slab2.initdb('t'))))

    async def test_copyslabzip_err(self):
        # an error raised by copyfd surfaces out of _copyslabzip
        class FakeEnv:
            def copyfd(self, fd, compact=False, txn=None):
                raise RuntimeError('copyfd boom')

        with zipfile.ZipFile(io.BytesIO(), mode='w') as zf:
            with self.raises(RuntimeError):
                s_backup._copyslabzip(zf, FakeEnv(), None, 'backup/foo.lmdb/data.mdb')

    async def test_backupwriter_chunks(self):
        # _BackupWriter batches bytes into ('data', chunk) messages of at most chunksize
        # (emitting full chunks as it fills and the remainder on flush), passing them to
        # the emit callable, and computes the running size and sha256.
        msgs = []
        writer = s_cell._BackupWriter(msgs.append, chunksize=1024)
        payload = bytes(range(200)) * 15  # 3000 bytes -> 2 full chunks + a remainder
        self.eq(len(payload), writer.write(payload))
        writer.flush()

        self.eq(3, len(msgs))
        self.true(all(m[0] == 'data' for m in msgs))
        self.eq(payload, b''.join(m[1] for m in msgs))
        self.eq(len(payload), writer.size)
        self.eq(hashlib.sha256(payload).hexdigest(), writer.sha256.hexdigest())

    def _drainProc(self, parent_sock):
        # decode the child's msgpack (type, info) messages from the data socket
        unpk = s_msgpack.Unpk()
        msgs = []
        while True:
            byts = parent_sock.recv(65536)
            if not byts:
                break
            msgs.extend(item for (_, item) in unpk.feed(byts))
        parent_sock.close()
        return msgs

    async def test_backupproc(self):
        # the backup subprocess pins the read txns, then writes msgpack messages to
        # the data socket: ('init', <info>) -> ('data', ...) -> ('fini', ...). The
        # data reassembles into a valid zip archive matching the fini size/sha256.
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')
            async with await s_lmdbslab.Slab.anit(s_common.genpath(srcdir, 'foo.lmdb')) as slab:
                await slab.put(b'k', b'v', db=slab.initdb('t'))
            with s_common.genfile(srcdir, 'cell.guid') as fd:
                fd.write(b'0' * 32)

            info = {'nexsoffs': 42, 'iden': 'a' * 32, 'type': 'cell', 'name': None}

            # a small archive fits in the socket buffer, so the in-process child does
            # not block writing before we read.
            parent_sock, child_sock = socket.socketpair()
            with mock.patch.object(s_cell.s_logging, 'setup'):
                s_cell.Cell._backupProc(child_sock, srcdir, {}, info)

            msgs = self._drainProc(parent_sock)

            # the child echoes the metadata it was given in its init message
            self.eq(('init', info), msgs[0])
            self.eq('fini', msgs[-1][0])
            self.isin('data', [m[0] for m in msgs])

            data = b''.join(m[1] for m in msgs if m[0] == 'data')
            fini = msgs[-1][1]
            self.eq(len(data), fini['size'])
            self.eq(hashlib.sha256(data).hexdigest(), fini['sha256'])

            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                # fini rawsize is the uncompressed size of the archive members
                self.gt(fini['rawsize'], 0)
                self.eq(fini['rawsize'], sum(zinfo.file_size for zinfo in zf.infolist()))
            self.true(any(n.endswith('foo.lmdb/data.mdb') for n in names))

    async def test_backupproc_err(self):
        # a failure inside the backup subprocess is reported as an ('err', ...) message
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')
            async with await s_lmdbslab.Slab.anit(s_common.genpath(srcdir, 'foo.lmdb')):
                pass

            def _boom(*args, **kwargs):
                raise RuntimeError('iter boom')

            parent_sock, child_sock = socket.socketpair()
            with mock.patch.object(s_backup, 'iterslabzip', _boom):
                with mock.patch.object(s_cell.s_logging, 'setup'):
                    s_cell.Cell._backupProc(child_sock, srcdir, {}, {})

            msgs = self._drainProc(parent_sock)

            self.eq('init', msgs[0][0])
            self.eq('err', msgs[-1][0])
            self.eq('RuntimeError', msgs[-1][1]['err'])

    async def test_backupprochandoff(self):
        # the handoff subprocess signals 'captured' on the control channel then writes
        # telepath t2:yield frames (init/data/fini + terminal) to the caller socket.
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')
            async with await s_lmdbslab.Slab.anit(s_common.genpath(srcdir, 'foo.lmdb')) as slab:
                await slab.put(b'k', b'v', db=slab.initdb('t'))
            with s_common.genfile(srcdir, 'cell.guid') as fd:
                fd.write(b'0' * 32)

            info = {'nexsoffs': 42, 'iden': 'a' * 32, 'type': 'cell', 'name': None}

            ctrl_parent, ctrl_child = socket.socketpair()
            caller_parent, caller_child = socket.socketpair()
            with mock.patch.object(s_cell.s_logging, 'setup'):
                s_cell.Cell._backupProcHandoff(ctrl_child, caller_child, srcdir, {}, info)

            # control channel carries only the capture handshake
            self.eq([('captured', None)], self._drainProc(ctrl_parent))

            # caller receives t2:yield frames terminated by a retn=None frame
            callermsgs = self._drainProc(caller_parent)
            self.true(all(m[0] == 't2:yield' for m in callermsgs))
            self.none(callermsgs[-1][1]['retn'])

            items = [m[1]['retn'][1] for m in callermsgs if m[1]['retn'] is not None]
            self.eq(('init', info), items[0])
            self.eq('fini', items[-1][0])
            self.isin('data', [i[0] for i in items])

            data = b''.join(i[1] for i in items if i[0] == 'data')
            fini = items[-1][1]
            self.eq(len(data), fini['size'])
            self.eq(hashlib.sha256(data).hexdigest(), fini['sha256'])
            self.gt(fini['rawsize'], 0)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                self.true(any(n.endswith('foo.lmdb/data.mdb') for n in zf.namelist()))

    async def test_backupprochandoff_err(self):
        info = {'nexsoffs': 0, 'iden': 'b' * 32, 'type': 'cell', 'name': None}

        # a failure after capture is surfaced as an in-band ('err', ...) item + terminal
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')
            async with await s_lmdbslab.Slab.anit(s_common.genpath(srcdir, 'foo.lmdb')):
                pass

            def _boom(*args, **kwargs):
                raise RuntimeError('iter boom')

            ctrl_parent, ctrl_child = socket.socketpair()
            caller_parent, caller_child = socket.socketpair()
            with mock.patch.object(s_backup, 'iterslabzip', _boom):
                with mock.patch.object(s_cell.s_logging, 'setup'):
                    s_cell.Cell._backupProcHandoff(ctrl_child, caller_child, srcdir, {}, info)

            self.eq([('captured', None)], self._drainProc(ctrl_parent))
            callermsgs = self._drainProc(caller_parent)
            self.none(callermsgs[-1][1]['retn'])
            items = [m[1]['retn'][1] for m in callermsgs if m[1]['retn'] is not None]
            self.eq(('init', info), items[0])
            self.eq('err', items[-1][0])
            self.eq('RuntimeError', items[-1][1]['err'])

        # a failure before capture writes nothing to the caller and no capture signal
        with self.getTestDir() as dirn:
            srcdir = s_common.gendir(dirn, 'svc')

            def _boom(*args, **kwargs):
                raise RuntimeError('capture boom')

            ctrl_parent, ctrl_child = socket.socketpair()
            caller_parent, caller_child = socket.socketpair()
            with mock.patch.object(s_backup, 'capturelmdbs', _boom):
                with mock.patch.object(s_cell.s_logging, 'setup'):
                    s_cell.Cell._backupProcHandoff(ctrl_child, caller_child, srcdir, {}, info)

            self.eq([], self._drainProc(ctrl_parent))
            self.eq([], self._drainProc(caller_parent))

    async def test_backup_exclude(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                layriden = core.getLayer().iden

            with self.getTestDir() as dirn2:

                argv = (
                    core.dirn,
                    dirn2,
                    '--skipdirs', '**/nodeedits.lmdb', './axon',
                )

                self.eq(0, await s_backup.main(argv))

                skipdirs = {'tmp', 'nodeedits.lmdb', 'axon'}
                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs=skipdirs)

                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'axon')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'layers', layriden, 'nodeedits.lmdb')))

                self.true(os.path.exists(s_common.genpath(dirn2, 'layers', layriden, 'layer_v2.lmdb')))
                self.isin(f'/layers/{layriden}/layer_v2.lmdb/data.mdb', fpset)

            with self.getTestDir() as dirn2:

                argv = (
                    core.dirn,
                    dirn2,
                    '--skipdirs', 'layers/*',
                )

                self.eq(0, await s_backup.main(argv))

                fpset = self.compare_dirs(core.dirn, dirn2, skipfns={'lock.mdb'}, skipdirs={'tmp', layriden})

                self.false(os.path.exists(s_common.genpath(dirn2, 'tmp')))
                self.true(os.path.exists(s_common.genpath(dirn2, 'layers')))
                self.false(os.path.exists(s_common.genpath(dirn2, 'layers', layriden)))

                self.true(os.path.exists(s_common.genpath(dirn2, 'slabs', 'cell.lmdb')))
                self.isin('/slabs/cell.lmdb/data.mdb', fpset)
