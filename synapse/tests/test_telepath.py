import time
import unittest

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
        link = ('tcpd',{'host':'127.0.0.1','port':0})

        daemon = s_daemon.Daemon()
        daemon.runLink(link)

        tele = daemon.loadSynService('telepath')
        tele.addSharedObject('foo',Foo())

        return daemon,link

    def test_telepath_basics(self):

        daemon,link = self.getFooServ()

        port = link[1].get('port')

        cli = ('tcp',{'host':'127.0.0.1','port':port,'telepath':'foo'})
        foo = s_telepath.Proxy(cli)

        s = time.time()
        for i in range(1000):
            foo.speed()
        e = time.time()

        # ensure perf is still good...
        self.assertTrue( (e - s) < 0.15 )

        self.assertEqual( foo.bar(10,20), 30 )
        self.assertRaises( s_telepath.TeleProtoError, foo.faz, 10, 20 )
        self.assertRaises( s_telepath.RemoteException, foo.baz, 10, 20 )

        foo.synFini()
        daemon.synFini()

    def test_telepath_auth_apikey(self):

        daemon,link = self.getFooServ()

        authmod = s_daemon.ApiKeyAuth(daemon)

        apikey = guid()

        authmod.addAuthAllow(apikey,'tele.call.foo.bar')
        daemon.setAuthModule(authmod)

        port = link[1].get('port')

        #cli = ('tcp',{'host':'127.0.0.1','port':port,'telepath':'foo','authinfo':authinfo})
        cli = ('tcp',{'host':'127.0.0.1','port':port,'telepath':'foo'})
        foo = s_telepath.Proxy(cli)

        self.assertRaises( s_telepath.TelePermDenied, foo.bar, 20, 30)

        foo.synFini()

        cli[1]['authinfo'] = {'apikey':apikey}

        foo = s_telepath.Proxy(cli)
        self.assertEqual( foo.bar(20,30), 50 )

        daemon.synFini()
        foo.synFini()

    '''
    def test_telepath_auth(self):

        data = {'allow':True}
        def callauth(event):
            sock = event[1].get('sock')
            mesg = event[1].get('mesg')
            return data.get('allow')

        serv,link = self.getFooServ()
        serv.synOn('tele:call:auth',callauth)

        foo = s_telepath.Proxy('foo',link)

        foo.bar(10,20)

        data['allow'] = False

        self.assertRaises( s_telepath.TeleProtoError, foo.bar, 10, 20)
    '''
