import unittest

import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

from synapse.tests.common import *

class Foo:
    def bar(self):
        return 'baz'

class CryptoTest(SynTest):

    def test_crypto_rc4(self):

        dmon = s_daemon.Daemon()
        dmon.share('foo',Foo())

        link = dmon.listen('tcp://127.0.0.1:0/foo?rc4key=asdfasdf')
        prox = s_telepath.openlink(link)

        self.assertEqual( prox.bar(), 'baz' )

        prox.fini()
        dmon.fini()

    def test_crypto_zerosig(self):

        dmon = s_daemon.Daemon()
        dmon.share('foo',Foo())

        link = dmon.listen('tcp://127.0.0.1:0/foo?zerosig=1')
        prox = s_telepath.openlink(link)

        self.assertEqual( prox.bar(), 'baz' )

        prox.fini()
        dmon.fini()
