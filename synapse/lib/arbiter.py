'''
Fork orchestrator for multi-process Cortex read workers.

The Arbiter forks N read-only worker processes after the Cortex has fully
initialized.  Workers inherit the listening socket and accept connections
directly (prefork model).  The parent retains the arbiter role: it detects
crashed workers via SIGCHLD and respawns them, and performs orderly shutdown
on SIGTERM.
'''
import os
import asyncio
import signal
import socket
import logging
import time

import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

# Seconds to wait for workers to exit after SIGTERM before sending SIGKILL.
SHUTDOWN_GRACE = 5.0

# Seconds between waitpid polls during shutdown drain.
SHUTDOWN_POLL = 0.1

# Seconds to wait for memlock threads to exit before fork.
MEMLOCK_JOIN_TIMEOUT = 5.0


def _shutdown_forkpool():
    '''Shut down the forkserver process pool before forking.

    The forkserver pool (ProcessPoolExecutor) spawns worker processes
    (SpawnProcess-1/2/3) that live in the parent's process group.  If we
    fork without shutting it down first, the forkserver workers receive
    SIGTERM from process group cleanup and die during startup.
    '''
    import synapse.lib.processpool as s_processpool
    if getattr(s_processpool, 'forkpool', None) is not None:
        s_processpool.forkpool.shutdown(wait=True)
        s_processpool.forkpool = None
        s_processpool.forkpool_sema = None
        logger.info('Shut down forkserver pool before fork')


def _stop_memlock_threads():
    '''Signal all slab memlock threads to stop and wait for them to exit.

    Must be called before _close_all_slabs() and before fork() so that no
    background threads are alive when we fork.
    '''
    slabs_with_memlock = [
        slab for slab in s_lmdbslab.Slab.allslabs.values()
        if slab.memlocktask is not None
    ]
    if not slabs_with_memlock:
        return

    # Signal all memlock threads to exit
    for slab in slabs_with_memlock:
        slab.isfini = True
        slab.resizeevent.set()

    # Wait for threads to finish (they check isfini and will exit)
    deadline = time.monotonic() + MEMLOCK_JOIN_TIMEOUT
    for slab in slabs_with_memlock:
        remaining = max(0, deadline - time.monotonic())
        # The memlocktask is a Future wrapping a thread executor call.
        # We can't await it (no event loop), but the underlying thread
        # will exit because we set isfini=True and signaled resizeevent.
        # Wait by polling the thread pool — the thread checks isfini on
        # each iteration of its loop.
        while not slab.memlocktask.done() and time.monotonic() < deadline:
            time.sleep(0.05)

        if not slab.memlocktask.done():
            logger.warning('Memlock thread for %s did not exit in time', slab.path)
        else:
            logger.debug('Memlock thread for %s stopped', slab.path)


def _close_all_slabs():
    '''Close every open LMDB environment so children don't inherit parent mmaps.

    Closes the lenv handles but preserves slab entries in allslabs so that
    forked workers can discover slab paths for readonly re-open.
    '''
    for slab in list(s_lmdbslab.Slab.allslabs.values()):
        try:
            slab.lenv.close()
        except Exception:
            logger.warning('Failed to close slab %s pre-fork', slab.path, exc_info=True)
    # NOTE: Do NOT clear allslabs here. Workers need the slab metadata
    # (paths) to re-open in readonly mode. See L-1 fix.


class Arbiter:
    '''Fork orchestrator and worker lifecycle manager.'''

    def __init__(self, router_mode='thin'):
        self._listen_sock = None
        self._uds_path = None
        self._worker_pids = []  # ordered list of child pids
        self._num_workers = 0
        self._worker_main = None
        self._shutdown_flag = False
        self._pending_restarts = []  # (slot_idx,) tuples queued by SIGCHLD handler
        self._loop = None  # set by install_loop_signal_handler
        self._router_pid = None
        self._thick_router_pid = None
        self._router_mode = router_mode  # 'thin' or 'thick'
        self._control_channels = {}  # {worker_id: (router_fd, worker_fd)}
        self._write_channels = {}    # {worker_id: (worker_fd, writer_fd)}
        # Thick router dispatch channels: thick router → worker
        self._dispatch_channels = {}  # {worker_id: (router_fd, worker_fd)}
        # Thick router → writer dispatch channel
        self._thick_writer_channel = None  # (router_fd, writer_fd)

    def fork_workers(self, num_workers, listen_sock, uds_path, worker_main):
        '''
        Fork *num_workers* read-only worker processes.

        Must be called after Cortex init completes and the asyncio event loop
        has been torn down (no running loop, no threads).

        Args:
            num_workers: Number of worker processes to fork.
            listen_sock: The bound/listening socket fd workers inherit.
            uds_path: Filesystem path of the writer's UDS endpoint.
            worker_main: Callable ``worker_main(control_fd, uds_path, worker_id)``
                         invoked in each child.  Must not return (call ``os._exit``).

        Returns:
            list[int]: PIDs of the forked workers.
        '''
        self._listen_sock = listen_sock
        self._uds_path = uds_path
        self._num_workers = num_workers
        self._worker_main = worker_main

        _shutdown_forkpool()
        _stop_memlock_threads()
        _close_all_slabs()

        # Create per-worker UDS socketpairs for fd passing
        for i in range(num_workers):
            router_end, worker_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            self._control_channels[i] = (router_end.fileno(), worker_end.fileno())
            router_end.detach()
            worker_end.detach()

            # Write channel (worker → writer): for write forwarding
            worker_write, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
            self._write_channels[i] = (worker_write.fileno(), writer_end.fileno())
            worker_write.detach()
            writer_end.detach()

        # Thick mode: create dispatch socketpairs (thick router → worker)
        if self._router_mode == 'thick':
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

    def fork_router(self, listen_fd):
        '''Fork the router process. Must be called after fork_workers().

        Args:
            listen_fd: The listening socket fd the router will accept on.

        Returns:
            int: PID of the router process.
        '''
        import synapse.lib.router as s_router

        self._listen_fd = listen_fd

        # Build {worker_id: router_end_fd} map
        worker_uds_fds = {}
        for wid, (router_fd, worker_fd) in self._control_channels.items():
            worker_uds_fds[wid] = router_fd

        pid = os.fork()
        if pid == 0:
            # --- child (router) ---
            try:
                # Close worker-end fds in router process
                for wid, (_, worker_fd) in self._control_channels.items():
                    if worker_fd >= 0:
                        try:
                            os.close(worker_fd)
                        except OSError:
                            pass

                # Close all write channel fds in router (not needed)
                for wid, (w_worker_fd, w_writer_fd) in self._write_channels.items():
                    for fd in (w_worker_fd, w_writer_fd):
                        if fd >= 0:
                            try:
                                os.close(fd)
                            except OSError:
                                pass

                # Close dispatch channel fds in thin router (not needed)
                for wid, (r_fd, w_fd) in self._dispatch_channels.items():
                    for fd in (r_fd, w_fd):
                        if fd >= 0:
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                if self._thick_writer_channel is not None:
                    for fd in self._thick_writer_channel:
                        if fd >= 0:
                            try:
                                os.close(fd)
                            except OSError:
                                pass

                router = s_router.RouterProcess(listen_fd, worker_uds_fds)
                router.router_main()
            except Exception:
                logger.exception('Router process crashed')
            finally:
                os._exit(0)

        # --- parent (arbiter) ---
        self._router_pid = pid
        logger.info('Forked router (pid %d)', pid)

        # F-2 fix: Close the worker-end fds in the parent. The router
        # detects dead workers via EPOLLHUP on the router-end fd, which
        # only fires when ALL worker-end fds are closed. Without this,
        # the parent's copy keeps the socketpair alive and HUP never fires.
        # We keep the router-end fds so _restart_router can re-fork.
        for wid, (router_fd, worker_fd) in list(self._control_channels.items()):
            if worker_fd >= 0:
                try:
                    os.close(worker_fd)
                except OSError:
                    pass
                self._control_channels[wid] = (router_fd, -1)

        # Close worker-end write fds in the parent (writer process).
        # The writer keeps the writer-end fds for receiving write RPCs.
        for wid, (w_worker_fd, w_writer_fd) in list(self._write_channels.items()):
            if w_worker_fd >= 0:
                try:
                    os.close(w_worker_fd)
                except OSError:
                    pass
                self._write_channels[wid] = (-1, w_writer_fd)

        return pid

    def get_writer_fds(self):
        '''Return a list of writer-end write channel fds.

        These fds are used by the writer process to receive write RPCs
        from workers via the write channel socketpairs.
        '''
        return [w_writer_fd for _, w_writer_fd in self._write_channels.values()
                if w_writer_fd >= 0]

    def fork_thick_router(self, listen_fd):
        '''Fork the thick router process. Must be called after fork_workers().

        The thick router owns all client connections on listen_fd, classifies
        queries, and dispatches reads to workers / writes to the writer via
        dedicated dispatch socketpairs.

        Args:
            listen_fd: The listening socket fd for the thick router (port 27493).

        Returns:
            int: PID of the thick router process.
        '''
        self._thick_listen_fd = listen_fd

        # Build {worker_id: router_end_fd} for dispatch channels
        dispatch_fds = {}
        for wid, (router_fd, _) in self._dispatch_channels.items():
            dispatch_fds[wid] = router_fd

        # Writer dispatch fd (router end)
        writer_dispatch_fd = self._thick_writer_channel[0]

        pid = os.fork()
        if pid == 0:
            # --- child (thick router) ---
            try:
                # Close worker-end dispatch fds (not needed in router)
                for wid, (_, worker_fd) in self._dispatch_channels.items():
                    if worker_fd >= 0:
                        try:
                            os.close(worker_fd)
                        except OSError:
                            pass

                # Close writer-end of thick writer channel
                if self._thick_writer_channel[1] >= 0:
                    try:
                        os.close(self._thick_writer_channel[1])
                    except OSError:
                        pass

                # Close thin router control channels (not needed)
                for wid, (r_fd, w_fd) in self._control_channels.items():
                    for fd in (r_fd, w_fd):
                        if fd >= 0:
                            try:
                                os.close(fd)
                            except OSError:
                                pass

                # Close write channels (not needed in thick router)
                for wid, (w_worker_fd, w_writer_fd) in self._write_channels.items():
                    for fd in (w_worker_fd, w_writer_fd):
                        if fd >= 0:
                            try:
                                os.close(fd)
                            except OSError:
                                pass

                _thick_router_main(listen_fd, dispatch_fds, writer_dispatch_fd)
            except Exception:
                logger.exception('Thick router process crashed')
            finally:
                os._exit(0)

        # --- parent (arbiter) ---
        self._thick_router_pid = pid
        logger.info('Forked thick router (pid %d) on fd %d', pid, listen_fd)

        # Close router-end dispatch fds in parent (only thick router uses them)
        for wid, (router_fd, worker_fd) in list(self._dispatch_channels.items()):
            if router_fd >= 0:
                try:
                    os.close(router_fd)
                except OSError:
                    pass
                self._dispatch_channels[wid] = (-1, worker_fd)

        # Close router-end of thick writer channel in parent
        if self._thick_writer_channel[0] >= 0:
            try:
                os.close(self._thick_writer_channel[0])
            except OSError:
                pass
            self._thick_writer_channel = (-1, self._thick_writer_channel[1])

        return pid

    def get_thick_writer_fd(self):
        '''Return the writer-end fd of the thick router → writer dispatch channel.

        Used by the writer process to receive dispatched queries from the
        thick router.
        '''
        if self._thick_writer_channel is None:
            return None
        return self._thick_writer_channel[1]

    # ------------------------------------------------------------------
    # internal fork helpers
    # ------------------------------------------------------------------

    def _fork_one(self, worker_id):
        pid = os.fork()
        if pid == 0:
            # --- child ---
            try:
                self._in_child(worker_id)
            except Exception:
                logger.exception('Worker %d crashed during init', os.getpid())
            finally:
                os._exit(1)

        # --- parent ---
        self._worker_pids.append(pid)
        logger.info('Forked worker %d (pid %d)', worker_id, pid)

    def _in_child(self, worker_id):
        '''Run in the child process immediately after fork.'''
        # Create a new session so SSM process group cleanup cannot reach us.
        os.setsid()
        # Reset inherited parent signal handlers.
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        # SIGTERM/SIGINT: let worker_main install its own handlers.
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Close router-end fds and other workers' fds in this child
        for wid, (router_fd, worker_fd) in self._control_channels.items():
            try:
                os.close(router_fd)
            except OSError:
                pass
            if wid != worker_id:
                try:
                    os.close(worker_fd)
                except OSError:
                    pass

        # Close writer-end fds and other workers' write fds in this child
        for wid, (w_worker_fd, w_writer_fd) in self._write_channels.items():
            try:
                os.close(w_writer_fd)
            except OSError:
                pass
            if wid != worker_id:
                try:
                    os.close(w_worker_fd)
                except OSError:
                    pass

        # Close dispatch channel fds not belonging to this worker
        for wid, (router_fd, worker_fd) in self._dispatch_channels.items():
            if router_fd >= 0:
                try:
                    os.close(router_fd)
                except OSError:
                    pass
            if wid != worker_id and worker_fd >= 0:
                try:
                    os.close(worker_fd)
                except OSError:
                    pass

        # Close thick writer channel fds in worker (not needed)
        if self._thick_writer_channel is not None:
            for fd in self._thick_writer_channel:
                if fd >= 0:
                    try:
                        os.close(fd)
                    except OSError:
                        pass

        # Pass the worker's control channel fd instead of the listen fd
        control_fd = self._control_channels[worker_id][1]
        write_fd = self._write_channels[worker_id][0]
        dispatch_fd = None
        if self._router_mode == 'thick' and worker_id in self._dispatch_channels:
            dispatch_fd = self._dispatch_channels[worker_id][1]
        self._worker_main(control_fd, self._uds_path, worker_id,
                          write_fd=write_fd, dispatch_fd=dispatch_fd)

    # ------------------------------------------------------------------
    # parent signal handlers
    # ------------------------------------------------------------------

    def _install_parent_signals(self):
        signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def _handle_sigchld(self, signum, frame):
        '''Reap exited children and queue restarts (signal-safe).

        This handler only reaps via waitpid and records which slots need
        restart.  Actual fork happens in process_pending_restarts() which
        runs from the event loop, not from a signal handler.
        '''
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break

            if pid == self._router_pid:
                if os.WIFSIGNALED(status):
                    sig = os.WTERMSIG(status)
                    logger.error('Router pid %d killed by signal %d', pid, sig)
                else:
                    code = os.WEXITSTATUS(status)
                    logger.error('Router pid %d exited with code %d', pid, code)
                self._router_pid = None
                continue

            if pid == self._thick_router_pid:
                if os.WIFSIGNALED(status):
                    sig = os.WTERMSIG(status)
                    logger.error('Thick router pid %d killed by signal %d', pid, sig)
                else:
                    code = os.WEXITSTATUS(status)
                    logger.error('Thick router pid %d exited with code %d', pid, code)
                self._thick_router_pid = None
                continue

            if pid in self._worker_pids:
                idx = self._worker_pids.index(pid)
                self._worker_pids[idx] = None

                if os.WIFSIGNALED(status):
                    sig = os.WTERMSIG(status)
                    logger.error('Worker pid %d killed by signal %d', pid, sig)
                else:
                    code = os.WEXITSTATUS(status)
                    logger.error('Worker pid %d exited with code %d', pid, code)

                if not self._shutdown_flag:
                    self._pending_restarts.append(idx)

    def install_loop_signal_handler(self, loop):
        '''Install an async-safe SIGCHLD handler on the event loop.

        Replaces the raw signal.signal handler with loop.add_signal_handler
        so that SIGCHLD wakes the event loop and restarts are processed
        safely (not inside a signal handler).
        '''
        self._loop = loop

        def _on_sigchld():
            # Reap children (async-signal-safe part)
            self._handle_sigchld(signal.SIGCHLD, None)
            # Schedule restarts from the event loop (safe to fork here)
            self.process_pending_restarts()

        loop.add_signal_handler(signal.SIGCHLD, _on_sigchld)

    def process_pending_restarts(self):
        '''Fork new workers for any slots that died.  Must be called from
        the main thread (not from a signal handler).'''
        while self._pending_restarts:
            idx = self._pending_restarts.pop(0)
            self.restart_worker(idx)

    # ------------------------------------------------------------------
    # restart / shutdown
    # ------------------------------------------------------------------

    def restart_worker(self, idx):
        '''Respawn the worker at slot *idx* with a fresh socketpair.

        F-5 fix: The old socketpair is dead. Create a new one, fork the
        worker, then restart the router so it picks up the new fd.
        '''
        old_pid = self._worker_pids[idx]
        if old_pid is not None:
            logger.warning('restart_worker called for slot %d but pid %d still tracked', idx, old_pid)

        # Create a fresh socketpair for this worker
        router_end, worker_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self._control_channels[idx] = (router_end.fileno(), worker_end.fileno())
        router_end.detach()
        worker_end.detach()

        # Create a fresh write channel socketpair
        worker_write, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self._write_channels[idx] = (worker_write.fileno(), writer_end.fileno())
        worker_write.detach()
        writer_end.detach()

        # Create a fresh dispatch channel socketpair (thick mode)
        if self._router_mode == 'thick':
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

        # Restart the router so it gets the new control channel fd
        self._restart_router()

    def get_write_channel_fds(self):
        '''Return {worker_id: writer_end_fd} for the writer process.

        Called after fork_router() when the parent becomes the writer.
        Only writer-end fds remain open at this point (worker-end fds
        were closed in fork_router).
        '''
        return {wid: wfd for wid, (_, wfd) in self._write_channels.items() if wfd >= 0}

    def _restart_router(self):
        '''Kill the old router and fork a new one with current control channels.'''
        if self._router_pid is not None:
            try:
                os.kill(self._router_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self._router_pid, 0)
            except ChildProcessError:
                pass
            self._router_pid = None

        self.fork_router(self._listen_fd)

        # Also restart thick router if in thick mode (needs new dispatch fds)
        if self._router_mode == 'thick' and self._thick_router_pid is not None:
            try:
                os.kill(self._thick_router_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(self._thick_router_pid, 0)
            except ChildProcessError:
                pass
            self._thick_router_pid = None
            self.fork_thick_router(self._thick_listen_fd)

    def shutdown(self):
        '''Send SIGTERM to router first, then workers, wait with timeout, SIGKILL stragglers.'''
        self._shutdown_flag = True

        # Phase 0: Stop routers first (no new connections)
        for rpid_attr in ('_router_pid', '_thick_router_pid'):
            rpid = getattr(self, rpid_attr)
            if rpid is not None:
                try:
                    os.kill(rpid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(rpid, 0)
                except ChildProcessError:
                    pass
                setattr(self, rpid_attr, None)

        alive = [p for p in self._worker_pids if p is not None]
        if not alive:
            return

        # Phase 1: SIGTERM
        for pid in alive:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        # Phase 2: wait up to SHUTDOWN_GRACE seconds
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

        # Phase 3: SIGKILL stragglers
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
    '''Entry point for the thick router child process.

    Runs an asyncio event loop hosting the ThickRouter which owns all client
    connections, classifies queries, and dispatches to workers/writer.

    Args:
        listen_fd: Listening socket fd (port 27493).
        worker_dispatch_fds: dict {worker_id: fd} — dispatch socketpairs to workers.
        writer_dispatch_fd: int — dispatch socketpair to writer.
    '''
    import synapse.lib.thickrouter as s_thickrouter

    async def _run():
        router = s_thickrouter.ThickRouter(
            cell=None,  # No cell in router process; dispatch-only mode
            worker_fds=worker_dispatch_fds,
            writer_fd=writer_dispatch_fd,
        )
        await router.start()

        # Listen on the inherited socket fd
        import socket as _socket
        sock = _socket.socket(fileno=listen_fd)
        sock.setblocking(False)
        await router.listen(f'tcp://0.0.0.0', ssl=None, sock=sock)

        # Block until shutdown signal
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
    '''Re-open LMDB environments in the writer process after fork.

    _close_all_slabs() closed all lenv handles before fork.  The writer
    needs them back in read-write mode.  Also resets isfini on slabs that
    were marked fini by _stop_memlock_threads(), and re-opens all cached
    database handles against the new environment.
    '''
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
            # Recreate asyncio events bound to the new loop
            slab.lockdoneevent = asyncio.Event()
            slab.lockdoneevent.set()  # no memlock in writer after fork

            if not slab.readonly:
                slab._initCoXact()

            # Re-open all cached database handles against the new env
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
