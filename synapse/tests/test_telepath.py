import time
import unittest

import synapse.telepath as s_telepath

class Foo:

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise Exception('derp')

    def speed(self):
        return


class TelePathTest(unittest.TestCase):

    def getFooServ(self):
        link = ('tcp',{'host':'127.0.0.1','port':0})

        serv = s_telepath.Server(link)
        serv.addSharedObject('foo',Foo())
        sockaddr = serv.runLinkServer()

        link[1]['port'] = sockaddr[1]

        return serv,link

    def test_telepath_basics(self):

        serv,link = self.getFooServ()

        foo = s_telepath.Proxy('foo',link)

        s = time.time()
        for i in range(1000):
            foo.speed()
        e = time.time()

        # ensure perf is at *least* 5k/sec base case
        self.assertTrue( (e - s) < 0.2 )

        self.assertEqual( foo.bar(10,20), 30 )
        self.assertRaises( s_telepath.TeleProtoError, foo.faz, 10, 20 )
        self.assertRaises( s_telepath.RemoteException, foo.baz, 10, 20 )

        serv.synFireFini()
        foo.synFireFini()

    def test_telepath_auth(self):

        data = {'allow':True}
        def callauth(sock,mesg):
            return data.get('allow')

        serv,link = self.getFooServ()
        serv.synOn('tele:call:auth',callauth)

        foo = s_telepath.Proxy('foo',link)

        foo.bar(10,20)

        data['allow'] = False

        self.assertRaises( s_telepath.TeleProtoError, foo.bar, 10, 20)
