from __future__ import absolute_import, unicode_literals
import unittest
import threading

import synapse.compat as s_compat
import synapse.lib.scope as s_scope
import synapse.lib.socket as s_socket

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

        # XXX We have a common handler for this type of check.
        # windows sockets seem to allow *huge* buffers in non-blocking
        # so triggering txbuf takes *way* too much ram to be a feasable test
        if s_thishost.get('platform') == 'windows':
            return
        print('.\nstart')
        plex = s_socket.Plex()

        s1,s2 = s_socket.socketpair()

        plex.addPlexSock(s2)

        s2.tx( tufo('hi',there='there') )

        self.assertEqual( s1.recvobj()[0], 'hi' )

        t = tufo('OMG', y='A'*409000)
        s2.tx( t )

        self.assertIsNotNone( s2.txbuf )

        s2.tx( tufo('foo', bar='baz') )

        self.assertEqual( len(s2.txque), 1 )
        print('recvobj call 1')
        m1 = s1.recvobj()
        print('recvobj call 2')
        time.sleep(0.01)
        m2 = s1.recvobj()
        print('Checking assertions!')
        self.assertEqual( len(m1[1].get('y')), 409000 )
        self.assertEqual( m2[0], 'foo' )
        print('fini s1')
        s1.fini()
        print('fini s2')
        s2.fini()
        print('plex fini')
        plex.fini()
        print('done test')

    def test_socket_hostaddr(self):
        self.assertIsNotNone( s_socket.hostaddr() )

    def test_socket_glob_plex(self):
        plex0 = s_scope.get('plex')

        self.nn(plex0)

        with s_scope.enter():
            plex1 = s_socket.Plex()
            s_scope.set('plex',plex1)
            self.ne( id(plex0), id( s_scope.get('plex') ) )
            plex1.fini()

        self.eq( id(plex0), id( s_scope.get('plex') ) )
