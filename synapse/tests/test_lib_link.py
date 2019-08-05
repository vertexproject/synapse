import synapse.tests.utils as s_test

import synapse.lib.coro as s_coro
import synapse.lib.link as s_link

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
