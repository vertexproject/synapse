import io
import time
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon

from synapse.common import *
from synapse.links.common import *

class LinkTest(unittest.TestCase):

    def test_link_invalid(self):
        link = ('tcp',{})
        self.assertRaises( NoLinkProp, s_link.initLinkRelay, link )

    def test_link_chopurl(self):

        info = s_link.chopurl('foo://woot.com:99/foo/bar')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), 99)
        self.assertEqual(info.get('host'), 'woot.com')
        self.assertEqual(info.get('path'), '/foo/bar')

        info = s_link.chopurl('foo://visi:secret@woot.com')
        self.assertEqual(info.get('user'), 'visi')
        self.assertEqual(info.get('passwd'), 'secret')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), None)
        self.assertEqual(info.get('host'), 'woot.com')

        info = s_link.chopurl('foo://[2607:f8b0:4004:806::1014]:99/foo/bar?baz=faz&gronk=woot')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), 99)
        self.assertEqual(info.get('host'), '2607:f8b0:4004:806::1014')
        self.assertEqual(info.get('path'), '/foo/bar')
        self.assertEqual(info.get('query').get('baz'), 'faz')
        self.assertEqual(info.get('query').get('gronk'), 'woot')

        info = s_link.chopurl('foo://2607:f8b0:4004:806::1014/foo/bar')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('host'), '2607:f8b0:4004:806::1014')
        self.assertEqual(info.get('port'), None)
        self.assertEqual(info.get('path'), '/foo/bar')
        self.assertEqual(info.get('query'), None)

    def test_link_fromurl(self):
        url = 'tcp://visi:secret@127.0.0.1:9999/foo?rc4key=wootwoot&timeout=30'
        link = s_link.chopLinkUrl(url)

        self.assertEqual(link[0],'tcp')
        self.assertEqual(link[1].get('port'),9999)
        self.assertEqual(link[1].get('path'),'/foo')
        self.assertEqual(link[1].get('timeout'),30)
        self.assertEqual(link[1].get('host'),'127.0.0.1')
        self.assertEqual(link[1].get('rc4key'),b'wootwoot')

        self.assertEqual(link[1]['authinfo'].get('user'),'visi')
        self.assertEqual(link[1]['authinfo'].get('passwd'),'secret')

    def test_link_tcp_client(self):

        data = {'count':0}
        def sockinit(event):
            data['count'] += 1

        mesgs = []
        def wootmesg(sock,mesg):
            mesgs.append(mesg)
            return tufo('woot',foo=mesg[1].get('id'))

        link = s_link.chopLinkUrl('tcp://127.0.0.1:0/?zerosig=1')
        #link = tufo('tcp',host='127.0.0.1',port=0)

        daemon = s_daemon.Daemon()
        daemon.on('link:sock:init',sockinit)
        daemon.setMesgMethod('woot',wootmesg)

        daemon.runLinkServer(link)

        relay = s_link.initLinkRelay(link)

        link[1]['trans'] = True
        client = relay.initLinkClient()

        reply = client.sendAndRecv('woot',id=1)
        self.assertEqual( reply[1].get('foo'), 1 )

        reply = client.sendAndRecv('woot',id=2)
        self.assertEqual( reply[1].get('foo'), 2 )

        self.assertEqual( data.get('count'), 3)

        client.fini()
        daemon.fini()

    def test_link_client_retry(self):
        link = s_link.chopLinkUrl('tcp://127.0.0.1:0/?retry=2')

        daemon = s_daemon.Daemon()
        daemon.runLinkServer(link)

        relay = s_link.initLinkRelay(link)
        client = relay.initLinkClient()

        daemon.fini()

        self.assertRaises( s_link.RetryExceeded, client.sendAndRecv, 'woot' )

        client.fini()
