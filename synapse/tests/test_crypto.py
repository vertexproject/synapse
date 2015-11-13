import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.tests.common import *

class CryptoTest(SynTest):

    def test_crypto_rc4(self):

        data = {}
        def wootmesg(mesg):
            data['foo'] = mesg[1].get('foo')
            return tufo('woot2')

        daemon = s_daemon.Daemon()
        daemon.rtor.act('woot1', wootmesg)

        link = daemon.listen('tcp://127.0.0.1:0?rc4key=asdfasdf')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        sock.fireobj('woot1',foo=2)
        repl = sock.recvobj()

        self.assertEqual( repl[0], 'woot1:ret' )
        self.assertEqual( data.get('foo'), 2)

        sock.fini()
        daemon.fini()
