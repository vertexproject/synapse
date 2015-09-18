from __future__ import absolute_import, unicode_literals
import unittest
import threading

import synapse.compat as s_compat
import synapse.socket as s_socket

def xor(k,byts):
    if s_compat.version < (3,0,0):
        return ''.join([ chr(ord(b) ^ k) for b in byts ])
    else:
        return bytes([ b ^ k for b in byts ])

class SocketTest(unittest.TestCase):

    def test_sock_xform(self):

        class Xor(s_socket.SockXform):
            def send(self, byts):
                return xor(0x56,byts)

            def recv(self, byts):
                return xor(0x56,byts)

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

    def test_sock_plex(self):

        def onmesg(event):
            sock = event[1].get('sock')
            mesg = event[1].get('mesg')
            sock.fireobj('hi:got', mesg=mesg)

        evt = threading.Event()
        def onfini(event):
            evt.set()

        plex = s_socket.Plex()
        plex.on('link:sock:mesg', onmesg)
        plex.on('link:sock:fini', onfini)

        s1,s2 = s_socket.socketpair()

        plex.addPlexSock(s2)
        self.assertEqual( len(plex), 1 )

        s1.fireobj('hi:there', whee='whee')

        ret = s1.recvobj()
        mesg = ret[1].get('mesg')

        self.assertEqual( ret[0], 'hi:got' )

        s1.fini()

        evt.wait(timeout=1)

        self.assertTrue( evt.is_set() )
        self.assertEqual( len(plex), 0 )

        plex.fini()

