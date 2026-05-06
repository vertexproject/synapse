'''
Unit tests for PureWorker — the socketpair task receiver for thick router mode.
'''
import os
import socket
import asyncio
import unittest

import msgpack

import synapse.exc as s_exc
import synapse.lib.msgpack as s_msgpack
from synapse.lib.worker import PureWorker


class MockCell:
    '''Mock cell that yields canned storm results.'''

    def __init__(self, results=None, raise_exc=None):
        self._results = results or []
        self._raise_exc = raise_exc

    async def storm(self, text, opts=None):
        if self._raise_exc:
            raise self._raise_exc
        for mesg in self._results:
            yield mesg


class TestPureWorker(unittest.TestCase):

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_worker(self, cell):
        '''Create a PureWorker with a socketpair, return (worker, router_fd).'''
        worker_sock, router_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        worker_fd = worker_sock.fileno()
        router_fd = router_sock.fileno()
        worker_sock.detach()
        router_sock.detach()
        worker = PureWorker(worker_fd, cell)
        return worker, worker_fd, router_fd

    def _read_responses(self, router_fd, timeout=2.0):
        '''Read all msgpack responses from the router fd.'''
        import time
        import select
        responses = []
        unpacker = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            r, _, _ = select.select([router_fd], [], [], min(remaining, 0.1))
            if not r:
                if responses and responses[-1][0] in ('done', 'err'):
                    break
                continue
            data = os.read(router_fd, 65536)
            if not data:
                break
            unpacker.feed(data)
            for msg in unpacker:
                responses.append(msg)
                if msg[0] in ('done', 'err'):
                    return responses
        return responses

    def test_storm_streams_results(self):
        '''PureWorker streams storm messages and sends done.'''
        results = [
            ('init', {'tick': 100}),
            ('node', ({'ndef': ('inet:fqdn', 'test.com')},)),
            ('fini', {'tock': 200}),
        ]
        cell = MockCell(results=results)
        worker, worker_fd, router_fd = self._make_worker(cell)

        async def _test():
            # Start serve in background
            serve_task = asyncio.get_running_loop().create_task(worker.serve())
            # Wait for ready byte
            ready = await asyncio.get_running_loop().run_in_executor(None, os.read, router_fd, 1)
            self.assertEqual(ready, b'\x52')

            # Send a storm task
            req = ('storm', 1, 'inet:fqdn=test.com', {})
            os.write(router_fd, s_msgpack.en(req))

            # Read responses
            responses = await asyncio.get_running_loop().run_in_executor(
                None, self._read_responses, router_fd)

            # Close to stop serve
            os.close(router_fd)
            await asyncio.wait_for(serve_task, timeout=2.0)
            os.close(worker_fd)
            return responses

        responses = self._run(_test())

        # Should have 3 msg + 1 done
        msgs = [r for r in responses if r[0] == 'msg']
        dones = [r for r in responses if r[0] == 'done']
        self.assertEqual(len(msgs), 3)
        self.assertEqual(len(dones), 1)
        self.assertEqual(msgs[0], ('msg', 1, ('init', {'tick': 100})))
        self.assertEqual(msgs[1], ('msg', 1, ('node', ({'ndef': ('inet:fqdn', 'test.com')},))))
        self.assertEqual(dones[0], ('done', 1))

    def test_isreadonly_error(self):
        '''PureWorker returns IsReadOnly error for write queries.'''
        cell = MockCell(raise_exc=s_exc.IsReadOnly(mesg='readonly'))
        worker, worker_fd, router_fd = self._make_worker(cell)

        async def _test():
            serve_task = asyncio.get_running_loop().create_task(worker.serve())
            ready = await asyncio.get_running_loop().run_in_executor(None, os.read, router_fd, 1)
            self.assertEqual(ready, b'\x52')

            req = ('storm', 42, '[ inet:fqdn=evil.com ]', {})
            os.write(router_fd, s_msgpack.en(req))

            responses = await asyncio.get_running_loop().run_in_executor(
                None, self._read_responses, router_fd)

            os.close(router_fd)
            await asyncio.wait_for(serve_task, timeout=2.0)
            os.close(worker_fd)
            return responses

        responses = self._run(_test())

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 'err')
        self.assertEqual(responses[0][1], 42)
        self.assertEqual(responses[0][2]['err'], 'IsReadOnly')

    def test_cancellation(self):
        '''PureWorker stops streaming on cancel.'''
        # Generate many results so cancellation can interrupt
        results = [('node', {'i': i}) for i in range(200)]
        cell = MockCell(results=results)
        worker, worker_fd, router_fd = self._make_worker(cell)

        async def _test():
            serve_task = asyncio.get_running_loop().create_task(worker.serve())
            ready = await asyncio.get_running_loop().run_in_executor(None, os.read, router_fd, 1)
            self.assertEqual(ready, b'\x52')

            # Send storm then immediately cancel
            req = ('storm', 7, 'inet:fqdn', {})
            cancel = ('cancel', 7)
            os.write(router_fd, s_msgpack.en(req) + s_msgpack.en(cancel))

            responses = await asyncio.get_running_loop().run_in_executor(
                None, self._read_responses, router_fd)

            os.close(router_fd)
            await asyncio.wait_for(serve_task, timeout=2.0)
            os.close(worker_fd)
            return responses

        responses = self._run(_test())

        # Should have fewer than 200 messages (cancelled early) and end with done
        msgs = [r for r in responses if r[0] == 'msg']
        dones = [r for r in responses if r[0] == 'done']
        self.assertLess(len(msgs), 200)
        self.assertEqual(len(dones), 1)

    def test_generic_exception(self):
        '''PureWorker returns err on unexpected exceptions.'''
        cell = MockCell(raise_exc=ValueError('something broke'))
        worker, worker_fd, router_fd = self._make_worker(cell)

        async def _test():
            serve_task = asyncio.get_running_loop().create_task(worker.serve())
            ready = await asyncio.get_running_loop().run_in_executor(None, os.read, router_fd, 1)
            self.assertEqual(ready, b'\x52')

            req = ('storm', 99, 'broken', {})
            os.write(router_fd, s_msgpack.en(req))

            responses = await asyncio.get_running_loop().run_in_executor(
                None, self._read_responses, router_fd)

            os.close(router_fd)
            await asyncio.wait_for(serve_task, timeout=2.0)
            os.close(worker_fd)
            return responses

        responses = self._run(_test())

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 'err')
        self.assertEqual(responses[0][1], 99)
        self.assertEqual(responses[0][2]['err'], 'ValueError')
        self.assertIn('something broke', responses[0][2]['mesg'])


if __name__ == '__main__':
    unittest.main()
