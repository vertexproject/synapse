import socket
import asyncio

import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link

import synapse.tests.utils as s_test

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

        await link.send(b'visi')
        self.eq(b'vert', await link.recvsize(4))
        self.none(await link.recvsize(1))

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

    async def test_link_fromspawn(self):

        link0, sock0 = await s_link.linksock()

        info = await link0.getSpawnInfo()
        link1 = await s_link.fromspawn(info)

        await link1.send(b'V')
        self.eq(sock0.recv(1), b'V')

        sock0.close()

        await link0.fini()
        await link1.fini()
