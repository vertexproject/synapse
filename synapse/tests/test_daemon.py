import io
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

from synapse.tests.common import *

class Woot:
    def foo(self,x,y=20):
        return x + y

class Blah:
    def __init__(self, woot):
        self.woot = woot

class DaemonTest(unittest.TestCase):

    def test_daemon_timeout(self):

        daemon = s_daemon.Daemon()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.assertEqual( sock.recvobj(),None)

        sock.fini()
        daemon.fini()

    def test_daemon_on(self):

        class Foo:
            def bar(self):
                return 'baz'

        dmon = s_daemon.Daemon()
        link = dmon.listen('tcp://127.0.0.1:0/')

        bus = s_eventbus.EventBus()
        foo = Foo()

        dmon.share('bus', bus)
        dmon.share('foo', foo)

        port = link[1].get('port')

        bprox = s_telepath.openurl('tcp://127.0.0.1/bus', port=port)
        fprox = s_telepath.openurl('tcp://127.0.0.1/foo', port=port)

        evt = threading.Event()
        def woot(mesg):
            evt.set()

        bprox.on('woot', woot)
        fprox.on('woot', woot)

        bus.fire('woot')

        evt.wait(timeout=2)

        fprox.off('woot', woot)

        self.assertTrue( evt.is_set() )

    def test_daemon_conf(self):

        class DmonConfTest(s_daemon.DmonConf,s_eventbus.EventBus):

            def __init__(self):
                s_daemon.DmonConf.__init__(self)
                s_eventbus.EventBus.__init__(self)

        conf = {

            'ctors':(
                ('woot','ctor://synapse.tests.test_daemon.Woot()'),
                ('blah','ctor://synapse.tests.test_daemon.Blah(woot)'),
            ),

            'addons':(
                ('haha','ctor://synapse.tests.test_daemon.Woot()'),
            ),

        }

        dcon = DmonConfTest()
        dcon.loadDmonConf(conf)

        self.assertEqual( dcon.locs.get('woot').foo(10,y=30), 40 )
        self.assertEqual( dcon.addons.get('haha').foo(10,y=30), 40 )

        self.assertEqual( dcon.locs.get('blah').woot.foo(10,y=30), 40 )
