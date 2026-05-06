'''
Unit tests for synapse.lib.writechannel.WriteChannelListener.

Tests the writer-side write channel listener using socketpairs and a mock
cell, without requiring a full Cortex instance.
'''
import os
import socket
import asyncio
import unittest

import msgpack

import synapse.lib.msgpack as s_msgpack
from synapse.lib.writechannel import WriteChannelListener

# Tests use send_ready=False since they read directly from the fd
# without a _demux_reader that expects the ready byte.
_TEST_SEND_READY = False


class MockCell:
    '''Minimal mock cell that provides storm() and callStorm().'''

    def __init__(self, messages=None, error=None, call_result=None):
        self._messages = messages or []
        self._error = error
        self._call_result = call_result

    async def storm(self, text, opts=None):
        if self._error:
            raise self._error
        for msg in self._messages:
            yield msg

    async def callStorm(self, text, opts=None):
        if self._error:
            raise self._error
        return self._call_result


def _pack(obj):
    return s_msgpack.en(obj)


def _recv_all(fd, unpacker, timeout=5.0):
    '''Read all available msgpack messages from fd within timeout.'''
    msgs = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            data = os.read(fd, 65536)
        except BlockingIOError:
            break
        if not data:
            break
        unpacker.feed(data)
        for msg in unpacker:
            msgs.append(msg)
            # Stop after receiving a 'done' or 'err' message
            if msg[0] in ('done', 'err'):
                return msgs
    return msgs


class TestWriteChannelListener(unittest.TestCase):

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_storm_streaming(self):
        '''Writer streams storm messages back with correct req_id framing.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        storm_msgs = [
            ('node', ({'ndef': ('inet:ipv4', 0x01020304)},)),
            ('node', ({'ndef': ('inet:ipv4', 0x05060708)},)),
        ]
        cell = MockCell(messages=storm_msgs)
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()
            # Send a storm request
            req = ('storm', 'req-1', 'inet:ipv4', None)
            os.write(worker_fd, _pack(req))

            # Read responses
            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            msgs = []
            for _ in range(20):  # poll up to 20 times
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        msgs.append(m)
                    # Check if we got the 'done' message
                    if any(m[0] == 'done' for m in msgs):
                        break

            await listener.stop()
            return msgs

        # Set worker_fd non-blocking for async reads
        import fcntl
        flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
        fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        msgs = self._run(_test())
        os.close(worker_fd)

        # Verify: 2 msg responses + 1 done
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0][0], 'msg')
        self.assertEqual(msgs[0][1], 'req-1')
        self.assertEqual(msgs[0][2], storm_msgs[0])
        self.assertEqual(msgs[1][0], 'msg')
        self.assertEqual(msgs[1][1], 'req-1')
        self.assertEqual(msgs[1][2], storm_msgs[1])
        self.assertEqual(msgs[2][0], 'done')
        self.assertEqual(msgs[2][1], 'req-1')

    def test_storm_error(self):
        '''Writer sends err response when storm() raises.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        cell = MockCell(error=RuntimeError('test error'))
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()
            req = ('storm', 'req-err', 'bad query', None)
            os.write(worker_fd, _pack(req))

            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            msgs = []
            import fcntl
            flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
            fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            for _ in range(20):
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        msgs.append(m)
                    if any(m[0] == 'err' for m in msgs):
                        break

            await listener.stop()
            return msgs

        msgs = self._run(_test())
        os.close(worker_fd)

        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0][0], 'err')
        self.assertEqual(msgs[0][1], 'req-err')
        self.assertIn('mesg', msgs[0][2])

    def test_concurrent_requests(self):
        '''Writer handles concurrent requests with different req_ids.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        storm_msgs = [('node', ({'ndef': ('test:str', 'hello')},))]
        cell = MockCell(messages=storm_msgs)
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()

            import fcntl
            flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
            fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Send two requests back-to-back
            os.write(worker_fd, _pack(('storm', 'r1', 'query1', None)))
            os.write(worker_fd, _pack(('storm', 'r2', 'query2', None)))

            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            msgs = []
            for _ in range(40):
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        msgs.append(m)
                    done_count = sum(1 for m in msgs if m[0] == 'done')
                    if done_count >= 2:
                        break

            await listener.stop()
            return msgs

        msgs = self._run(_test())
        os.close(worker_fd)

        # Should have responses for both req_ids
        r1_msgs = [m for m in msgs if m[1] == 'r1']
        r2_msgs = [m for m in msgs if m[1] == 'r2']
        self.assertEqual(len(r1_msgs), 2)  # 1 msg + 1 done
        self.assertEqual(len(r2_msgs), 2)  # 1 msg + 1 done
        self.assertEqual(r1_msgs[-1][0], 'done')
        self.assertEqual(r2_msgs[-1][0], 'done')

    def test_callStorm(self):
        '''Writer returns result for callStorm requests.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        cell = MockCell(call_result='test-result-value')
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()

            import fcntl
            flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
            fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            req = ('callStorm', 'req-cs', '[ inet:fqdn=x.com ] return($node.repr())', None)
            os.write(worker_fd, _pack(req))

            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            msgs = []
            for _ in range(20):
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        msgs.append(m)
                    if any(m[0] in ('result', 'err') for m in msgs):
                        break

            await listener.stop()
            return msgs

        msgs = self._run(_test())
        os.close(worker_fd)

        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0][0], 'result')
        self.assertEqual(msgs[0][1], 'req-cs')
        self.assertEqual(msgs[0][2], 'test-result-value')

    def test_callStorm_error(self):
        '''Writer sends err response when callStorm() raises.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        cell = MockCell(error=RuntimeError('callStorm failed'))
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()

            import fcntl
            flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
            fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            req = ('callStorm', 'req-cse', 'bad query', None)
            os.write(worker_fd, _pack(req))

            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            msgs = []
            for _ in range(20):
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        msgs.append(m)
                    if any(m[0] == 'err' for m in msgs):
                        break

            await listener.stop()
            return msgs

        msgs = self._run(_test())
        os.close(worker_fd)

        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0][0], 'err')
        self.assertEqual(msgs[0][1], 'req-cse')
        self.assertIn('callStorm failed', msgs[0][2]['mesg'])

    def test_worker_disconnect(self):
        '''Listener handles worker disconnect gracefully.'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        cell = MockCell()
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        async def _test():
            await listener.start()
            # Close worker end — should trigger EPOLLHUP on writer end
            os.close(worker_fd)
            await asyncio.sleep(1.5)  # Let epoll detect it
            await listener.stop()

        # Should not raise
        self._run(_test())

    def test_burst_writes_no_data_loss(self):
        '''Burst of rapid writes completes without data loss (partial write regression).'''
        worker_end, writer_end = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_end.fileno()
        writer_fd = writer_end.fileno()
        worker_end.detach()
        writer_end.detach()

        storm_msgs = [('node', ({'ndef': ('inet:ipv4', i)},)) for i in range(3)]
        cell = MockCell(messages=storm_msgs)
        listener = WriteChannelListener(cell, [writer_fd], send_ready=_TEST_SEND_READY)

        num_requests = 20

        async def _test():
            await listener.start()

            import fcntl
            flags = fcntl.fcntl(worker_fd, fcntl.F_GETFL)
            fcntl.fcntl(worker_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Send many requests as fast as possible
            for i in range(num_requests):
                req = ('storm', f'burst-{i}', f'query-{i}', None)
                data = _pack(req)
                mv = memoryview(data)
                while mv:
                    try:
                        sent = os.write(worker_fd, mv)
                        mv = mv[sent:]
                    except BlockingIOError:
                        await asyncio.sleep(0.01)

            unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
            done_ids = set()
            for _ in range(200):
                await asyncio.sleep(0.05)
                try:
                    data = os.read(worker_fd, 65536)
                except BlockingIOError:
                    continue
                if data:
                    unpacker.feed(data)
                    for m in unpacker:
                        if m[0] == 'done':
                            done_ids.add(m[1])
                if len(done_ids) >= num_requests:
                    break

            await listener.stop()
            return done_ids

        done_ids = self._run(_test())
        os.close(worker_fd)

        self.assertEqual(len(done_ids), num_requests,
                         f'Expected {num_requests} done responses, got {len(done_ids)}')


if __name__ == '__main__':
    unittest.main()
