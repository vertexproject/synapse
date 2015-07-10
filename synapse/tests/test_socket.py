import unittest

import synapse.socket as s_socket

class SocketTest(unittest.TestCase):

    def test_sock_xform(self):

        class Xor(s_socket.SockXform):
            def send(self, byts):
                return bytes([ b ^ 0x56 for b in byts ])

            def recv(self, byts):
                return bytes([ b ^ 0x56 for b in byts ])

        lisn = s_socket.listen( ('127.0.0.1',0) )

        sockaddr = lisn.getsockname()

        sock1 = s_socket.connect(sockaddr)
        sock2,addr = lisn.accept()

        sock1.sendall(b'woot')
        self.assertEqual( sock2.recvall(4), b'woot' )

        xform = Xor()
        sock1.addSockXform(xform)
        sock2.addSockXform(xform)

        sock1.sendall(b'woot')
        self.assertEqual( sock2.recvall(4), b'woot' )
