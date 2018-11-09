import synapse.tests.utils as s_test

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
