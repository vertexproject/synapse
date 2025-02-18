import socket
import asyncio
import logging
import collections

import cryptography.x509 as c_x509
import cryptography.hazmat.primitives.hashes as c_hashes

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

READSIZE = 16 * s_const.mebibyte
MAXWRITE = 64 * s_const.mebibyte

async def connect(host, port, ssl=None, hostname=None, linkinfo=None):
    '''
    Async connect and return a Link().
    '''
    info = {'host': host, 'port': port, 'ssl': ssl, 'hostname': hostname, 'tls': bool(ssl)}
    if linkinfo is not None:
        info.update(linkinfo)

    ssl = info.get('ssl')
    hostname = info.get('hostname')

    reader, writer = await asyncio.open_connection(host, port, ssl=ssl, server_hostname=hostname)
    return await Link.anit(reader, writer, info=info)

async def listen(host, port, onlink, ssl=None):
    '''
    Listen on the given host/port and fire onlink(Link).

    Returns a server object that contains the listening sockets
    '''
    async def onconn(reader, writer):
        info = {'tls': bool(ssl)}
        link = await Link.anit(reader, writer, info=info)
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

async def linkfile(mode='wb'):
    '''
    Connect a socketpair to a file-object and return (link, file).
    '''
    sock0, sock1 = socket.socketpair()

    file1 = sock1.makefile(mode)
    sock1.close()

    reader, writer = await asyncio.open_connection(sock=sock0)
    link0 = await Link.anit(reader, writer, info={'unix': True})

    return link0, file1

async def linksock(forceclose=False):
    '''
    Connect a Link, socket pair.
    '''
    sock0, sock1 = socket.socketpair()
    reader, writer = await asyncio.open_connection(sock=sock0)
    link0 = await Link.anit(reader, writer, info={'unix': True}, forceclose=forceclose)
    return link0, sock1

async def fromspawn(spawninfo):
    sock = spawninfo.get('sock')
    info = spawninfo.get('info', {})
    info['spawn'] = True
    reader, writer = await asyncio.open_connection(sock=sock)
    return await Link.anit(reader, writer, info=info)

class Link(s_base.Base):
    '''
    A Link() is created to wrap a socket reader/writer.
    '''
    async def __anit__(self, reader, writer, info=None, forceclose=False):

        await s_base.Base.__anit__(self)

        self.iden = s_common.guid()

        writer.transport.set_write_buffer_limits(high=1)

        self.reader = reader
        self.writer = writer

        self.rxqu = collections.deque()

        self.sock = self.writer.get_extra_info('socket')
        self.peercert = self.writer.get_extra_info('peercert')

        self._txlock = asyncio.Lock()
        self._forceclose = forceclose

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

        self._addrinfo = {}
        # _addrinfo is populated in this order so that as first hit tls links (prod deployments)
        # then unix links (unit tests with local sockets, container healthchecks, local tools )
        # then tcp links ( unit tests and legacy deployments )
        if self.info.get('tls'):
            self._addrinfo['family'] = 'tls'
            self._addrinfo['addr'] = self.sock.getpeername()
        elif self.info.get('unix'):
            self._addrinfo['family'] = 'unix'
            # Unix sockets don't use getpeername
            self._addrinfo['addr'] = self.sock.getsockname()
        else:
            self._addrinfo['family'] = 'tcp'
            self._addrinfo['addr'] = self.sock.getpeername()
        if self.sock.family == socket.AF_INET:
            self._addrinfo['ipver'] = 'ipv4'
        elif self.sock.family == socket.AF_INET6:
            self._addrinfo['ipver'] = 'ipv6'

        self.unpk = s_msgpack.Unpk()

        async def fini():
            self.writer.close()
            if self._forceclose:
                self.reader._transport.abort()
            try:
                await self.writer.wait_closed()
            except Exception as e:
                logger.debug('Link error waiting on close: %s', str(e))

        self.onfini(fini)

        self.certhash = info.get('certhash')
        self.hostname = info.get('hostname')

        if self.certhash is not None:

            byts = info.get('ssl').telessl.getpeercert(True)
            cert = c_x509.load_der_x509_certificate(byts)
            thishash = s_common.ehex(cert.fingerprint(c_hashes.SHA256()))
            if thishash != self.certhash:
                mesg = f'Server cert does not match pinned certhash={self.certhash}.'
                raise s_exc.LinkBadCert(mesg=mesg)

        elif self.hostname is not None:
            if self.hostname != self.getTlsPeerCn():
                mesg = f'Expected: {self.hostname} Got: {self.getTlsPeerCn()}'
                await self.fini()
                raise s_exc.BadCertHost(mesg=mesg)

    def getTlsPeerCn(self):

        if self.peercert is None:
            return None

        for items in self.peercert.get('subject', ()):
            for name, valu in items:
                if name == 'commonName':
                    return valu

    async def getSpawnInfo(self):
        info = {}

        # selectively add info for pickle...
        if self.info.get('unix'):
            info['unix'] = True

        if self.info.get('tls'):
            info['unix'] = True
            link0, sock = await linksock()
            link0.onfini(sock.close)

            async def relay(link):
                async with link:
                    while True:
                        byts = await link.recv(1024)
                        if not byts:
                            break
                        await self.send(byts)

            self.schedCoro(relay(link0))

        else:
            sock = self.reader._transport._sock

        return {
            'info': info,
            'sock': sock,
        }

    def getAddrInfo(self):
        '''
        Get a summary of address information related to the link.
        '''
        return dict(self._addrinfo)

    async def send(self, byts):

        offs = 0
        size = len(byts)

        async with self._txlock:

            while offs < size:

                self.writer.write(byts[offs:offs + MAXWRITE])
                offs += MAXWRITE

                await self.writer.drain()

    async def tx(self, mesg):
        '''
        Async transmit routine which will wait for writer drain().
        '''
        if self.isfini:
            raise s_exc.IsFini()

        offs = 0
        byts = s_msgpack.en(mesg)
        size = len(byts)

        async with self._txlock:

            try:

                while offs < size:

                    self.writer.write(byts[offs:offs + MAXWRITE])
                    offs += MAXWRITE

                    await self.writer.drain()

            except (asyncio.CancelledError, Exception) as e:

                await self.fini()

                einfo = s_common.retnexc(e)
                logger.debug('link.tx connection trouble %s', einfo)

                raise

    def txfini(self):
        self.sock.shutdown(1)

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

                byts = await self.reader.read(READSIZE)
                if not byts:
                    await self.fini()
                    return None

                for _, mesg in self.feed(byts):
                    self.rxqu.append(mesg)

            except asyncio.CancelledError:
                await self.fini()
                raise

            except Exception as e:
                mesg = f'rx error {e} link={self.getAddrInfo()}'
                if isinstance(e, (BrokenPipeError, ConnectionResetError)):
                    logger.warning(mesg)
                else:
                    logger.exception(mesg)
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
