from __future__ import absolute_import, unicode_literals
import unittest
import threading

import synapse.compat as s_compat
import synapse.lib.scope as s_scope
import synapse.lib.socket as s_socket

from synapse.tests.common import *

class SocketTest(SynTest):

    def test_sock_plex(self):

        def onmesg(event):
            sock = event[1].get('sock')
            mesg = event[1].get('mesg')

            sock.tx(tufo('hi:got', mesg=mesg))

        plex = s_socket.Plex()
        plex.on('link:sock:mesg', onmesg)

        s1, s2 = s_socket.socketpair()

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
        self.eq(len(plex.getPlexSocks()), 2)

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
