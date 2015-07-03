import io
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *

class LinkTest(unittest.TestCase):

    def test_link_invalid(self):

        link = ('tcp',{})
        self.assertRaises( s_link.NoLinkProp, s_link.reqValidLink, link )

    def test_link_fromuri(self):
        uri = 'tcp://127.0.0.1:9999?rc4key=wootwoot&timeout=30'
        link = s_link.initLinkFromUri(uri)

        self.assertEqual(link[0],'tcp')
        self.assertEqual(link[1].get('timeout'),30)
        self.assertEqual(link[1].get('rc4key'),b'wootwoot')
        self.assertEqual(link[1].get('connect'),('127.0.0.1',9999))

    def test_link_tcp_client(self):

        data = {'count':0}
        def sockinit(event):
            data['count'] += 1

        mesgs = []
        def wootmesg(sock,mesg):
            mesgs.append(mesg)
            return tufo('woot',foo=mesg[1].get('id'))

        link = tufo('tcp',listen=('127.0.0.1',34343))

        daemon = s_daemon.Daemon()
        daemon.synOn('link:sock:init',sockinit)
        daemon.setMesgMethod('woot',wootmesg)

        daemon.runLink(link)

        link = tufo('tcp',connect=('127.0.0.1',34343),trans=True)
        client = s_link.LinkClient(link)

        reply = client.sendAndRecv('woot',id=1)
        self.assertEqual( reply[1].get('foo'), 1 )

        reply = client.sendAndRecv('woot',id=2)
        self.assertEqual( reply[1].get('foo'), 2 )

        self.assertEqual( data.get('count'), 3)

        client.synFini()
        daemon.synFini()
