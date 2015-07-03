import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *

class CryptoTest(unittest.TestCase):

    def test_crypto_rc4(self):

        link1 = tufo('tcp',listen=('127.0.0.1',34343),rc4key=b'asdfasdf')
        link2 = tufo('tcp',connect=('127.0.0.1',34343),rc4key=b'asdfasdf')

        data = {}
        def wootmesg(sock,mesg):
            data['foo'] = mesg[1].get('foo')
            return ('woot2',{})

        daemon = s_daemon.Daemon()
        daemon.setMesgMethod('woot1',wootmesg)

        daemon.runLink(link1)

        client = s_link.LinkClient(link2)
        repl = client.sendAndRecv('woot1',foo=2)

        self.assertEqual( repl[0], 'woot2' )
        self.assertEqual( data.get('foo'), 2)

        client.synFini()
        daemon.synFini()
