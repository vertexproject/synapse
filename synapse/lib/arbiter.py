'''
Fork orchestrator for multi-process Cortex read workers.

The Arbiter forks N read-only worker processes after the Cortex has fully
initialized.  Workers inherit the listening socket and accept connections
directly (prefork model).  The parent retains the arbiter role: it detects
crashed workers via SIGCHLD and respawns them, and performs orderly shutdown
on SIGTERM.
'''
from __future__ import annotations

import os
import asyncio
import signal
import socket
import logging
import time
from typing import Callable, Optional

import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

SHUTDOWN_GRACE = 5.0
SHUTDOWN_POLL = 0.1
MEMLOCK_JOIN_TIMEOUT = 5.0


def _close_fd(fd: int) -> None:
    '''Close a file descriptor, ignoring errors.'''
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass


def _shutdown_forkpool() -> None:
    '''Shut down the forkserver process pool before forking.'''
    import synapse.lib.processpool as s_processpool
    if getattr(s_processpool, 'forkpool', None) is not None:
        s_processpool.forkpool.shutdown(wait=True)
        s_processpool.forkpool = None
        s_processpool.forkpool_sema = None
        logger.info('Shut down forkserver pool before fork')


def _stop_memlock_threads() -> None:
    '''Signal all slab memlock threads to stop and wait for them to exit.'''
    slabs_with_memlock = [
        slab for slab in s_lmdbslab.Slab.allslabs.values()
        if slab.memlocktask is not None
    ]
    if not slabs_with_memlock:
        return

    for slab in slabs_with_memlock:
        slab.isfini = True
        slab.resizeevent.set()

    deadline = time.monotonic() + MEMLOCK_JOIN_TIMEOUT
    for slab in slabs_with_memlock:
        while not slab.memlocktask.done() and time.monotonic() < deadline:
            time.sleep(0.05)

        if not slab.memlocktask.done():
            logger.warning('Memlock thread for %s did not exit in time', slab.path)
        else:
            logger.debug('Memlock thread for %s stopped', slab.path)


def _close_all_slabs() -> None:
    '''Close every open LMDB environment so children don't inherit parent mmaps.'''
    for slab in list(s_lmdbslab.Slab.allslabs.values()):
        try:
            slab.lenv.close()
        except Exception:
            logger.warning('Failed to close slab %s pre-fork', slab.path, exc_info=True)


class Arbiter:
    '''Fork orchestrator and worker lifecycle manager.'''

    def __init__(self) -> None:
        self._listen_sock: Optional[socket.socket] = None
        self._uds_path: Optional[str] = None
        self._worker_pids: list[Optional[int]] = []
        self._num_workers: int = 0
        self._worker_main: Optional[Callable] = None
        self._shutdown_flag: bool = False
        self._pending_restarts: list[int] = []
        self._pending_thick_router_restart: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thick_router_pid: Optional[int] = None
        self._write_channels: dict[int, tuple[int, int]] = {}
        self._dispatch_channels: dict[int, tuple[int, int]] = {}
        self._thick_writer_channel: Optional[tuple[int, int]] = None

    def fork_workers(
        self,
        num_workers: int,
        listen_sock: int,
        uds_path: str,
        worker_main: Callable,
    ) -> list[int]:
        '''
        Fork *num_workers* read-only worker processes.

        Must be called after Cortex init completes and the asyncio event loop
        has been torn down (no running loop, no threads).

        Returns:
            List of PIDs of the forked workers.
        '''
        self._listen_sock = listen_sock
        self._uds_path = uds_path
        self._num_workers = num_workers
        self._worker_main = worker_main

        _shutdown_forkpool()
        _stop_memlock_threads()
        _close_all_slabs()

        # Create per-worker write channel socketpairs
        for i in range(num_workers):
            worker_write, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            self._write_channels[i] = (worker_write.fileno(), writer_end.fileno())
            worker_write.detach()
            writer_end.detach()

        # Create dispatch socketpairs (thick router → worker)
        for i in range(num_workers):
            router_end, worker_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            self._dispatch_channels[i] = (router_end.fileno(), worker_end.fileno())
            router_end.detach()
            worker_end.detach()

        # Thick router → writer dispatch channel
        router_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self._thick_writer_channel = (router_end.fileno(), writer_end.fileno())
        router_end.detach()
        writer_end.detach()

        self._install_parent_signals()

        for i in range(num_workers):
            self._fork_one(i)

        logger.info('Forked %d workers: %s', num_workers, self._worker_pids)
        return list(self._worker_pids)

    def fork_thick_router(self, listen_fd: int) -> int:
        '''
        Fork the thick router process.

        The thick router owns all client connections on listen_fd, classifies
        queries, and dispatches reads to workers / writes to the writer via
        dedicated dispatch socketpairs.

        Returns:
            PID of the thick router process.
        '''
        self._thick_listen_fd = listen_fd

        dispatch_fds = {}
        for wid, (router_fd, _) in self._dispatch_channels.items():
            dispatch_fds[wid] = router_fd

        writer_dispatch_fd = self._thick_writer_channel[0]

        pid = os.fork()
        if pid == 0:
            # --- child (thick router) ---
            try:
                for wid, (_, worker_fd) in self._dispatch_channels.items():
                    _close_fd(worker_fd)

                _close_fd(self._thick_writer_channel[1])

                for wid, (w_worker_fd, w_writer_fd) in self._write_channels.items():
                    _close_fd(w_worker_fd)
                    _close_fd(w_writer_fd)

                _thick_router_main(listen_fd, dispatch_fds, writer_dispatch_fd)
            except Exception:
                logger.exception('Thick router process crashed')
            finally:
                os._exit(0)

        # --- parent (arbiter) ---
        self._thick_router_pid = pid
        logger.info('Forked thick router (pid %d) on fd %d', pid, listen_fd)
        return pid

    def get_writer_fds(self) -> list[int]:
        '''Return a list of writer-end write channel fds.'''
        return [w_writer_fd for _, w_writer_fd in self._write_channels.values()
                if w_writer_fd >= 0]

    def get_thick_writer_fd(self) -> Optional[int]:
        '''Return the writer-end fd of the thick router → writer dispatch channel.'''
        if self._thick_writer_channel is None:
            return None
        return self._thick_writer_channel[1]

    # ------------------------------------------------------------------
    # internal fork helpers
    # ------------------------------------------------------------------

    def _fork_one(self, worker_id: int) -> None:
        pid = os.fork()
        if pid == 0:
            try:
                self._in_child(worker_id)
            except Exception:
                logger.exception('Worker %d crashed during init', os.getpid())
            finally:
                os._exit(1)

        self._worker_pids.append(pid)
        logger.info('Forked worker %d (pid %d)', worker_id, pid)

    def _in_child(self, worker_id: int) -> None:
        '''Run in the child process immediately after fork.'''
        os.setsid()
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Close writer-end fds and other workers' write fds
        for wid, (w_worker_fd, w_writer_fd) in self._write_channels.items():
            _close_fd(w_writer_fd)
            if wid != worker_id:
                _close_fd(w_worker_fd)

        # Close dispatch channel fds not belonging to this worker
        for wid, (router_fd, worker_fd) in self._dispatch_channels.items():
            _close_fd(router_fd)
            if wid != worker_id:
                _close_fd(worker_fd)

        # Close thick writer channel fds (not needed in worker)
        if self._thick_writer_channel is not None:
            _close_fd(self._thick_writer_channel[0])
            _close_fd(self._thick_writer_channel[1])

        write_fd = self._write_channels[worker_id][0]
        dispatch_fd = self._dispatch_channels[worker_id][1] if worker_id in self._dispatch_channels else None
        self._worker_main(None, self._uds_path, worker_id,
                          write_fd=write_fd, dispatch_fd=dispatch_fd)

    # ------------------------------------------------------------------
    # parent signal handlers
    # ------------------------------------------------------------------

    def _install_parent_signals(self) -> None:
        signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def _handle_sigchld(self, signum, frame) -> None:
        '''Reap only arbiter-managed children. Leave SpawnProcess children
        for multiprocessing to handle.'''
        # Check thick router
        if self._thick_router_pid is not None:
            try:
                pid, status = os.waitpid(self._thick_router_pid, os.WNOHANG)
                if pid != 0:
                    if os.WIFSIGNALED(status):
                        sig = os.WTERMSIG(status)
                        logger.error('Thick router pid %d killed by signal %d', pid, sig)
                    else:
                        code = os.WEXITSTATUS(status)
                        logger.error('Thick router pid %d exited with code %d', pid, code)
                    self._thick_router_pid = None
                    if not self._shutdown_flag:
                        self._pending_thick_router_restart = True
            except ChildProcessError:
                pass

        # Check each worker
        for idx, wpid in enumerate(self._worker_pids):
            if wpid is None:
                continue
            try:
                pid, status = os.waitpid(wpid, os.WNOHANG)
                if pid != 0:
                    self._worker_pids[idx] = None
                    if os.WIFSIGNALED(status):
                        sig = os.WTERMSIG(status)
                        logger.error('Worker pid %d killed by signal %d', pid, sig)
                    else:
                        code = os.WEXITSTATUS(status)
                        logger.error('Worker pid %d exited with code %d', pid, code)
                    if not self._shutdown_flag:
                        self._pending_restarts.append(idx)
            except ChildProcessError:
                pass

    def install_loop_signal_handler(self, loop: asyncio.AbstractEventLoop) -> None:
        '''Install an async-safe SIGCHLD handler on the event loop.'''
        self._loop = loop

        def _on_sigchld():
            self._handle_sigchld(signal.SIGCHLD, None)
            self.process_pending_restarts()

        loop.add_signal_handler(signal.SIGCHLD, _on_sigchld)

    def process_pending_restarts(self) -> None:
        '''Fork new workers for any slots that died.'''
        if self._pending_thick_router_restart:
            self._pending_thick_router_restart = False
            logger.info('Respawning thick router...')
            self.fork_thick_router(self._thick_listen_fd)
        while self._pending_restarts:
            idx = self._pending_restarts.pop(0)
            self.restart_worker(idx)

    # ------------------------------------------------------------------
    # restart / shutdown
    # ------------------------------------------------------------------

    def restart_worker(self, idx: int) -> None:
        '''Respawn the worker at slot *idx* with a fresh socketpair.'''
        # Create a fresh write channel socketpair
        worker_write, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self._write_channels[idx] = (worker_write.fileno(), writer_end.fileno())
        worker_write.detach()
        writer_end.detach()

        # Create a fresh dispatch channel socketpair
        router_end, worker_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self._dispatch_channels[idx] = (router_end.fileno(), worker_end.fileno())
        router_end.detach()
        worker_end.detach()

        pid = os.fork()
        if pid == 0:
            try:
                self._in_child(idx)
            except Exception:
                logger.exception('Worker %d crashed during init', os.getpid())
            finally:
                os._exit(1)

        self._worker_pids[idx] = pid
        logger.info('Respawned worker slot %d as pid %d', idx, pid)

        self._restart_router()

    def get_write_channel_fds(self) -> dict[int, int]:
        '''Return {worker_id: writer_end_fd} for the writer process.'''
        return {wid: wfd for wid, (_, wfd) in self._write_channels.items() if wfd >= 0}

    def _restart_router(self) -> None:
        '''Kill the old thick router and fork a new one with current dispatch channels.'''
        if self._thick_router_pid is not None:
            try:
                os.kill(self._thick_router_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self._thick_router_pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self._thick_router_pid = None
            self.fork_thick_router(self._thick_listen_fd)

    def shutdown(self) -> None:
        '''Send SIGTERM to thick router first, then workers, wait with timeout, SIGKILL stragglers.'''
        self._shutdown_flag = True

        # Stop thick router first
        if self._thick_router_pid is not None:
            try:
                os.kill(self._thick_router_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self._thick_router_pid, 0)
            except ChildProcessError:
                pass
            self._thick_router_pid = None

        alive = [p for p in self._worker_pids if p is not None]
        if not alive:
            return

        for pid in alive:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        deadline = time.monotonic() + SHUTDOWN_GRACE
        while time.monotonic() < deadline:
            alive = [p for p in self._worker_pids if p is not None]
            if not alive:
                return
            for pid in alive:
                try:
                    rpid, _ = os.waitpid(pid, os.WNOHANG)
                    if rpid != 0:
                        idx = self._worker_pids.index(pid)
                        self._worker_pids[idx] = None
                except ChildProcessError:
                    idx = self._worker_pids.index(pid)
                    self._worker_pids[idx] = None
            time.sleep(SHUTDOWN_POLL)

        for i, pid in enumerate(self._worker_pids):
            if pid is None:
                continue
            logger.warning('Worker pid %d did not exit in time, sending SIGKILL', pid)
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            self._worker_pids[i] = None


def _thick_router_main(listen_fd, worker_dispatch_fds, writer_dispatch_fd):
    '''Entry point for the thick router child process.'''
    import synapse.lib.thickrouter as s_thickrouter

    async def _run():
        import threading
        import synapse.glob as s_glob
        s_glob._glob_loop = asyncio.get_running_loop()
        s_glob._glob_thrd = threading.current_thread()

        print(f'[thick-router pid={os.getpid()}] Starting...', flush=True)
        router = s_thickrouter.ThickRouter(
            cell=None,
            worker_fds=worker_dispatch_fds,
            writer_fd=writer_dispatch_fd,
        )
        await router.start()
        print(f'[thick-router pid={os.getpid()}] Daemon started', flush=True)

        import socket as _socket
        sock = _socket.socket(fileno=listen_fd)
        sock.setblocking(False)
        await router.listen(f'tcp://0.0.0.0', ssl=None, sock=sock)
        print(f'[thick-router pid={os.getpid()}] Listening', flush=True)

        stop_event = asyncio.Event()

        def _on_term():
            stop_event.set()

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, _on_term)
        loop.add_signal_handler(signal.SIGINT, _on_term)

        await stop_event.wait()
        await router.stop()

    asyncio.run(_run())


def _reopen_writer_slabs():
    '''Re-open LMDB environments in the writer process after fork.'''
    import lmdb as _lmdb
    for slab in list(s_lmdbslab.Slab.allslabs.values()):
        path = slab.path
        opts = {
            'map_size': slab.mapsize,
            'max_dbs': 128,
            'max_readers': 256,
            'writemap': True,
            'readonly': slab.readonly,
            'readahead': slab.readahead,
            'map_async': True,
        }
        try:
            slab.lenv = _lmdb.open(str(path), **opts)
            slab.isfini = False
            slab.lockdoneevent = asyncio.Event()
            slab.lockdoneevent.set()

            if not slab.readonly:
                slab._initCoXact()

            old_dbnames = dict(slab.dbnames)
            slab.dbnames = {None: (None, False)}
            for name, (db, dupsort) in old_dbnames.items():
                if name is None:
                    continue
                try:
                    if slab.readonly:
                        newdb = slab.lenv.open_db(name.encode('utf8'), create=False, dupsort=dupsort)
                    else:
                        newdb = slab.lenv.open_db(name.encode('utf8'), txn=slab.xact, dupsort=dupsort)
                    slab.dbnames[name] = (newdb, dupsort)
                except Exception:
                    logger.warning('Failed to re-open db %s in slab %s', name, path)

            if not slab.readonly:
                slab.dirty = True
                slab.forcecommit()

            logger.debug('Re-opened slab %s for writer (%d dbs)', path, len(slab.dbnames) - 1)
        except Exception:
            logger.exception('Failed to re-open slab %s for writer', path)
