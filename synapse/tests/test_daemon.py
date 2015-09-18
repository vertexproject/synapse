import io
import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *

class DaemonTest(unittest.TestCase):

    def test_daemon_getlinks(self):
        daemon = s_daemon.Daemon()
        daemon.addLinkServer('woot1',tufo('tcp',host='127.0.0.1',port=0))
        daemon.addLinkServer('woot2',tufo('tcp',host='127.0.0.1',port=0))
        self.assertEqual( len(daemon.getLinks()), 2 )
        daemon.fini()

    def test_daemon_extend(self):

        def onwoot(sock,mesg):
            sock.sendobj( ('woot',{'foo':'bar'}) )

        daemon = s_daemon.Daemon()
        daemon.setMesgMeth('woot',onwoot)

        link = tufo('tcp',host='127.0.0.1',port=0)
        daemon.runLinkServer(link)

        relay = s_link.initLinkRelay(link)
        sock = relay.initClientSock()

        self.assertIsNotNone(sock)

        sock.sendobj( ('woot',{}) )
        mesg = sock.recvobj()

        self.assertEqual( mesg[0], 'woot' )
        self.assertEqual( mesg[1].get('foo'), 'bar' )

        sock.fini()
        daemon.fini()

    def test_daemon_timeout(self):
        link = tufo('tcp',host='127.0.0.1',port=0,timeout=0.1)

        daemon = s_daemon.Daemon()
        daemon.runLinkServer(link)

        relay = s_link.initLinkRelay(link)
        sock = relay.initClientSock()

        self.assertEqual( sock.recvobj(),None)

        sock.fini()
        daemon.fini()

    def test_daemon_auth_apikey(self):

        dmonfd = io.BytesIO()
        authfd = io.BytesIO()

        daemon = s_daemon.Daemon(statefd=dmonfd)
        authapi = s_daemon.ApiKeyAuth(statefd=authfd)

        apikey = guid()
        authinfo = {'apikey':apikey}

        ident = authapi.getAuthIdent( authinfo )
        self.assertEqual( ident, apikey )

        authapi.addAuthRule(ident,'foo.bar')

        self.assertTrue( authapi.getAuthAllow( ident, 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.gronk') )

        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.gronk') )

        daemon.fini()

        dmonfd.seek(0)
        authfd.seek(0)

        daemon = s_daemon.Daemon(statefd=dmonfd)
        authapi = s_daemon.ApiKeyAuth(statefd=authfd)

        self.assertTrue( authapi.getAuthAllow( ident, 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.gronk') )

        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.bar') )
        self.assertFalse( authapi.getAuthAllow( guid(), 'foo.gronk') )

        authapi.delAuthRule(ident, 'foo.bar')
        self.assertFalse( authapi.getAuthAllow( ident, 'foo.bar') )

        daemon.fini()
