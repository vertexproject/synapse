'''
Thin router process — accepts TCP connections and passes fds to workers via SCM_RIGHTS.

Synchronous (no asyncio). Uses epoll for multiplexing the listen socket
and per-worker UDS control channels.
'''
import os
import array
import signal
import select
import socket
import logging

logger = logging.getLogger(__name__)

# Protocol bytes
NEW_CONN = b'\x01'
READY = b'\x52'


def send_fd(uds_sock, conn_fd):
    '''Send a file descriptor over a UDS socket via SCM_RIGHTS.'''
    fds = array.array('i', [conn_fd])
    uds_sock.sendmsg([NEW_CONN], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])


def recv_fd(uds_sock):
    '''Receive a file descriptor from a UDS socket. Returns fd or None.'''
    try:
        msg, ancdata, flags, addr = uds_sock.recvmsg(1, socket.CMSG_SPACE(4))
    except (OSError, ConnectionError):
        return None
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            fds = array.array('i')
            fds.frombytes(cmsg_data[:4])
            return fds[0]
    return None


class RouterProcess:
    '''Synchronous router: accept on listen_fd, round-robin sendmsg to workers.'''

    def __init__(self, listen_fd, worker_uds_fds):
        self._listen_fd = listen_fd
        self._worker_fds = dict(worker_uds_fds)  # {worker_id: uds_fd}
        self._ready = set()
        self._alive = set(self._worker_fds.keys())
        self._rr_index = 0
        self._stopping = False

        # F-8 fix: Set all worker UDS fds non-blocking so a slow worker
        # cannot stall the entire router's accept loop.
        for fd in self._worker_fds.values():
            os.set_inheritable(fd, False)
            os.set_blocking(fd, False)

    def router_main(self):
        '''Entry point after fork. Blocks until shutdown.'''
        os.setsid()
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

        logger.info('Router pid %d: waiting for workers', os.getpid())
        self._wait_for_workers()

        if not self._ready:
            logger.error('Router: no workers became ready, exiting')
            return

        logger.info('Router pid %d: entering accept loop (%d workers ready)',
                     os.getpid(), len(self._ready))
        self._accept_loop()
        logger.info('Router pid %d: stopped', os.getpid())

    def _wait_for_workers(self):
        '''Block until all workers send READY or die.'''
        ep = select.epoll()
        pending = {}
        for wid, fd in self._worker_fds.items():
            ep.register(fd, select.EPOLLIN | select.EPOLLHUP)
            pending[fd] = wid

        while pending and not self._stopping:
            try:
                events = ep.poll(1.0)
            except OSError:
                break
            for fd, event in events:
                wid = pending.get(fd)
                if wid is None:
                    continue
                if event & select.EPOLLHUP:
                    self._alive.discard(wid)
                    del pending[fd]
                    continue
                if event & select.EPOLLIN:
                    try:
                        data = os.read(fd, 1)
                    except OSError:
                        self._alive.discard(wid)
                        del pending[fd]
                        continue
                    if data == READY:
                        self._ready.add(wid)
                        del pending[fd]
                        logger.info('Router: worker %d ready', wid)

        ep.close()

    def _accept_loop(self):
        '''epoll on listen_fd, accept, round-robin sendmsg to workers.'''
        listen_sock = socket.socket(fileno=self._listen_fd)
        listen_sock.setblocking(False)

        ep = select.epoll()
        ep.register(self._listen_fd, select.EPOLLIN)

        # Also monitor worker UDS for HUP (dead workers)
        for wid in list(self._alive):
            fd = self._worker_fds[wid]
            ep.register(fd, select.EPOLLHUP)

        while not self._stopping:
            pool = self._alive & self._ready
            if not pool:
                try:
                    events = ep.poll(1.0)
                except OSError:
                    break
                self._process_hup_events(events)
                continue

            try:
                events = ep.poll(1.0)
            except OSError:
                break

            for fd, event in events:
                if fd == self._listen_fd and (event & select.EPOLLIN):
                    self._do_accept(listen_sock)
                else:
                    self._check_hup(fd, event)

        ep.close()
        listen_sock.detach()

    def _do_accept(self, listen_sock):
        '''Accept and dispatch one connection.'''
        try:
            conn, addr = listen_sock.accept()
        except (BlockingIOError, OSError):
            return

        conn_fd = conn.fileno()

        # F-8 fix: Try round-robin workers; skip any whose UDS would block.
        pool = sorted(self._alive & self._ready)
        dispatched = False
        for _ in range(len(pool)):
            worker = self._next_worker()
            if worker is None:
                break
            uds_fd = self._worker_fds[worker]
            uds_sock = socket.socket(fileno=uds_fd)
            try:
                send_fd(uds_sock, conn_fd)
                dispatched = True
            except BlockingIOError:
                logger.debug('Router: worker %d UDS full, skipping', worker)
            except OSError:
                logger.warning('Router: sendmsg to worker %d failed', worker)
                self._alive.discard(worker)
            finally:
                uds_sock.detach()
            if dispatched:
                break

        if not dispatched:
            logger.warning('Router: no worker could accept connection, dropping')

        conn.close()

    def _next_worker(self):
        '''Round-robin, skip dead workers.'''
        pool = sorted(self._alive & self._ready)
        if not pool:
            return None
        idx = self._rr_index % len(pool)
        self._rr_index += 1
        return pool[idx]

    def _process_hup_events(self, events):
        for fd, event in events:
            self._check_hup(fd, event)

    def _check_hup(self, fd, event):
        if not (event & select.EPOLLHUP):
            return
        for wid, wfd in self._worker_fds.items():
            if wfd == fd:
                logger.warning('Router: worker %d UDS hung up', wid)
                self._alive.discard(wid)
                break

    def _handle_sigterm(self, signum, frame):
        self._stopping = True

    def shutdown(self):
        self._stopping = True
