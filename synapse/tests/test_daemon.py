import io
import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.tests.common import *

class DaemonTest(unittest.TestCase):

    def test_daemon_extend(self):

        def onwoot(mesg):
            return tufo('hehe',foo='bar')

        daemon = s_daemon.Daemon()
        daemon.rtor.act('woot',onwoot)

        link = daemon.listen('tcp://127.0.0.1:0')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.assertIsNotNone(sock)

        sock.sendobj( ('woot',{}) )
        mesg = sock.recvobj()
        resp = mesg[1].get('ret')

        self.assertEqual( resp[0], 'hehe')
        self.assertEqual( resp[1].get('foo'), 'bar' )

        sock.fini()
        daemon.fini()

    def test_daemon_timeout(self):

        daemon = s_daemon.Daemon()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.assertEqual( sock.recvobj(),None)

        sock.fini()
        daemon.fini()
