import socket
import asyncio
import logging

import collections

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

readsize = 10 * s_const.megabyte

async def connect(host, port, ssl=None):
    '''
    Async connect and return a Link().
    '''
    info = {'host': host, 'port': port, 'ssl': ssl}
    reader, writer = await asyncio.open_connection(host, port, ssl=ssl)
    return await Link.anit(reader, writer, info=info)

async def listen(host, port, onlink, ssl=None):
    '''
    Listen on the given host/port and fire onlink(Link).

    Returns a server object that contains the listening sockets
    '''
    async def onconn(reader, writer):
        link = await Link.anit(reader, writer)
        link.schedCoro(onlink(link))

    server = await asyncio.start_server(onconn, host=host, port=port, ssl=ssl)
    return server

async def unixlisten(path, onlink):
    '''
    Start an PF_UNIX server listening on the given path.
    '''
    info = {'path': path, 'unix': True}
    async def onconn(reader, writer):
        link = await Link.anit(reader, writer, info=info)
        link.schedCoro(onlink(link))
    return await asyncio.start_unix_server(onconn, path=path)

async def unixconnect(path):
    '''
    Connect to a PF_UNIX server listening on the given path.
    '''
    reader, writer = await asyncio.open_unix_connection(path=path)
    info = {'path': path, 'unix': True}
    return await Link.anit(reader, writer, info=info)

class Link(s_base.Base):
    '''
    A Link() is created to wrap a socket reader/writer.
    '''
    async def __anit__(self, reader, writer, info=None):

        await s_base.Base.__anit__(self)

        self.iden = s_common.guid()

        self.reader = reader
        self.writer = writer

        self.rxqu = collections.deque()

        self.sock = self.writer.get_extra_info('socket')

        self._drain_lock = asyncio.Lock()

        if info is None:
            info = {}

        if not info.get('unix'):

            # disable nagle ( to minimize latency for small xmit )
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # enable TCP keep alives...
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, 'TCP_KEEPIDLE'):
                # start sending a keep alives after 3 sec of inactivity
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 3)
                # send keep alives every 3 seconds once started
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
                # close the socket after 5 failed keep alives (15 sec)
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

        self.info = info

        self.unpk = s_msgpack.Unpk()

        async def fini():
            self.writer.close()

        self.onfini(fini)

    async def send(self, byts):
        self.writer.write(byts)
        # Avoid Python bug.  See https://bugs.python.org/issue29930
        async with self._drain_lock:
            await self.writer.drain()

    async def tx(self, mesg):
        '''
        Async transmit routine which will wait for writer drain().
        '''
        if self.isfini:
            raise s_exc.IsFini()

        byts = s_msgpack.en(mesg)
        try:

            self.writer.write(byts)

            # Avoid Python bug.  See https://bugs.python.org/issue29930
            async with self._drain_lock:
                await self.writer.drain()

        except Exception as e:

            await self.fini()

            einfo = s_common.retnexc(e)
            logger.debug('link.tx connection trouble %s', einfo)

            raise

    async def recv(self, size):
        return await self.reader.read(size)

    async def recvsize(self, size):
        byts = b''
        while size:

            recv = await self.reader.read(size)
            if not recv:
                await self.fini()
                return None

            size -= len(recv)
            byts += recv

        return byts

    async def rx(self):

        while not self.rxqu:

            if self.isfini:
                return None

            try:

                byts = await self.reader.read(readsize)
                if not byts:
                    await self.fini()
                    return None

                for size, mesg in self.feed(byts):
                    self.rxqu.append(mesg)

            except (BrokenPipeError, ConnectionResetError) as e:
                logger.warning('%s', str(e))
                await self.fini()
                return None

            except asyncio.CancelledError:
                await self.fini()
                raise

            except Exception:
                logger.exception('rx error')
                await self.fini()
                return None

        return self.rxqu.popleft()

    def get(self, name, defval=None):
        '''
        Get a property from the Link info.
        '''
        return self.info.get(name, defval)

    def set(self, name, valu):
        '''
        Set a property in the Link info.
        '''
        self.info[name] = valu

    def feed(self, byts):
        '''
        Used by Plex() to unpack bytes.
        '''
        return self.unpk.feed(byts)
