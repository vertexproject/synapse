import unittest

import synapse.link as s_link
import synapse.crypto as s_crypto
import synapse.socket as s_socket

class CryptoTest(unittest.TestCase):

    def test_crypto_rc4(self):

        data = {}
        def sockmesg(sock,mesg):
            data['mesg'] = mesg
            sock.sendSockMesg(('woot',2))

        link = ('tcp',{'host':'127.0.0.1','port':0,'rc4key':b'asdfasdf'})

        serv = s_link.LinkServer(link)
        serv.synOn('sockmesg',sockmesg)
        addr = serv.runLinkServer()

        link[1]['port'] = addr[1]

        clin = s_link.LinkClient(link)
        reply = clin.txrxLinkMesg( ('woot',1) )

        self.assertEqual( reply, ('woot',2) )
        self.assertEqual( data.get('mesg'), ('woot',1) )

        serv.synFireFini()
        clin.synFireFini()
