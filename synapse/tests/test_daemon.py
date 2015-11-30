import io
import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.tests.common import *

class DaemonTest(unittest.TestCase):

    def test_daemon_timeout(self):

        daemon = s_daemon.Daemon()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.assertEqual( sock.recvobj(),None)

        sock.fini()
        daemon.fini()
