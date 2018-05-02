import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.link as s_link

import synapse.tests.common as s_test

class Foo:

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise ValueError('derp')

    def echo(self, x):
        return x

    def speed(self):
        return

    def echo(self, x):
        return x

    def genr(self):
        yield 10
        yield 20
        yield 30

    def raze(self):
        # test that SynErr makes it through
        raise s_exc.NoSuchMeth(name='haha')

    async def corovalu(self, x, y):
        return x * 2 + y

    async def corogenr(self, x):
        for i in range(x):
            yield i


class TeleTest(s_test.SynTest):

    def test_telepath_basics(self):

        foo = Foo()

        with self.getTestDmon() as dmon:

            addr = dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            # called via synchelp...
            prox = s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1])

            # check a standard return value
            self.eq(30, prox.bar(10, 20))

            # check a coroutine return value
            self.eq(25, prox.corovalu(10, 5))

            # check a generator return channel
            genr = prox.genr()
            self.true(isinstance(genr, s_link.Chan))
            self.eq((10, 20, 30), tuple(genr))

            # check an async generator return channel
            genr = prox.corogenr(3)
            self.true(isinstance(genr, s_link.Chan))
            self.eq((0, 1, 2), tuple(genr))

            self.raises(s_exc.NoSuchMeth, prox.raze)

            self.raises(s_exc.NoSuchMeth, prox.fake)

    def test_telepath_server_badvers(self):

        with self.getTestDmon() as dmon:

            dmon.televers = (0, 0)

            host, port = dmon.listen('tcp://127.0.0.1:0/')

            self.raises(s_exc.BadMesgVers, s_telepath.openurl, 'tcp://127.0.0.1/', port=port)
