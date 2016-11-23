import io
import ssl
import time
import unittest
import threading

import synapse.link as s_link
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.thishost as s_thishost

from synapse.tests.common import *

class FooBar:

    def foo(self):

        return 'bar'

class LinkTest(SynTest):

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

        info = s_urlhelp.chopurl('foo:///bar')
        self.assertEqual(info.get('scheme'), 'foo')
        self.assertEqual(info.get('path'), '/bar')

    def test_link_fromurl(self):
        url = 'tcp://visi:secret@127.0.0.1:9999/foo?rc4key=wootwoot&retry=20'
        link = s_link.chopLinkUrl(url)

        self.assertEqual(link[0],'tcp')
        self.assertEqual(link[1].get('port'),9999)
        self.assertEqual(link[1].get('path'),'/foo')
        self.assertEqual(link[1].get('retry'),20)
        self.assertEqual(link[1].get('host'),'127.0.0.1')
        self.assertEqual(link[1].get('rc4key'),b'wootwoot')

        self.assertEqual(link[1].get('user'),'visi')
        self.assertEqual(link[1].get('passwd'),'secret')

    def newp_link_ssl_basic(self):

        # FIXME some kind of cert validation diffs in *py* vers killed us
        cafile = getTestPath('ca.pem')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.pem')

        dmon = s_daemon.Daemon()
        dmon.share('foobar', FooBar() )

        link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)

        port = link[1].get('port')

        url = 'ssl://localhost/foobar'
        foo = s_telepath.openurl(url, port=port, cafile=cafile)

        self.assertEqual( foo.foo(), 'bar' )

        foo.fini()
        dmon.fini()

    def test_link_ssl_nocheck(self):

        cafile = getTestPath('ca.pem')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.pem')

        dmon = s_daemon.Daemon()
        dmon.share('foobar', FooBar() )

        link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)

        port = link[1].get('port')

        url = 'ssl://localhost/foobar'
        self.assertRaises( LinkErr, s_telepath.openurl, url, port=port )

        foo = s_telepath.openurl(url, port=port, nocheck=True)

        foo.fini()
        dmon.fini()

    def test_link_ssl_nofile(self):
        url = 'ssl://localhost:33333/foobar?cafile=/newpnewpnewp'
        self.assertRaises( NoSuchFile, s_telepath.openurl, url )

        url = 'ssl://localhost:33333/foobar?keyfile=/newpnewpnewp'
        self.assertRaises( NoSuchFile, s_telepath.openurl, url )

        url = 'ssl://localhost:33333/foobar?certfile=/newpnewpnewp'
        self.assertRaises( NoSuchFile, s_telepath.openurl, url )

    def test_link_pool(self):
        link = s_link.chopLinkUrl('foo://visi:c@t@woot.com?poolsize=7&poolmax=-1')
        self.assertEqual( link[1].get('poolsize'), 7 )
        self.assertEqual( link[1].get('poolmax'), -1 )

    def test_link_local(self):
        self.thisHostMustNot(platform='windows')
        name = guid()

        dmon = s_daemon.Daemon()
        dmon.share('foo',FooBar())

        link = dmon.listen('local://%s' % (name,))

        prox = s_telepath.openurl('local://%s/foo' % name)

        self.assertEqual( prox.foo(), 'bar' )

        prox.fini()
        dmon.fini()

    def test_link_refused(self):
        self.assertRaises(LinkRefused, s_telepath.openurl, 'tcp://127.0.0.1:1/foo')
        self.assertRaises(LinkRefused, s_telepath.openurl, 'ssl://127.0.0.1:1/foo')
        if s_thishost.get('platform') != 'windows':
            self.assertRaises(LinkRefused, s_telepath.openurl, 'local://newpnewpnewp/foo')
