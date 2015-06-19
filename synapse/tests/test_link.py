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

        link = ('tcp',{'host':'_','port':80})
        self.assertRaises( s_link.BadLinkProp, s_link.reqValidLink, link )

    def test_link_tcp_client(self):

        data = {'count':0}
        def sockinit(event):
            data['count'] += 1

        mesgs = []
        def wootmesg(sock,mesg):
            mesgs.append(mesg)
            return tufo('woot',foo=mesg[1].get('id'))

        link = ('tcpd',{'host':'127.0.0.1','port':0})

        daemon = s_daemon.Daemon()
        daemon.synOn('sockinit',sockinit)
        daemon.setMesgMethod('woot',wootmesg)

        daemon.runLink(link)

        port = link[1].get('port')

        link = ('tcp',{'host':'127.0.0.1','port':port,'trans':True})
        client = s_link.LinkClient(link)

        reply = client.sendAndRecv('woot',id=1)
        self.assertEqual( reply[1].get('foo'), 1 )

        reply = client.sendAndRecv('woot',id=2)
        self.assertEqual( reply[1].get('foo'), 2 )

        self.assertEqual( data.get('count'), 3)

        daemon.synFini()
        client.synFini()

    def test_link_fromuri_tcp(self):
        link = s_link.initLinkFromUri('tcp://1.2.3.4:99')
        self.assertEqual( link[1].get('host'), '1.2.3.4' )
        self.assertEqual( link[1].get('port'), 99 )

    def test_link_fromuri_params(self):
        link = s_link.initLinkFromUri('tcp://1.2.3.4:99?gronk=wootwoot')
        self.assertEqual( link[1].get('host'), '1.2.3.4' )
        self.assertEqual( link[1].get('port'), 99 )
        self.assertEqual( link[1].get('gronk'), 'wootwoot' )
