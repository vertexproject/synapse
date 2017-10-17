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

    bigdata = os.urandom(1000 * 1000 * 50)

    def foo(self):
        return 'bar'

    def big(self):
        return FooBar.bigdata

class LinkTest(SynTest):

    def test_link_invalid(self):
        link = ('tcp', {})
        self.raises(PropNotFound, s_link.getLinkRelay, link)

    def test_link_chopurl(self):

        info = s_urlhelp.chopurl('foo://woot.com:99/foo/bar')
        self.eq(info.get('scheme'), 'foo')
        self.eq(info.get('port'), 99)
        self.eq(info.get('host'), 'woot.com')
        self.eq(info.get('path'), '/foo/bar')

        info = s_urlhelp.chopurl('foo://visi:secret@woot.com')
        self.eq(info.get('user'), 'visi')
        self.eq(info.get('passwd'), 'secret')
        self.eq(info.get('scheme'), 'foo')
        self.eq(info.get('port'), None)
        self.eq(info.get('host'), 'woot.com')

        info = s_urlhelp.chopurl('foo://[2607:f8b0:4004:806::1014]:99/foo/bar?baz=faz&gronk=woot')
        self.eq(info.get('scheme'), 'foo')
        self.eq(info.get('port'), 99)
        self.eq(info.get('host'), '2607:f8b0:4004:806::1014')
        self.eq(info.get('path'), '/foo/bar')
        self.eq(info.get('query').get('baz'), 'faz')
        self.eq(info.get('query').get('gronk'), 'woot')

        info = s_urlhelp.chopurl('foo://2607:f8b0:4004:806::1014/foo/bar')
        self.eq(info.get('scheme'), 'foo')
        self.eq(info.get('host'), '2607:f8b0:4004:806::1014')
        self.eq(info.get('port'), None)
        self.eq(info.get('path'), '/foo/bar')
        self.eq(info.get('query'), None)

        info = s_urlhelp.chopurl('foo://visi:c@t@woot.com')
        self.eq(info.get('user'), 'visi')
        self.eq(info.get('passwd'), 'c@t')
        self.eq(info.get('host'), 'woot.com')

        info = s_urlhelp.chopurl('foo:///bar')
        self.eq(info.get('scheme'), 'foo')
        self.eq(info.get('path'), '/bar')

    def test_link_fromurl(self):
        url = 'tcp://visi:secret@127.0.0.1:9999/foo?rc4key=wootwoot&retry=20'
        link = s_link.chopLinkUrl(url)

        self.eq(link[0], 'tcp')
        self.eq(link[1].get('port'), 9999)
        self.eq(link[1].get('path'), '/foo')
        self.eq(link[1].get('retry'), 20)
        self.eq(link[1].get('host'), '127.0.0.1')
        self.eq(link[1].get('rc4key'), b'wootwoot')

        self.eq(link[1].get('user'), 'visi')
        self.eq(link[1].get('passwd'), 'secret')

    def test_link_ssl_big(self):

        # FIXME some kind of cert validation diffs in *py* vers killed us
        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        with s_daemon.Daemon() as dmon:

            dmon.share('foobar', FooBar())
            link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)
            port = link[1].get('port')
            url = 'ssl://localhost/foobar'

            with s_telepath.openurl(url, port=port, cafile=cafile) as foo:
                # FIXME ssl.SSLWantWriteError should not be raised here
                x = foo.big()

    def test_link_ssl_basic(self):

        # FIXME some kind of cert validation diffs in *py* vers killed us
        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        with s_daemon.Daemon() as dmon:

            dmon.share('foobar', FooBar())

            link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)

            port = link[1].get('port')

            url = 'ssl://localhost/foobar'

            with s_telepath.openurl(url, port=port, cafile=cafile) as foo:
                self.eq(foo.foo(), 'bar')

    def test_link_ssl_auth(self):

        # FIXME some kind of cert validation diffs in *py* vers killed us
        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        userkey = getTestPath('user.key')
        usercert = getTestPath('user.crt')

        with s_daemon.Daemon() as dmon:

            dmon.share('foobar', FooBar())

            link = dmon.listen('ssl://localhost:0/', cafile=cafile, keyfile=keyfile, certfile=certfile)

            port = link[1].get('port')

            url = 'ssl://localhost/foobar'

            with s_telepath.openurl(url, port=port, cafile=cafile, keyfile=userkey, certfile=usercert) as foo:
                self.eq(foo.foo(), 'bar')

    def test_link_ssl_nocheck(self):

        cafile = getTestPath('ca.crt')
        keyfile = getTestPath('server.key')
        certfile = getTestPath('server.crt')

        with s_daemon.Daemon() as dmon:

            dmon.share('foobar', FooBar())

            link = dmon.listen('ssl://localhost:0/', keyfile=keyfile, certfile=certfile)

            port = link[1].get('port')

            url = 'ssl://localhost/foobar'
            self.raises(LinkErr, s_telepath.openurl, url, port=port)

            with s_telepath.openurl(url, port=port, nocheck=True) as foo:
                pass

    def test_link_ssl_nofile(self):
        url = 'ssl://localhost:33333/foobar?cafile=/newpnewpnewp'
        self.raises(NoSuchFile, s_telepath.openurl, url)

        url = 'ssl://localhost:33333/foobar?keyfile=/newpnewpnewp'
        self.raises(NoSuchFile, s_telepath.openurl, url)

        url = 'ssl://localhost:33333/foobar?certfile=/newpnewpnewp'
        self.raises(NoSuchFile, s_telepath.openurl, url)

    def test_link_pool(self):
        link = s_link.chopLinkUrl('foo://visi:c@t@woot.com?poolsize=7&poolmax=-1')
        self.eq(link[1].get('poolsize'), 7)
        self.eq(link[1].get('poolmax'), -1)

    def test_link_local(self):
        self.thisHostMustNot(platform='windows')
        name = guid()

        dmon = s_daemon.Daemon()
        dmon.share('foo', FooBar())

        link = dmon.listen('local://%s' % (name,))

        prox = s_telepath.openurl('local://%s/foo' % name)

        self.eq(prox.foo(), 'bar')

        prox.fini()
        dmon.fini()

    def test_link_refused(self):
        self.raises(LinkRefused, s_telepath.openurl, 'tcp://127.0.0.1:1/foo')
        self.raises(LinkRefused, s_telepath.openurl, 'ssl://127.0.0.1:1/foo')
        if s_thishost.get('platform') != 'windows':
            self.raises(LinkRefused, s_telepath.openurl, 'local://newpnewpnewp/foo')
