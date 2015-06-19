import unittest

import synapse.link as s_link
import synapse.daemon as s_daemon

class CryptoTest(unittest.TestCase):

    def test_crypto_rc4(self):

        link = ('tcpd',{'host':'127.0.0.1','port':0,'rc4key':b'asdfasdf'})

        data = {}
        def wootmesg(sock,mesg):
            data['foo'] = mesg[1].get('foo')
            return ('woot2',{})

        daemon = s_daemon.Daemon()
        daemon.setMesgMethod('woot1',wootmesg)

        daemon.runLink(link)

        port = link[1].get('port')

        link2 = ('tcp',{'host':'127.0.0.1','port':port,'rc4key':b'asdfasdf'})


        client = s_link.LinkClient(link)
        repl = client.sendAndRecv('woot1',foo=2)

        self.assertEqual( repl[0], 'woot2' )
        self.assertEqual( data.get('foo'), 2)

        daemon.synFini()
        client.synFini()
