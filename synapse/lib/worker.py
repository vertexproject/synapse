'''
ReadOnlyWorker — forked read worker for the prefork Cortex architecture.

After the parent Cortex initializes fully, it forks N workers that inherit
the listening socket. Each worker re-opens LMDB in readonly mode, accepts
client connections with EPOLLEXCLUSIVE, serves reads locally, and forwards
writes to the writer process via msgpack RPC over a pre-connected socketpair.
'''
import os
import re
import time
import select
import socket
import asyncio
import logging

import lmdb
import msgpack

import synapse.exc as s_exc
import synapse.daemon as s_daemon
import synapse.lib.link as s_link
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query classification
# ---------------------------------------------------------------------------

_write_commands = frozenset((
    'auth.user.add', 'auth.user.del', 'auth.role.add', 'auth.role.del',
    'auth.user.grant', 'auth.user.revoke', 'auth.user.addrule', 'auth.user.delrule',
    'auth.role.addrule', 'auth.role.delrule',
    'cron.add', 'cron.del', 'cron.mod', 'cron.move', 'cron.enable', 'cron.disable',
    'cron.cleanup',
    'delnode',
    'dmon.add', 'dmon.del',
    'feed.ingest',
    'graph.add', 'graph.del',
    'layer.add', 'layer.del', 'layer.set', 'layer.pull.add', 'layer.push.add',
    'macro.set', 'macro.del',
    'merge',
    'model.edge.set', 'model.edge.del',
    'model.depr.lock', 'model.depr.unlock',
    'movetag',
    'pkg.load', 'pkg.del',
    'queue.add', 'queue.del',
    'service.add', 'service.del',
    'trigger.add', 'trigger.del', 'trigger.mod', 'trigger.enable', 'trigger.disable',
    'view.add', 'view.del', 'view.set', 'view.merge',
))

_re_edit_bracket = re.compile(r'(?<![a-zA-Z0-9_\)\]])\[')
_re_write_cmd = re.compile(
    r'\|\s*(' + '|'.join(re.escape(c) for c in sorted(_write_commands, key=len, reverse=True)) + r')\b'
)
_re_write_patterns = re.compile(
    r'\$node\.data\.set\b'
    r'|\$node\.data\.pop\b'
    r'|\$lib\.queue\.\w+\.put\b'
    r'|->>\s*\w+'
)

_re_comment = re.compile(r'//[^\n]*')


def classify(text):
    '''Classify a Storm query as 'read' or 'write'.'''
    stripped = _re_comment.sub('', text)
    if _re_edit_bracket.search(stripped):
        return 'write'
    if _re_write_cmd.search(stripped):
        return 'write'
    if _re_write_patterns.search(stripped):
        return 'write'
    return 'read'


# ---------------------------------------------------------------------------
# Worker entry point (called after fork)
# ---------------------------------------------------------------------------

def worker_main(control_fd, uds_path, datadir, cell=None, write_fd=None, dispatch_fd=None):
    '''
    Entry point for a forked read worker process.

    Args:
        control_fd: File descriptor of the UDS control channel from the router.
        uds_path: Path to the writer's UDS endpoint (legacy, unused with write_fd).
        datadir: Cortex data directory (for LMDB slab re-open).
        cell: The inherited Cortex cell object (shared via dmon for telepath).
        write_fd: File descriptor of the write channel socketpair to the writer.
        dispatch_fd: File descriptor of the dispatch channel from the thick router.
    '''
    # Neutralize the inherited forkpool (stale threads/pipes after fork)
    import synapse.lib.processpool as s_processpool
    if getattr(s_processpool, 'forkpool', None) is not None:
        s_processpool.forkpool.shutdown(wait=False)
        s_processpool.forkpool = None

    _reopen_lmdb_readonly(datadir)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Rebind all inherited Base objects to the worker's new event loop.
    if cell is not None:
        import gc
        import synapse.lib.base as s_base
        for obj in gc.get_objects():
            if isinstance(obj, s_base.Base) and obj.anitted:
                obj.loop = loop
                obj.finievt = asyncio.Event()
        cell.loop = loop

    if dispatch_fd is not None:
        # Thick router mode — run as pure worker (socketpair task receiver)
        # pure_worker_main handles its own LMDB reopen and event loop
        # so we skip the ReadOnlyWorker path entirely. But worker_main
        # already reopened LMDB and created a loop above, so just use
        # PureWorker directly on the existing loop.
        worker = PureWorker(dispatch_fd, cell)
        try:
            loop.run_until_complete(worker.serve())
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        return

    worker = ReadOnlyWorker(control_fd, uds_path, cell=cell, write_fd=write_fd)
    try:
        loop.run_until_complete(worker.serve())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def _reopen_lmdb_readonly(datadir):
    '''Re-open inherited LMDB slabs in readonly mode.'''
    for slab in list(s_lmdbslab.Slab.allslabs.values()):
        path = slab.path
        try:
            slab.lenv = lmdb.open(
                str(path),
                map_size=0,
                max_dbs=128,
                max_readers=256,
                readonly=True,
                create=False,
                readahead=False,
            )
            slab.isfini = False
            slab.readonly = True
            slab.xact = None
            slab.txnrefcount = 0

            old_dbnames = dict(slab.dbnames)
            slab.dbnames = {None: (None, False)}
            for name, (db, dupsort) in old_dbnames.items():
                if name is None:
                    continue
                try:
                    newdb = slab.lenv.open_db(name.encode('utf8'), create=False, dupsort=dupsort)
                    slab.dbnames[name] = (newdb, dupsort)
                except Exception:
                    logger.warning('Worker: failed to re-open db %s in slab %s', name, path)

            logger.debug('Worker: re-opened slab %s readonly (%d dbs)', path, len(slab.dbnames) - 1)
        except Exception:
            logger.exception('Worker: failed to re-open slab %s', path)


# ---------------------------------------------------------------------------
# ReadOnlyWorker
# ---------------------------------------------------------------------------

_RECV_BUF = 65536
_REQ_COUNTER = 0


class ReadOnlyWorker:
    '''
    Forked read worker. Receives connection fds from the router via a UDS
    control channel, serves Storm reads locally, and forwards writes to
    the writer via msgpack RPC over a pre-connected socketpair.
    '''

    def __init__(self, control_fd, uds_path, cell=None, write_fd=None):
        self._control_fd = control_fd
        self._uds_path = uds_path
        self._cell = cell
        self._write_fd = write_fd
        self._write_alive = write_fd is not None
        self._dmon = None
        self._stopping = False
        self._pid = os.getpid()
        # Demux state: single reader task dispatches to per-request queues
        self._write_lock = None       # asyncio.Lock for serializing sends
        self._write_ready = None      # asyncio.Event set when writer is ready
        self._pending_reqs = {}       # {req_id: asyncio.Queue}
        self._reader_task = None

    async def serve(self):
        '''Main worker loop. Receives fds from router via recvmsg on control channel.'''
        loop = asyncio.get_running_loop()

        if self._cell is not None:
            self._install_write_forwarding()

        if self._cell is not None:
            self._dmon = await s_daemon.Daemon.anit()
            parent_dmon = getattr(self._cell, 'dmon', None)
            if parent_dmon is not None:
                for name, item in parent_dmon.shared.items():
                    self._dmon.share(name, self._cell)
            else:
                self._dmon.share('*', self._cell)

        control_sock = socket.socket(fileno=self._control_fd)
        control_sock.setblocking(False)

        try:
            control_sock.send(b'\x52')
        except OSError:
            logger.error('Worker %d: failed to send READY', self._pid)

        logger.info('Worker %d: receiving connections via control channel', self._pid)

        try:
            while not self._stopping:
                readable = await loop.run_in_executor(None, self._poll_control, control_sock)
                if not readable:
                    continue

                fd = await loop.run_in_executor(None, self._recv_fd, control_sock)
                if fd is None:
                    if self._stopping:
                        break
                    logger.warning('Worker %d: control channel closed', self._pid)
                    break

                conn = socket.socket(fileno=fd)
                conn.setblocking(False)
                loop.create_task(self._handle_connection(conn, conn.getpeername()))
        finally:
            control_sock.detach()
            if self._dmon is not None:
                await self._dmon.fini()
            if self._write_fd is not None:
                try:
                    os.close(self._write_fd)
                except OSError:
                    pass
            logger.info('Worker %d: stopped', self._pid)

    def _poll_control(self, control_sock):
        '''Poll the control socket for readability (blocking, run in executor).'''
        try:
            r, _, _ = select.select([control_sock], [], [], 1.0)
            return bool(r)
        except (OSError, ValueError):
            return False

    def _recv_fd(self, control_sock):
        '''Receive a file descriptor from the control channel.'''
        from synapse.lib.router import recv_fd
        return recv_fd(control_sock)

    async def _handle_connection(self, conn, addr):
        '''Handle a single client connection via the telepath dmon protocol.'''
        if self._dmon is None:
            conn.close()
            return

        reader, writer = await asyncio.open_connection(sock=conn)
        link = await s_link.Link.anit(reader, writer)
        link.schedCoro(self._dmon._onLinkInit(link))

    # ------------------------------------------------------------------
    # Write forwarding via socketpair RPC
    # ------------------------------------------------------------------

    def _install_write_forwarding(self):
        '''Monkey-patch cell.storm() and cell.callStorm() to forward writes.

        Strategy: execute all queries with readonly=True. If IsReadOnly
        surfaces, forward to the writer via the write channel socketpair.
        Regex classify() provides a fast-path for obvious writes.
        '''
        cell = self._cell
        _orig_storm = cell.storm
        _orig_callStorm = cell.callStorm
        worker = self

        # Start the demux reader and init the send lock
        self._write_lock = asyncio.Lock()
        self._write_ready = asyncio.Event()
        if self._write_fd is not None:
            self._reader_task = asyncio.get_running_loop().create_task(self._demux_reader())

        def _refresh_all_ro_slabs():
            for slab in s_lmdbslab.Slab.allslabs.values():
                if slab.readonly:
                    slab._refresh_ro_xact()

        async def _patched_storm(text, opts=None):
            _refresh_all_ro_slabs()
            if classify(text) == 'write':
                async for mesg in worker._forward_write_stream(text, opts):
                    yield mesg
                return

            ropts = dict(opts) if opts else {}
            ropts['readonly'] = True

            async for mesg in _orig_storm(text, opts=ropts):
                if mesg[0] == 'err' and mesg[1][0] == 'IsReadOnly':
                    async for fmesg in worker._forward_write_stream(text, opts):
                        yield fmesg
                    return
                yield mesg

        async def _patched_callStorm(text, opts=None):
            _refresh_all_ro_slabs()
            if classify(text) == 'write':
                return await worker._forward_callStorm(text, opts)

            ropts = dict(opts) if opts else {}
            ropts['readonly'] = True

            try:
                return await _orig_callStorm(text, opts=ropts)
            except s_exc.IsReadOnly:
                return await worker._forward_callStorm(text, opts)

        cell.storm = _patched_storm
        cell.callStorm = _patched_callStorm

    async def _demux_reader(self):
        '''Background task: read from write_fd and dispatch to per-request queues.'''
        loop = asyncio.get_running_loop()

        # Wait for the writer's ready byte before processing responses.
        # The WriteChannelListener sends 0x01 on each writer-end fd once
        # its epoll loop is registered and ready to receive requests.
        try:
            ready_byte = await asyncio.wait_for(
                loop.run_in_executor(None, os.read, self._write_fd, 1),
                timeout=60.0)
            if not ready_byte:
                logger.error('Worker %d: write channel closed before ready', self._pid)
                self._write_alive = False
                return
            logger.info('Worker %d: write channel ready', self._pid)
        except (OSError, asyncio.TimeoutError) as e:
            logger.error('Worker %d: write channel ready wait failed: %s', self._pid, e)
            self._write_alive = False
            return

        # Signal that writes can now be forwarded
        self._write_ready.set()

        unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
        while self._write_alive:
            try:
                data = await loop.run_in_executor(None, os.read, self._write_fd, _RECV_BUF)
            except OSError:
                break
            if not data:
                break
            unpacker.feed(data)
            for resp in unpacker:
                req_id = resp[1]
                q = self._pending_reqs.get(req_id)
                if q is not None:
                    q.put_nowait(resp)
        # Channel dead — signal all waiters
        self._write_alive = False
        for q in self._pending_reqs.values():
            q.put_nowait(None)

    async def _send_write_rpc(self, req):
        '''Send a write RPC request, serialized via lock.'''
        # Wait for the writer to signal readiness (ready byte received)
        if self._write_ready is not None and not self._write_ready.is_set():
            try:
                await asyncio.wait_for(self._write_ready.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                raise s_exc.SynErr(mesg='Writer unavailable (write channel not ready)')

        if not self._write_alive:
            raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')

        data = s_msgpack.en(req)
        loop = asyncio.get_running_loop()
        async with self._write_lock:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, self._sendall, data),
                    timeout=30.0)
            except (OSError, BrokenPipeError, asyncio.TimeoutError):
                self._write_alive = False
                raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')

    def _sendall(self, data):
        '''Write all bytes to the write channel fd, handling partial writes.'''
        mv = memoryview(data)
        while mv:
            sent = os.write(self._write_fd, mv)
            mv = mv[sent:]

    async def _forward_write_stream(self, text, opts):
        '''Forward a storm query to the writer via socketpair, yielding messages.'''
        global _REQ_COUNTER
        _REQ_COUNTER += 1
        req_id = _REQ_COUNTER

        q = asyncio.Queue()
        self._pending_reqs[req_id] = q
        try:
            await self._send_write_rpc(('storm', req_id, text, opts))
            while True:
                resp = await asyncio.wait_for(q.get(), timeout=30.0)
                if resp is None:
                    raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')
                if resp[0] == 'msg':
                    yield resp[2]
                elif resp[0] == 'done':
                    return
                elif resp[0] == 'err':
                    raise s_exc.SynErr(mesg=resp[2].get('mesg', 'Write forwarding error'))
        except asyncio.TimeoutError:
            raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')
        finally:
            self._pending_reqs.pop(req_id, None)

    async def _forward_callStorm(self, text, opts):
        '''Forward a callStorm to the writer, returning the result value.'''
        global _REQ_COUNTER
        _REQ_COUNTER += 1
        req_id = _REQ_COUNTER

        q = asyncio.Queue()
        self._pending_reqs[req_id] = q
        try:
            await self._send_write_rpc(('callStorm', req_id, text, opts))
            while True:
                resp = await asyncio.wait_for(q.get(), timeout=30.0)
                if resp is None:
                    raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')
                if resp[0] == 'result':
                    return resp[2]
                elif resp[0] == 'err':
                    raise s_exc.SynErr(mesg=resp[2].get('mesg', 'Write forwarding error'))
        except asyncio.TimeoutError:
            raise s_exc.SynErr(mesg='Writer unavailable (write channel dead)')
        finally:
            self._pending_reqs.pop(req_id, None)

    def shutdown(self):
        '''Signal the worker to stop accepting new connections.'''
        self._stopping = True
        logger.info('Worker %d: shutdown requested', self._pid)


# ---------------------------------------------------------------------------
# Pure Worker — socketpair task receiver for thick router
# ---------------------------------------------------------------------------

_CANCEL_CHECK_INTERVAL = 64  # Check cancellation every N yielded messages


def pure_worker_main(task_fd, datadir, cell):
    '''
    Entry point for a pure read worker (thick router mode).

    Receives query tasks via socketpair, executes storm(), streams results
    back. No Daemon, no connection handling, no write forwarding.

    Args:
        task_fd: File descriptor of the socketpair to the router.
        datadir: Cortex data directory (for LMDB slab re-open).
        cell: The inherited Cortex cell object.
    '''
    import synapse.lib.processpool as s_processpool
    if getattr(s_processpool, 'forkpool', None) is not None:
        s_processpool.forkpool.shutdown(wait=False)
        s_processpool.forkpool = None

    _reopen_lmdb_readonly(datadir)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if cell is not None:
        import gc
        import synapse.lib.base as s_base
        for obj in gc.get_objects():
            if isinstance(obj, s_base.Base) and obj.anitted:
                obj.loop = loop
                obj.finievt = asyncio.Event()
        cell.loop = loop

    worker = PureWorker(task_fd, cell)
    try:
        loop.run_until_complete(worker.serve())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


class PureWorker:
    '''
    Pure read worker for the thick router. Receives query tasks via
    socketpair, executes cell.storm() directly, streams results back.
    No Daemon, no connection handling, no write forwarding.
    '''

    def __init__(self, task_fd, cell):
        self._task_fd = task_fd
        self._cell = cell
        self._pid = os.getpid()
        self._cancelled = set()  # Set of cancelled req_ids

    async def serve(self):
        '''Main loop: read tasks from socketpair, execute, stream results.'''
        loop = asyncio.get_running_loop()
        unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)

        # Signal ready to router
        try:
            os.write(self._task_fd, b'\x52')
        except OSError:
            logger.error('PureWorker %d: failed to send READY', self._pid)
            return

        logger.info('PureWorker %d: ready', self._pid)

        while True:
            try:
                data = await loop.run_in_executor(None, os.read, self._task_fd, _RECV_BUF)
            except OSError:
                break
            if not data:
                break

            unpacker.feed(data)
            for msg in unpacker:
                kind = msg[0]
                if kind == 'storm':
                    _, req_id, text, opts = msg
                    loop.create_task(self._exec_storm(req_id, text, opts))
                elif kind == 'cancel':
                    _, req_id = msg
                    self._cancelled.add(req_id)

        logger.info('PureWorker %d: stopped', self._pid)

    async def _exec_storm(self, req_id, text, opts):
        '''Execute a storm query and stream results back to the router.'''
        self._refresh_slabs()

        ropts = dict(opts) if opts else {}
        ropts['readonly'] = True

        try:
            count = 0
            async for mesg in self._cell.storm(text, opts=ropts):
                if req_id in self._cancelled:
                    break
                self._send(('msg', req_id, mesg))
                count += 1
                if count % _CANCEL_CHECK_INTERVAL == 0:
                    await asyncio.sleep(0)  # Yield to process cancellations

            if req_id in self._cancelled:
                self._cancelled.discard(req_id)
                self._send(('done', req_id))
            else:
                self._send(('done', req_id))

        except s_exc.IsReadOnly:
            self._send(('err', req_id, {'err': 'IsReadOnly'}))
        except Exception as e:
            logger.exception('PureWorker %d: storm error req=%s', self._pid, req_id)
            self._send(('err', req_id, {'err': type(e).__name__, 'mesg': str(e)}))
        finally:
            self._cancelled.discard(req_id)

    def _refresh_slabs(self):
        '''Refresh all readonly LMDB transactions before each query.'''
        for slab in s_lmdbslab.Slab.allslabs.values():
            if slab.readonly:
                slab._refresh_ro_xact()

    def _send(self, msg):
        '''Send a msgpack-encoded message to the router via socketpair.'''
        data = s_msgpack.en(msg)
        mv = memoryview(data)
        while mv:
            try:
                sent = os.write(self._task_fd, mv)
                mv = mv[sent:]
            except OSError:
                return
