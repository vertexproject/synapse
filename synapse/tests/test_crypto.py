import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *

class CryptoTest(unittest.TestCase):

    def test_crypto_rc4(self):

        link1 = s_link.chopLinkUrl('tcp://127.0.0.1:0?rc4key=asdfasdf')

        data = {}
        def wootmesg(sock,mesg):
            data['foo'] = mesg[1].get('foo')
            return ('woot2',{})

        daemon = s_daemon.Daemon()
        daemon.setMesgMethod('woot1',wootmesg)

        daemon.runLinkServer(link1)

        relay = s_link.initLinkRelay(link1)
        client = relay.initLinkClient()

        repl = client.sendAndRecv('woot1',foo=2)

        self.assertEqual( repl[0], 'woot2' )
        self.assertEqual( data.get('foo'), 2)

        client.fini()
        daemon.fini()
