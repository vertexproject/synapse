import time
import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

from synapse.common import *

class Foo:

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise Exception('derp')

    def speed(self):
        return


class TelePathTest(unittest.TestCase):

    def getFooServ(self):
        link = s_link.chopLinkUrl('tcp://127.0.0.1:0/foo')

        daemon = s_daemon.Daemon()
        daemon.runLinkServer(link)

        daemon.addSharedObject('foo',Foo())

        return daemon,link

    def test_telepath_basics(self):

        daemon,link = self.getFooServ()

        foo = s_telepath.Proxy(link)

        s = time.time()
        for i in range(1000):
            foo.speed()
        e = time.time()

        # ensure perf is still good...
        self.assertTrue( (e - s) < 0.3 )

        self.assertEqual( foo.bar(10,20), 30 )
        self.assertRaises( s_telepath.TeleProtoError, foo.faz, 10, 20 )
        self.assertRaises( s_telepath.RemoteException, foo.baz, 10, 20 )

        foo.fini()
        daemon.fini()

    def test_telepath_auth_apikey(self):

        daemon,link = self.getFooServ()
        authmod = s_daemon.ApiKeyAuth()

        apikey = guid()

        authmod.addAuthRule(apikey,'tele.call.foo.bar')
        daemon.setAuthModule(authmod)

        sockaddr = link[1].get('listen')

        foo = s_telepath.Proxy(link)

        self.assertRaises( s_telepath.TelePermDenied, foo.bar, 20, 30)

        foo.fini()

        link[1]['authinfo'] = {'apikey':apikey}

        foo = s_telepath.Proxy(link)
        self.assertEqual( foo.bar(20,30), 50 )

        foo.fini()
        daemon.fini()

    def test_telepath_chop(self):

        daemon,link = self.getFooServ()

        port = link[1].get('port')

        foo = s_telepath.getProxy('tcp://localhost:%d/foo' % (port,))

        self.assertEqual( foo.bar(10,20), 30 )

        foo.fini()
        daemon.fini()
