import io
import unittest

import synapse.daemon as s_daemon
import synapse.socket as s_socket
import synapse.service as s_service

from synapse.common import *

class DaemonTest(unittest.TestCase):

    def test_daemon_saveload(self):
        fd = io.BytesIO()
        daemon = s_daemon.Daemon(statefd=fd)

        daemon.addLink('woot1',('tcp',{'host':'127.0.0.1','port':80}))
        daemon.addLink('woot2',('tcp',{'host':'127.0.0.1','port':90}))

        daemon.synFini()

        fd.seek(0)

        daemon = s_daemon.Daemon(statefd=fd)

        self.assertEqual( daemon.getLink('woot1')[1]['port'], 80 )
        self.assertEqual( daemon.getLink('woot2')[1]['port'], 90 )

        daemon.synFini()

    def test_daemon_getlinks(self):
        daemon = s_daemon.Daemon()
        daemon.addLink('woot1',('tcp',{'host':'127.0.0.1','port':80}))
        daemon.addLink('woot2',('tcp',{'host':'127.0.0.1','port':90}))
        self.assertEqual( len(daemon.getLinks()), 2 )

    def test_daemon_syn(self):

        daemon = s_daemon.Daemon()

        link = ('tcpd',{'host':'127.0.0.1','port':0})

        daemon.runLink(link)

        port = link[1].get('port')

        sock = s_socket.connect( ('127.0.0.1',port) )
        self.assertIsNotNone(sock)

        sock.fireobj('dae:syn')
        mesg = sock.recvobj()

        self.assertEqual( mesg[0], 'dae:syn:ret')
        self.assertIsNotNone( mesg[1].get('services') )

        sock.close()
        daemon.synFini()

    def test_daemon_service(self):

        class Woot1(s_service.Service):

            def initServiceLocals(self):
                self.setMesgMethod('woot', self._onMesgWoot )

            def _onMesgWoot(self, sock, mesg):
                sock.sendobj( ('woot',{'foo':'bar'}) )


        daemon = s_daemon.Daemon()
        daemon.addSynService('woot',Woot1(daemon))

        link = ('tcpd',{'host':'127.0.0.1','port':0})
        daemon.runLink(link)

        port = link[1].get('port')

        sock = s_socket.connect( ('127.0.0.1',port) )
        self.assertIsNotNone(sock)

        sock.sendobj( ('woot',{}) )
        mesg = sock.recvobj()

        self.assertEqual( mesg[0], 'woot' )
        self.assertEqual( mesg[1].get('foo'), 'bar' )

    def test_daemon_timeout(self):
        link = ('tcpd',{'host':'127.0.0.1','port':0,'timeout':0.1})

        daemon = s_daemon.Daemon()
        daemon.runLink(link)

        addr = ('127.0.0.1', link[1].get('port'))
        sock = s_socket.connect(addr)
        self.assertEqual( sock.recvobj(),None)

        daemon.synFini()

    def test_daemon_auth_apikey(self):

        fd = io.BytesIO()
        daemon = s_daemon.Daemon(statefd=fd)
        authapi = s_daemon.ApiKeyAuth(daemon)

        apikey = guid()
        authinfo = {'apikey':apikey}

        ident = authapi.getAuthIdent( authinfo )
        self.assertEqual( ident, apikey )

        authapi.addAuthAllow(ident,'foo.bar')

        self.assertTrue( authapi.getAuthAllow( ident, 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.gronk') )

        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.gronk') )

        daemon.synFini()

        fd.seek(0)
        daemon = s_daemon.Daemon(statefd=fd)
        authapi = s_daemon.ApiKeyAuth(daemon)

        self.assertTrue( authapi.getAuthAllow( ident, 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.gronk') )

        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.gronk') )

        authapi.delAuthAllow(ident, 'foo.bar')
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.bar') )
