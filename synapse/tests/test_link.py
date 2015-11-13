import io
import time
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.lib.urlhelp as s_urlhelp

#from synapse.links.common import *
from synapse.tests.common import *

class LinkTest(unittest.TestCase):

    def test_link_invalid(self):
        link = ('tcp',{})
        self.assertRaises( PropNotFound, s_link.getLinkRelay, link )

    def test_link_chopurl(self):

        info = s_urlhelp.chopurl('foo://woot.com:99/foo/bar')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), 99)
        self.assertEqual(info.get('host'), 'woot.com')
        self.assertEqual(info.get('path'), '/foo/bar')

        info = s_urlhelp.chopurl('foo://visi:secret@woot.com')
        self.assertEqual(info.get('user'), 'visi')
        self.assertEqual(info.get('passwd'), 'secret')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), None)
        self.assertEqual(info.get('host'), 'woot.com')

        info = s_urlhelp.chopurl('foo://[2607:f8b0:4004:806::1014]:99/foo/bar?baz=faz&gronk=woot')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('port'), 99)
        self.assertEqual(info.get('host'), '2607:f8b0:4004:806::1014')
        self.assertEqual(info.get('path'), '/foo/bar')
        self.assertEqual(info.get('query').get('baz'), 'faz')
        self.assertEqual(info.get('query').get('gronk'), 'woot')

        info = s_urlhelp.chopurl('foo://2607:f8b0:4004:806::1014/foo/bar')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('host'), '2607:f8b0:4004:806::1014')
        self.assertEqual(info.get('port'), None)
        self.assertEqual(info.get('path'), '/foo/bar')
        self.assertEqual(info.get('query'), None)

        info = s_urlhelp.chopurl('foo://visi:c@t@woot.com')
        self.assertEqual( info.get('user'), 'visi')
        self.assertEqual( info.get('passwd'), 'c@t')
        self.assertEqual( info.get('host'), 'woot.com')

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

