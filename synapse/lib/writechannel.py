'''
Write channel listener for the writer process.

The writer process listens on per-worker write channel socketpairs via epoll.
Workers send write requests (storm/callStorm) as msgpack-encoded tuples;
the writer executes them against the cell and streams results back.

Protocol (all messages are msgpack-encoded, self-delimiting on SOCK_STREAM):

  Request:  ('storm', req_id, text, opts)
  Response: ('msg', req_id, mesg) ...  (one per storm yield)
            ('done', req_id)           (stream complete)
            ('err', req_id, excinfo)   (on error)
'''
import os
import select
import asyncio
import logging

import msgpack

import synapse.exc as s_exc
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# Read buffer size for recv() calls on the write channel socketpairs.
_RECV_BUF = 65536


class WriteChannelListener:
    '''Epoll-based listener that receives write RPCs from worker socketpairs.

    Args:
        cell: The Cortex cell object (provides storm/callStorm methods).
        writer_fds: List of writer-end file descriptors from the arbiter.
    '''

    def __init__(self, cell, writer_fds, send_ready=True):
        self._cell = cell
        self._writer_fds = list(writer_fds)
        self._running = False
        self._task = None
        self._send_ready = send_ready

    async def start(self):
        '''Start the write channel listener as a background task.'''
        self._running = True
        self._task = asyncio.get_running_loop().create_task(self._listen())
        logger.info('Write channel listener started with %d worker fds', len(self._writer_fds))

    async def stop(self):
        '''Stop the listener and close all writer-end fds.'''
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        for fd in self._writer_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        logger.info('Write channel listener stopped')

    async def _listen(self):
        '''Main listener loop: epoll on all writer fds, dispatch requests.'''
        loop = asyncio.get_running_loop()
        ep = select.epoll()

        # Per-fd msgpack unpacker for SOCK_STREAM framing
        unpackers = {}
        for fd in self._writer_fds:
            ep.register(fd, select.EPOLLIN)
            unpackers[fd] = msgpack.Unpacker(**s_msgpack.unpacker_kwargs)

        # Signal readiness to workers: send a single byte on each writer-end
        # fd so the worker's _demux_reader knows the channel is ready.
        if self._send_ready:
            for fd in self._writer_fds:
                try:
                    os.write(fd, b'\x01')
                except OSError as e:
                    logger.warning('Failed to send ready byte on fd %d: %s', fd, e)

        try:
            while self._running:
                # Poll in executor to avoid blocking the event loop
                events = await loop.run_in_executor(None, ep.poll, 1.0)
                for fd, event in events:
                    if event & (select.EPOLLHUP | select.EPOLLERR):
                        logger.warning('Write channel fd %d closed (worker died)', fd)
                        ep.unregister(fd)
                        unpackers.pop(fd, None)
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                        continue

                    if event & select.EPOLLIN:
                        try:
                            data = os.read(fd, _RECV_BUF)
                        except OSError:
                            continue
                        if not data:
                            # EOF — worker closed its end
                            logger.warning('Write channel fd %d EOF', fd)
                            ep.unregister(fd)
                            unpackers.pop(fd, None)
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                            continue

                        unpacker = unpackers[fd]
                        unpacker.feed(data)
                        for msg in unpacker:
                            # Dispatch each request as a concurrent task
                            loop.create_task(self._handle_request(fd, msg))
        except asyncio.CancelledError:
            pass
        finally:
            ep.close()

    async def _handle_request(self, fd, msg):
        '''Handle a single write request and stream results back.

        Args:
            fd: The writer-end fd to send responses on.
            msg: Decoded msgpack tuple: ('storm', req_id, text, opts)
        '''
        try:
            kind = msg[0]
            req_id = msg[1]
        except (IndexError, TypeError):
            logger.error('Malformed write request on fd %d: %r', fd, msg)
            return

        if kind == 'storm':
            await self._handle_storm(fd, req_id, msg)
        elif kind == 'callStorm':
            await self._handle_callStorm(fd, req_id, msg)
        elif kind == 'method':
            await self._handle_method(fd, req_id, msg)
        else:
            logger.error('Unknown write request kind %r on fd %d', kind, fd)
            await self._send(fd, ('err', req_id, {'mesg': f'Unknown request kind: {kind}'}))

    async def _handle_storm(self, fd, req_id, msg):
        '''Execute cell.storm() and stream results back to the worker.'''
        try:
            text = msg[2]
            opts = msg[3] if len(msg) > 3 else None
        except (IndexError, TypeError):
            await self._send(fd, ('err', req_id, {'mesg': 'Malformed storm request'}))
            return

        try:
            async for mesg in self._cell.storm(text, opts=opts):
                await self._send(fd, ('msg', req_id, mesg))
            await self._send(fd, ('done', req_id))
        except Exception as e:
            excinfo = {
                'mesg': str(e),
                'err': e.__class__.__name__,
            }
            await self._send(fd, ('err', req_id, excinfo))

    async def _handle_callStorm(self, fd, req_id, msg):
        '''Execute cell.callStorm() and return the result to the worker.'''
        try:
            text = msg[2]
            opts = msg[3] if len(msg) > 3 else None
        except (IndexError, TypeError):
            await self._send(fd, ('err', req_id, {'mesg': 'Malformed callStorm request'}))
            return

        try:
            result = await self._cell.callStorm(text, opts=opts)
            await self._send(fd, ('result', req_id, result))
        except Exception as e:
            excinfo = {
                'mesg': str(e),
                'err': e.__class__.__name__,
            }
            await self._send(fd, ('err', req_id, excinfo))

    async def _handle_method(self, fd, req_id, msg):
        '''Execute an arbitrary method on the cell and return the result.'''
        try:
            methname = msg[2]
            args = msg[3] if len(msg) > 3 else ()
            kwargs = msg[4] if len(msg) > 4 else {}
        except (IndexError, TypeError):
            await self._send(fd, ('err', req_id, {'mesg': 'Malformed method request'}))
            return

        try:
            meth = getattr(self._cell, methname)
            result = meth(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            # Verify the result is msgpack-serializable (Share objects are not)
            s_msgpack.en(('result', req_id, result))
            await self._send(fd, ('result', req_id, result))
        except (TypeError, OverflowError, s_exc.NotMsgpackSafe) as e:
            # Non-serializable result (e.g., Share object) — explicit error
            excinfo = {
                'mesg': f'Method {methname!r} returned a non-serializable result (Share object). Use storm instead.',
                'err': 'NoSuchMeth',
            }
            await self._send(fd, ('err', req_id, excinfo))
        except Exception as e:
            excinfo = {
                'mesg': str(e),
                'err': e.__class__.__name__,
            }
            await self._send(fd, ('err', req_id, excinfo))

    async def _send(self, fd, msg):
        '''Send a msgpack-encoded message on the given fd.

        For messages under 64KB, writes directly (socketpair writes are
        atomic on Linux for sizes under PIPE_BUF/64KB). Falls back to
        executor for larger messages to avoid blocking the event loop.
        '''
        data = s_msgpack.en(msg)
        try:
            if len(data) < 65536:
                os.write(fd, data)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _sendall, fd, data)
        except OSError as e:
            logger.warning('Write channel send failed on fd %d: %s', fd, e)


def _sendall(fd, data):
    '''Write all bytes to fd, handling partial writes (blocking, thread-safe).'''
    mv = memoryview(data)
    while mv:
        sent = os.write(fd, mv)
        mv = mv[sent:]
