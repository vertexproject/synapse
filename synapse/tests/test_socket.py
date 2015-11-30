from __future__ import absolute_import, unicode_literals
import unittest
import threading

import synapse.compat as s_compat
import synapse.socket as s_socket

from synapse.tests.common import *

def xor(k,byts):
    if s_compat.version < (3,0,0):
        return ''.join([ chr(ord(b) ^ k) for b in byts ])
    else:
        return bytes([ b ^ k for b in byts ])

class SocketTest(SynTest):

    def test_sock_xform(self):

        class Xor(s_socket.SockXform):
            def txform(self, byts):
                return xor(0x56,byts)

            def rxform(self, byts):
                return xor(0x56,byts)

        sock1,sock2 = s_socket.socketpair()

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

            sock.tx( tufo('hi:got', mesg=mesg) )

        plex = s_socket.Plex()

        s1,s2 = s_socket.socketpair()
        s2.on('link:sock:mesg', onmesg)

        waiter = self.getTestWait(s2, 1, 'link:sock:mesg')

        plex.addPlexSock(s2)

        s1.tx( tufo('hi:there', whee='whee') )

        ret = s1.recvobj()
        mesg = ret[1].get('mesg')

        self.assertEqual( ret[0], 'hi:got' )

        s1.fini()
        plex.fini()

    def test_sock_plex_txbuf(self):

        plex = s_socket.Plex()

        s1,s2 = s_socket.socketpair()

        plex.addPlexSock(s2)

        s2.tx( tufo('hi',there='there') )

        self.assertEqual( s1.recvobj()[0], 'hi' )

        s2.tx( tufo('OMG', y='A'*409000) )

        self.assertIsNotNone( s2.txbuf )

        s2.tx( tufo('foo', bar='baz') )

        self.assertEqual( len(s2.txque), 1 )

        m1 = s1.recvobj()
        m2 = s1.recvobj()

        self.assertEqual( len(m1[1].get('y')), 409000 )
        self.assertEqual( m2[0], 'foo' )

        s1.fini()
        s2.fini()

        plex.fini()
