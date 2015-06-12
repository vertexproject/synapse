import unittest

import synapse.socket as s_socket

class SocketTest(unittest.TestCase):

    def test_socket_pool(self):
        data = {}
        def sockmesg(sock,msg):
            data['msg'] = msg
            sock.sendSockMesg(('haha',40))

        pool = s_socket.SocketPool()
        pool.synOn('sockmesg',sockmesg)
        pool.runSockPool()

        lisn = s_socket.listen( ('127.0.0.1',0) )
        self.assertIsNotNone(lisn)

        addr = lisn.getsockname()

        pool.addSockToPool(lisn)

        sock = s_socket.connect(addr)
        self.assertIsNotNone(sock)

        sock.sendSockMesg( ('hehe',30) )

        self.assertEqual(sock.recvSockMesg(),('haha',40))

        self.assertEqual(data.get('msg'),('hehe',30) )

        pool.synFireFini()
        sock.close()

    # FIXME
    #def test_socket_pump(self):

