from __future__ import absolute_import, unicode_literals
import unittest
import threading

import synapse.compat as s_compat
import synapse.lib.scope as s_scope
import synapse.lib.socket as s_socket

from synapse.tests.common import *

def xor(k, byts):
    if s_compat.version < (3, 0, 0):
        return ''.join([chr(ord(b) ^ k) for b in byts])
    else:
        return bytes([b ^ k for b in byts])

class SocketTest(SynTest):

    def test_sock_xform(self):

        class Xor(s_socket.SockXform):
            def txform(self, byts):
                return xor(0x56, byts)

            def rxform(self, byts):
                return xor(0x56, byts)

        sock1, sock2 = s_socket.socketpair()

        sock1.sendall(b'woot')

        self.eq(sock2.recvall(4), b'woot')

        xform = Xor()
        sock1.addSockXform(xform)
        sock2.addSockXform(xform)

        sock1.sendall(b'woot')
        self.eq(sock2.recvall(4), b'woot')

    def test_sock_plex(self):

        def onmesg(event):
            sock = event[1].get('sock')
            mesg = event[1].get('mesg')

            sock.tx(tufo('hi:got', mesg=mesg))

        plex = s_socket.Plex()

        s1, s2 = s_socket.socketpair()
        s2.on('link:sock:mesg', onmesg)

        waiter = self.getTestWait(s2, 1, 'link:sock:mesg')

        plex.addPlexSock(s2)

        s1.tx(tufo('hi:there', whee='whee'))

        ret = s1.recvobj()
        mesg = ret[1].get('mesg')

        self.eq(ret[0], 'hi:got')

        s1.fini()
        plex.fini()

    def test_sock_plex_txbuf(self):
        # windows sockets seem to allow *huge* buffers in non-blocking
        # so triggering txbuf takes *way* too much ram to be a feasable test
        if s_thishost.get('platform') == 'windows':
            return

        plex = s_socket.Plex()

        s1, s2 = s_socket.socketpair()

        plex.addPlexSock(s2)

        # the rx socket is a blocking socket which cause calls to
        # rx() to block on the recv() call in the main thread of
        # the python program

        t0 = tufo('hi', there='there')
        t1 = tufo('OMG', y='A' * 409000)
        t2 = tufo('foo', bar='baz')

        s2.tx(t0)
        m0 = s1.recvobj()
        self.eq(m0[0], 'hi')

        # So this is pushing a large message which is going to be
        # transmitted in parts - hence the NEXT assertion statement
        s2.tx(t1)

        self.nn(s2.txbuf)

        s2.tx(t2)

        self.eq(len(s2.txque), 1)

        m1 = s1.recvobj()
        m2 = s1.recvobj()

        self.eq(len(m1[1].get('y')), 409000)
        self.eq(m2[0], 'foo')

        s1.fini()
        s2.fini()
        plex.fini()

    def test_socket_hostaddr(self):
        self.nn(s_socket.hostaddr())

    def test_socket_glob_plex(self):
        plex0 = s_scope.get('plex')

        self.nn(plex0)

        with s_scope.enter():
            plex1 = s_socket.Plex()
            s_scope.set('plex', plex1)
            self.ne(id(plex0), id(s_scope.get('plex')))
            plex1.fini()

        self.eq(id(plex0), id(s_scope.get('plex')))
