import ssl
import sys
import socket
import asyncio
import multiprocessing

import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link

import synapse.tests.utils as s_test


# Helpers related to spawn link coverage
async def _spawnTarget(n, info):
    link = await s_link.fromspawn(info)
    async with link:
        await link.send(b'V' * n)

def spawnTarget(n, info):
    asyncio.run(_spawnTarget(n, info))

async def _spawnHost(n, pipe):
    link0, sock0 = await s_link.linksock()
    info = await link0.getSpawnInfo()
    pipe.send(info)
    buf = b''
    j = n
    while True:
        data = sock0.recv(j)
        buf = buf + data
        if len(buf) == n:
            break
        j = n - len(data)

    sock0.close()
    await link0.fini()

    if buf == b'V' * n:
        return

    return 137

def spawnHost(n, pipe: multiprocessing.Pipe):
    ret = asyncio.run(_spawnHost(n, pipe))
    if ret is None:
        return
    sys.exit(ret)

class LinkTest(s_test.SynTest):

    async def test_link_raw(self):

        async def onlink(link):
            self.eq(b'vis', await link.recvsize(3))
            self.eq(b'i', await link.recv(1))
            await link.send(b'vert')
            await link.fini()

        serv = await s_link.listen('127.0.0.1', 0, onlink)
        host, port = serv.sockets[0].getsockname()

        link = await s_link.connect(host, port)
        info = link.getAddrInfo()
        self.eq(info.get('family'), 'tcp')
        self.eq(info.get('ipver'), 'ipv4')

        with mock.patch('synapse.lib.link.MAXWRITE', 2):
            await link.send(b'visi')

        self.eq(b'vert', await link.recvsize(4))
        self.none(await link.recvsize(1))
        await link.fini()
        # We can still get the info after we've closed the socket / fini'd the link.
        self.eq(info, link.getAddrInfo())

    async def test_link_tx_sadpath(self):

        evt = asyncio.Event()

        async def onlink(link):
            msg0 = await link.rx()
            self.eq(('what', {'k': 1}), msg0)
            link.onfini(evt.set)
            await link.fini()

        serv = await s_link.listen('127.0.0.1', 0, onlink)
        host, port = serv.sockets[0].getsockname()
        link = await s_link.connect(host, port)
        await link.tx(('what', {'k': 1}))
        self.true(await s_coro.event_wait(evt, 6))
        # Why does this first TX post fini on the server link work,
        # but the second one fails?
        await link.tx(('me', {'k': 2}))
        await self.asyncraises(ConnectionError, link.tx(('worry?', {'k': 3})))

    async def test_link_rx_sadpath(self):

        junk = 'a9d0cdafef705b9864bd'
        # random sequence of data which causes an error
        # to be thrown when unpacking data via msgpack.
        junk = s_common.uhex(junk)

        evt = asyncio.Event()

        async def onlink(link):
            await link.tx(('what', {'k': 1}))
            self.true(await s_coro.event_wait(evt, 6))
            # Send purposely bad data through the link
            await link.send(junk)
            await link.fini()

        serv = await s_link.listen('127.0.0.1', 0, onlink)
        host, port = serv.sockets[0].getsockname()
        link = await s_link.connect(host, port)
        msg0 = await link.rx()
        self.eq(msg0, ('what', {'k': 1}))
        evt.set()
        await asyncio.sleep(0)
        with self.getAsyncLoggerStream('synapse.lib.link', 'rx error') as stream:
            msg1 = await link.rx()
            self.true(await stream.wait(6))
        self.none(msg1)

    async def test_link_file(self):

        link0, file0 = await s_link.linkfile('rb')

        def reader(fd):
            byts = fd.read()
            fd.close()
            return byts

        coro = s_coro.executor(reader, file0)

        await link0.send(b'asdf')
        await link0.send(b'qwer')

        await link0.fini()

        self.eq(b'asdfqwer', await coro)

        link1, file1 = await s_link.linkfile('wb')

        def writer(fd):
            fd.write(b'asdf')
            fd.write(b'qwer')
            fd.close()

        coro = s_coro.executor(writer, file1)

        byts = b''

        while True:
            x = await link1.recv(1000000)
            if not x:
                break
            byts += x

        await coro

        self.eq(b'asdfqwer', byts)

    async def test_linksock(self):
        link0, sock0 = await s_link.linksock()
        self.isinstance(link0, s_link.Link)
        self.isinstance(sock0, socket.socket)

        def reader(sock):
            buf = b''
            while True:
                byts = sock.recv(1024)
                if not byts:
                    break
                buf += byts
            return buf

        coro = s_coro.executor(reader, sock0)

        await link0.send(b'part1')
        await link0.send(b'qwer')

        await link0.fini()

        self.eq(b'part1qwer', await coro)
        sock0.close()

        link1, sock1 = await s_link.linksock()

        def writer(sock):
            sock.sendall(b'part2')
            sock.sendall(b'qwer')
            sock.shutdown(socket.SHUT_WR)

        coro = s_coro.executor(writer, sock1)
        await coro

        self.eq(b'part2qwer', await link1.recvsize(9))

        await link1.fini()
        sock1.close()

    async def test_link_fromspawns(self):

        n = 100000
        ctx = multiprocessing.get_context('spawn')

        # Remote use test - this is normally how linksock is used.

        link0, sock0 = await s_link.linksock()

        info = await link0.getSpawnInfo()

        def getproc():
            proc = ctx.Process(target=spawnTarget, args=(n, info))
            proc.start()
            return proc

        proc = await s_coro.executor(getproc)

        buf = b''
        j = n
        while True:
            data = sock0.recv(j)
            buf = buf + data
            if len(buf) == n:
                break
            j = n - len(data)

        self.eq(buf, b'V' * n)

        await s_coro.executor(proc.join)

        sock0.close()
        await link0.fini()

        # Coverage test
        mypipe, child_pipe = ctx.Pipe()

        def getproc():
            proc = ctx.Process(target=spawnHost, args=(n, child_pipe))
            proc.start()
            return proc

        proc = await s_coro.executor(getproc)  # type: multiprocessing.Process

        def waitforinfo():
            nonlocal proc
            hasdata = mypipe.poll(timeout=30)
            if not hasdata:
                raise s_exc.SynErr(mesg='failed to get link info')
            info = mypipe.recv()
            return info

        info = await s_coro.executor(waitforinfo)

        link = await s_link.fromspawn(info)
        await link.send(b'V' * n)

        def waitforjoin():
            proc.join()
            return proc.exitcode

        code = await asyncio.wait_for(s_coro.executor(waitforjoin), timeout=30)
        self.eq(code, 0)
        await link.fini()

    async def test_tls_ciphers(self):
        self.thisHostMustNot(platform='darwin')
        self.skipIfNoPath(path='certdir')

        with self.getTestDir(mirror='certdir') as dirn:
            with self.getTestCertDir(dirn) as certdir:

                hostname = socket.gethostname()
                certdir.genHostCert(hostname, signas='ca')

                lport = 0

                async def func(*args, **kwargs):
                    pass

                srv_sslctx = certdir.getServerSSLContext(hostname)  # type: ssl.SSLContext
                # The server context has a default minimum version.
                self.eq(srv_sslctx.minimum_version, ssl.TLSVersion.TLSv1_2)

                # Change the maximum server version to tls 1.1 so that our
                # link ssl context will not work with it.
                srv_sslctx.maximum_version = ssl.TLSVersion.TLSv1_1

                server = await s_link.listen(hostname, lport, onlink=func, ssl=srv_sslctx)
                _, port = server.sockets[0].getsockname()

                sslctx = certdir.getClientSSLContext()  # type: ssl.SSLContext
                # The client context has a default minimum version.
                self.eq(sslctx.minimum_version, ssl.TLSVersion.TLSv1_2)

                try:
                    # Our default does not talk to a TLS server that is lower than TLS 1.2 though.
                    with self.raises(ConnectionResetError):
                        await s_link.connect(hostname, port=port, ssl=sslctx)
                finally:
                    server.close()

                # Ensure we can talk to a TLS link though.
                async def func(link: s_link.Link):
                    self.eq(b'go', await link.recv(2))
                    await link.tx(link.getAddrInfo())
                    await link.fini()

                srv_sslctx = certdir.getServerSSLContext(hostname)  # type: ssl.SSLContext
                server = await s_link.listen(hostname, lport, onlink=func, ssl=srv_sslctx)
                sslctx = certdir.getClientSSLContext()  # type: ssl.SSLContext
                _, port = server.sockets[0].getsockname()
                print(f'listening on port {port=}')
                async with await s_link.connect(hostname, port=port, ssl=sslctx) as link:
                    await link.send(b'go')
                    item = await link.rx()
                    self.eq(link.getAddrInfo().get('family'), 'tls')
                    self.eq(item.get('family'), 'tls')
                server.close()

    async def test_link_unix(self):
        with self.getTestDir() as dirn:

            async def func(link: s_link.Link):
                self.eq(b'go', await link.recv(2))
                await link.tx(link.getAddrInfo())
                await link.fini()
            fp = s_common.genpath(dirn, 'sock')
            server = await s_link.unixlisten(fp, onlink=func)

            async with await s_link.unixconnect(fp) as link:
                await link.send(b'go')
                item = await link.rx()
                self.eq(link.getAddrInfo().get('family'), 'unix')
                self.eq(item.get('addr'), fp)
                self.eq(item.get('family'), 'unix')
            server.close()
