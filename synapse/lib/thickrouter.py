'''
Thick router process — owns all client telepath connections, classifies
queries, and dispatches reads to workers / writes to the writer via
socketpair RPC.

Workers are pure readers: they receive ('storm', req_id, text, opts) and
stream back ('msg', req_id, mesg) / ('done', req_id) / ('err', req_id, info).
'''
import os
import asyncio
import logging

import msgpack

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.lib.link as s_link
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
import synapse.lib.worker as s_worker

logger = logging.getLogger(__name__)

_RECV_BUF = 65536
_REQ_COUNTER = 0


class _HandshakeProxy:
    '''Minimal proxy for telepath handshake when cell is None.

    Exposes storm as an async generator so getShareInfo marks it genr=True,
    which tells the client proxy to use GenrMethod (t2:genr protocol).
    '''
    async def storm(self, text, opts=None):
        yield  # pragma: no cover

    async def callStorm(self, text, opts=None):
        return None  # pragma: no cover

    async def getCellInfo(self):
        return None  # pragma: no cover


def _next_req_id():
    global _REQ_COUNTER
    _REQ_COUNTER += 1
    return _REQ_COUNTER


class ThickRouter:
    '''Thick router: owns Daemon, classifies queries, dispatches via socketpair RPC.

    Args:
        cell: The Cortex cell object (for Daemon sharing).
        worker_fds: dict {worker_id: fd} — socketpair endpoints to workers.
        writer_fd: int — socketpair endpoint to the writer process.
    '''

    def __init__(self, cell, worker_fds, writer_fd):
        self._cell = cell
        self._worker_fds = dict(worker_fds)  # {wid: fd}
        self._writer_fd = writer_fd
        self._dmon = None
        self._running = False

        # Per-fd msgpack unpackers (SOCK_STREAM framing)
        self._unpackers = {}
        # Per-fd asyncio.Queue for demuxed responses: {fd: {req_id: Queue}}
        self._pending = {}
        # Reader tasks per fd
        self._reader_tasks = {}
        # Outstanding query count per worker for least-outstanding selection
        self._outstanding = {}

        for wid, fd in self._worker_fds.items():
            self._unpackers[fd] = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            self._pending[fd] = {}
            self._outstanding[wid] = 0

        self._unpackers[writer_fd] = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
        self._pending[writer_fd] = {}

    async def start(self):
        '''Initialize the Daemon and start reader tasks for all socketpairs.'''
        self._running = True
        loop = asyncio.get_running_loop()

        # Start demux reader tasks for each worker fd
        for wid, fd in self._worker_fds.items():
            self._reader_tasks[fd] = loop.create_task(self._demux_reader(fd))

        # Start demux reader for writer fd
        self._reader_tasks[self._writer_fd] = loop.create_task(
            self._demux_reader(self._writer_fd))

        # Initialize Daemon and share a proxy placeholder.
        # The thick router intercepts all t2:init messages via _onTaskV2Init,
        # so the shared object is only needed for the tele:syn handshake.
        self._dmon = await s_daemon.Daemon.anit()
        proxy = self._cell if self._cell is not None else _HandshakeProxy()
        self._dmon.share('*', proxy)

        # When cell is None, override _getSharedItem so any share name
        # resolves to the proxy (clients connect with e.g. /cortex).
        if self._cell is None:
            async def _getAnyShare(name):
                return proxy
            self._dmon._getSharedItem = _getAnyShare

        # Override _onTaskV2Init with our dispatch logic
        self._dmon.mesgfuncs['t2:init'] = self._onTaskV2Init

        logger.info('ThickRouter started with %d workers', len(self._worker_fds))

    async def listen(self, url, **opts):
        '''Bind the Daemon to listen on the given URL.'''
        return await self._dmon.listen(url, **opts)

    async def stop(self):
        '''Stop the thick router, cancel reader tasks, close fds.'''
        self._running = False

        for task in self._reader_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self._dmon is not None:
            await self._dmon.fini()

        for fd in self._worker_fds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.close(self._writer_fd)
        except OSError:
            pass

        logger.info('ThickRouter stopped')

    # ------------------------------------------------------------------
    # Demux reader: reads from a socketpair fd and dispatches to queues
    # ------------------------------------------------------------------

    async def _demux_reader(self, fd):
        '''Read msgpack messages from fd and route to per-request queues.'''
        loop = asyncio.get_running_loop()
        unpacker = self._unpackers[fd]

        try:
            while self._running:
                try:
                    data = await loop.run_in_executor(None, os.read, fd, _RECV_BUF)
                except OSError:
                    break
                if not data:
                    break
                unpacker.feed(data)
                for msg in unpacker:
                    # Skip non-tuple messages (e.g. ready byte from PureWorker)
                    if not isinstance(msg, (list, tuple)) or len(msg) < 2:
                        continue
                    req_id = msg[1]
                    q = self._pending[fd].get(req_id)
                    if q is not None:
                        q.put_nowait(msg)
        except asyncio.CancelledError:
            pass
        finally:
            # Signal all waiters on this fd
            for q in self._pending[fd].values():
                q.put_nowait(None)

    # ------------------------------------------------------------------
    # Worker selection: least outstanding queries
    # ------------------------------------------------------------------

    def _select_worker(self):
        '''Select the worker with the fewest outstanding queries.'''
        if not self._worker_fds:
            return None
        wid = min(self._outstanding, key=self._outstanding.get)
        return wid

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    def _send(self, fd, msg):
        '''Send a msgpack-encoded message on fd (blocking, full write).'''
        data = s_msgpack.en(msg)
        mv = memoryview(data)
        while mv:
            try:
                sent = os.write(fd, mv)
            except OSError as e:
                logger.warning('ThickRouter: send failed on fd %d: %s', fd, e)
                return False
            mv = mv[sent:]
        return True

    async def _dispatch_storm(self, fd, text, opts):
        '''Dispatch a storm query to fd and yield response messages.

        Yields:
            Each ('msg', req_id, mesg) payload as mesg.

        Returns when ('done', req_id) is received.

        Raises:
            s_exc.SynErr on ('err', req_id, excinfo) or channel death.
        '''
        req_id = _next_req_id()
        q = asyncio.Queue()
        self._pending[fd][req_id] = q

        try:
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(
                None, self._send, fd, ('storm', req_id, text, opts))
            if not ok:
                raise s_exc.SynErr(mesg='Failed to dispatch to worker/writer')

            while True:
                resp = await q.get()
                if resp is None:
                    raise s_exc.SynErr(mesg='Worker/writer channel died')
                kind = resp[0]
                if kind == 'msg':
                    yield resp[2]
                elif kind == 'done':
                    return
                elif kind == 'err':
                    excinfo = resp[2]
                    raise _ExcInfo(excinfo)
        finally:
            self._pending[fd].pop(req_id, None)

    # ------------------------------------------------------------------
    # t2:init override — the core dispatch logic
    # ------------------------------------------------------------------

    async def _onTaskV2Init(self, link: s_link.Link, mesg):
        '''Handle t2:init: classify, dispatch, relay results to client.'''
        name = mesg[1].get('name')
        sidn = mesg[1].get('sess')
        todo = mesg[1].get('todo')

        try:
            if sidn is None or todo is None:
                raise s_exc.NoSuchObj(name=name)

            # Resolve session (same logic as Daemon._onTaskV2Init)
            sess = self._dmon.sessions.get(sidn)
            if sess is None:
                sess = link.get('sess')
                if sess is not None:
                    item = sess.getSessItem(name)
                    if item is None:
                        raise s_exc.NoSuchObj(name=name)
                else:
                    item = await self._dmon._getSharedItem(name or '*')
                    if item is None:
                        raise s_exc.NoSuchObj(name=name)

                    sess = await s_daemon.Sess.anit()

                    async def sessfini():
                        self._dmon.sessions.pop(sess.iden, None)

                    sess.onfini(sessfini)
                    link.onfini(sess.fini)
                    self._dmon.sessions[sess.iden] = sess
                    link.set('sess', sess)
                    sess.setSessItem(name, item)
            else:
                item = sess.getSessItem(name)
                if item is None:
                    raise s_exc.NoSuchObj(name=name)

            s_scope.set('sess', sess)
            s_scope.set('link', link)

            methname, args, kwargs = todo

            # Intercept storm() and callStorm() for dispatch
            if methname not in ('storm', 'callStorm'):
                # Route non-storm methods to the writer (which has full telepath)
                await self._dispatch_method_to_writer(link, methname, args, kwargs)
                return

            # Extract storm args: storm(text, opts=None)
            text = args[0] if args else kwargs.get('text', '')
            opts = kwargs.get('opts') or (args[1] if len(args) > 1 else None) or {}

            # Propagate user/view context from session into opts
            if 'user' not in opts:
                user = getattr(sess, 'user', None)
                if user is not None:
                    opts = dict(opts)
                    opts['user'] = user

            await self._dispatch_and_relay(link, methname, text, opts)

        except (asyncio.CancelledError, Exception) as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.exception('ThickRouter: error on t2:init: %s',
                                 s_common.trimText(repr(mesg), n=80))
            if not link.isfini:
                retn = s_common.retnexc(e)
                await link.tx(('t2:fini', {'retn': retn}))

    async def _dispatch_and_relay(self, link, methname, text, opts):
        '''Classify, dispatch to worker or writer, relay streaming results.'''
        classification = s_worker.classify(text)

        if methname == 'callStorm':
            # callStorm always goes to writer (it's a write operation)
            await self._relay_callstorm_to_writer(link, text, opts)
        elif classification == 'write':
            await self._relay_to_writer(link, text, opts)
        else:
            await self._relay_to_worker(link, text, opts)

    async def _relay_to_worker(self, link, text, opts):
        '''Dispatch read query to a worker, relay results. Re-dispatch on IsReadOnly.'''
        wid = self._select_worker()
        if wid is None:
            raise s_exc.SynErr(mesg='No workers available')

        fd = self._worker_fds[wid]
        self._outstanding[wid] += 1

        try:
            await link.tx(('t2:genr', {}))

            async for mesg in self._dispatch_storm(fd, text, opts):
                await link.tx(('t2:yield', {'retn': (True, mesg)}))

            await link.tx(('t2:yield', {'retn': None}))

        except _ExcInfo as e:
            if e.excinfo.get('err') == 'IsReadOnly':
                # Re-dispatch to writer (client never sees the failed attempt)
                await self._relay_to_writer_continued(link, text, opts)
            else:
                # Forward error to client
                retn = (False, (e.excinfo.get('err', 'SynErr'),
                                {'mesg': e.excinfo.get('mesg', 'Worker error')}))
                await link.tx(('t2:yield', {'retn': retn}))
                await link.tx(('t2:yield', {'retn': None}))
        finally:
            self._outstanding[wid] -= 1

    async def _relay_to_writer(self, link, text, opts):
        '''Dispatch write query to the writer, relay results.'''
        await link.tx(('t2:genr', {}))

        try:
            async for mesg in self._dispatch_storm(self._writer_fd, text, opts):
                await link.tx(('t2:yield', {'retn': (True, mesg)}))

            await link.tx(('t2:yield', {'retn': None}))

        except _ExcInfo as e:
            retn = (False, (e.excinfo.get('err', 'SynErr'),
                            {'mesg': e.excinfo.get('mesg', 'Writer error')}))
            await link.tx(('t2:yield', {'retn': retn}))
            await link.tx(('t2:yield', {'retn': None}))

    async def _relay_to_writer_continued(self, link, text, opts):
        '''Re-dispatch to writer after IsReadOnly, continuing an already-started stream.'''
        try:
            async for mesg in self._dispatch_storm(self._writer_fd, text, opts):
                await link.tx(('t2:yield', {'retn': (True, mesg)}))

            await link.tx(('t2:yield', {'retn': None}))

        except _ExcInfo as e:
            retn = (False, (e.excinfo.get('err', 'SynErr'),
                            {'mesg': e.excinfo.get('mesg', 'Writer error')}))
            await link.tx(('t2:yield', {'retn': retn}))
            await link.tx(('t2:yield', {'retn': None}))

    async def _relay_callstorm_to_writer(self, link, text, opts):
        '''Dispatch callStorm to the writer and return the result.'''
        req_id = _next_req_id()
        q = asyncio.Queue()
        self._pending[self._writer_fd][req_id] = q

        try:
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(
                None, self._send, self._writer_fd,
                ('callStorm', req_id, text, opts))
            if not ok:
                raise s_exc.SynErr(mesg='Failed to dispatch callStorm to writer')

            resp = await q.get()
            if resp is None:
                raise s_exc.SynErr(mesg='Writer channel died during callStorm')

            kind = resp[0]
            if kind == 'result':
                await link.tx(('t2:fini', {'retn': (True, resp[2])}))
            elif kind == 'err':
                excinfo = resp[2]
                retn = (False, (excinfo.get('err', 'SynErr'),
                                {'mesg': excinfo.get('mesg', 'Writer error')}))
                await link.tx(('t2:fini', {'retn': retn}))
            else:
                raise s_exc.SynErr(mesg=f'Unexpected callStorm response: {kind}')

        finally:
            self._pending[self._writer_fd].pop(req_id, None)


    async def _dispatch_method_to_writer(self, link, methname, args, kwargs):
        '''Dispatch a non-storm method call to the writer and return the result.'''
        req_id = _next_req_id()
        q = asyncio.Queue()
        self._pending[self._writer_fd][req_id] = q

        try:
            loop = asyncio.get_running_loop()
            ok = await loop.run_in_executor(
                None, self._send, self._writer_fd,
                ('method', req_id, methname, args, kwargs))
            if not ok:
                raise s_exc.SynErr(mesg='Failed to dispatch method to writer')

            resp = await q.get()
            if resp is None:
                raise s_exc.SynErr(mesg='Writer channel died during method call')

            kind = resp[0]
            if kind == 'result':
                await link.tx(('t2:fini', {'retn': (True, resp[2])}))
            elif kind == 'err':
                excinfo = resp[2]
                retn = (False, (excinfo.get('err', 'SynErr'),
                                {'mesg': excinfo.get('mesg', 'Writer error')}))
                await link.tx(('t2:fini', {'retn': retn}))
            else:
                raise s_exc.SynErr(mesg=f'Unexpected method response: {kind}')

        finally:
            self._pending[self._writer_fd].pop(req_id, None)


class _ExcInfo(Exception):
    '''Internal exception wrapping an error response from a worker/writer.'''
    def __init__(self, excinfo):
        self.excinfo = excinfo
        super().__init__(excinfo.get('mesg', ''))
