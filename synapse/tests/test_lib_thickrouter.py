'''
Unit tests for synapse.lib.thickrouter.ThickRouter.

Tests the thick router dispatch logic using socketpairs and mock workers,
without requiring a full Cortex instance.
'''
import os
import socket
import asyncio
import unittest

import msgpack

import synapse.lib.msgpack as s_msgpack
from synapse.lib.thickrouter import ThickRouter


class MockCell:
    '''Minimal mock cell for Daemon sharing.'''
    pass


def _pack(obj):
    return s_msgpack.en(obj)


def _sendall(fd, data):
    mv = memoryview(data)
    while mv:
        sent = os.write(fd, mv)
        mv = mv[sent:]


class MockWorkerResponder:
    '''Simulates a worker process responding on a socketpair.

    Reads ('storm', req_id, text, opts) and responds with messages.
    '''

    def __init__(self, fd, responses=None, error=None):
        self._fd = fd
        self._responses = responses or []
        self._error = error
        self._task = None

    async def start(self):
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        loop = asyncio.get_running_loop()
        unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
        try:
            while True:
                data = await loop.run_in_executor(None, os.read, self._fd, 65536)
                if not data:
                    break
                unpacker.feed(data)
                for msg in unpacker:
                    await self._handle(msg)
        except (asyncio.CancelledError, OSError):
            pass

    async def _handle(self, msg):
        req_id = msg[1]
        if self._error:
            _sendall(self._fd, _pack(('err', req_id, self._error)))
            return
        for resp in self._responses:
            _sendall(self._fd, _pack(('msg', req_id, resp)))
        _sendall(self._fd, _pack(('done', req_id)))


class TestThickRouterDispatch(unittest.TestCase):
    '''Test the dispatch and relay logic of ThickRouter.'''

    def test_select_worker_least_outstanding(self):
        '''Verify least-outstanding-queries selection.'''
        # Create dummy fds (won't actually be used for I/O here)
        router = ThickRouter(MockCell(), {0: 999, 1: 998}, 997)
        router._outstanding[0] = 5
        router._outstanding[1] = 2
        self.assertEqual(router._select_worker(), 1)

    def test_select_worker_empty(self):
        '''No workers returns None.'''
        router = ThickRouter(MockCell(), {}, 997)
        self.assertIsNone(router._select_worker())


class TestThickRouterIntegration(unittest.IsolatedAsyncioTestCase):
    '''Integration tests using real socketpairs.'''

    async def test_dispatch_read_to_worker(self):
        '''A read query dispatches to a worker and relays results.'''
        # Create socketpairs: router_end <-> worker_end
        r_sock, w_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        router_fd = r_sock.fileno()
        worker_fd = w_sock.fileno()
        r_sock.detach()
        w_sock.detach()

        # Writer socketpair (unused for this test but required)
        wr_sock, ww_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        writer_router_fd = wr_sock.fileno()
        writer_fd = ww_sock.fileno()
        wr_sock.detach()
        ww_sock.detach()

        # Set up mock worker responder
        responder = MockWorkerResponder(worker_fd, responses=[
            ('node', {'iden': 'abc123'}),
            ('node', {'iden': 'def456'}),
        ])
        await responder.start()

        # Create ThickRouter (don't call start() — we test _dispatch_storm directly)
        router = ThickRouter(MockCell(), {0: router_fd}, writer_router_fd)
        router._running = True
        # Start the demux reader for the worker fd
        loop = asyncio.get_running_loop()
        router._reader_tasks[router_fd] = loop.create_task(
            router._demux_reader(router_fd))

        # Give the reader task a moment to start
        await asyncio.sleep(0.05)

        # Dispatch and collect results
        results = []
        async for mesg in router._dispatch_storm(router_fd, 'inet:ipv4', {}):
            results.append(mesg)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ('node', {'iden': 'abc123'}))
        self.assertEqual(results[1], ('node', {'iden': 'def456'}))

        # Cleanup
        await responder.stop()
        router._running = False
        for task in router._reader_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for fd in (router_fd, worker_fd, writer_router_fd, writer_fd):
            try:
                os.close(fd)
            except OSError:
                pass

    async def test_dispatch_error_from_worker(self):
        '''An error response from worker raises _ExcInfo.'''
        r_sock, w_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        router_fd = r_sock.fileno()
        worker_fd = w_sock.fileno()
        r_sock.detach()
        w_sock.detach()

        wr_sock, ww_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        writer_router_fd = wr_sock.fileno()
        writer_fd = ww_sock.fileno()
        wr_sock.detach()
        ww_sock.detach()

        responder = MockWorkerResponder(worker_fd, error={
            'err': 'IsReadOnly',
            'mesg': 'Cannot write in readonly mode',
        })
        await responder.start()

        router = ThickRouter(MockCell(), {0: router_fd}, writer_router_fd)
        router._running = True
        loop = asyncio.get_running_loop()
        router._reader_tasks[router_fd] = loop.create_task(
            router._demux_reader(router_fd))

        await asyncio.sleep(0.05)

        from synapse.lib.thickrouter import _ExcInfo
        with self.assertRaises(_ExcInfo) as ctx:
            async for _ in router._dispatch_storm(router_fd, '[inet:ipv4=1.2.3.4]', {}):
                pass

        self.assertEqual(ctx.exception.excinfo['err'], 'IsReadOnly')

        await responder.stop()
        router._running = False
        for task in router._reader_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for fd in (router_fd, worker_fd, writer_router_fd, writer_fd):
            try:
                os.close(fd)
            except OSError:
                pass


if __name__ == '__main__':
    unittest.main()
