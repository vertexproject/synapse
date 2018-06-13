import logging
import threading

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.telepath as s_telepath

import synapse.tests.common as s_test

class Boom:
    pass

class Foo:

    def __init__(self):
        self.genrwait = threading.Event()
        self.retnwait = threading.Event()
        self.genrexited = False

    def iAmLoop(self):
        return s_glob.plex.iAmLoop()

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise ValueError('derp')

    def echo(self, x):
        return x

    def speed(self):
        return

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

    def boom(self):
        return Boom()

    def genrexit(self):

        try:

            yield 1000
            self.genrwait.wait(timeout=2)
            yield 2000
            yield 3000

        except GeneratorExit as e:
            self.genrexited = True

        finally:
            self.retnwait.set()

class TeleApi:

    def __init__(self, item, link):
        self.item = item
        self.link = link

    def getFooBar(self, x, y):
        return x - y

class TeleAware(s_telepath.Aware):

    def getTeleApi(self, link, mesg):
        return TeleApi(self, link)

class TeleAuth(s_telepath.Aware):

    def getTeleApi(self, link, mesg):

        auth = mesg[1].get('auth')
        if auth is None:
            raise s_exc.AuthDeny()

        user, info = auth

        passwd = info.get('passwd')
        if passwd != 'secretsauce':
            raise s_exc.AuthDeny()

        return self

    def getFooBar(self, x, y):
        return x + y

class TeleTest(s_test.SynTest):

    def test_telepath_basics(self):

        foo = Foo()

        with self.getTestDmon() as dmon:

            addr = dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            self.raises(s_exc.BadUrl, s_telepath.openurl, 'noscheme/foo')

            print('a')

            # called via synchelp...
            prox = s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1])

            self.false(prox.iAmLoop())
            print('a')

            # check a standard return value
            self.eq(30, prox.bar(10, 20))
            print('a')

            # check a coroutine return value
            self.eq(25, prox.corovalu(10, 5))
            print('a')

            # check a generator return channel
            genr = prox.genr()
            self.true(isinstance(genr, s_telepath.Genr))
            self.eq((10, 20, 30), tuple(genr))

            # check an async generator return channel
            genr = prox.corogenr(3)
            self.true(isinstance(genr, s_telepath.Genr))
            self.eq((0, 1, 2), tuple(genr))

            self.raises(s_exc.NoSuchMeth, prox.raze)

            self.raises(s_exc.NoSuchMeth, prox.fake)

            self.raises(s_exc.SynErr, prox.boom)

    def test_telepath_aware(self):

        item = TeleAware()

        with self.getTestDmon() as dmon:
            dmon.share('woke', item)
            proxy = dmon._getTestProxy('woke')
            self.eq(10, proxy.getFooBar(20, 10))

    def test_telepath_auth(self):

        item = TeleAuth()
        with self.getTestDmon() as dmon:
            dmon.share('auth', item)
            host, port = dmon.addr

            url = 'tcp://localhost/auth'
            self.raises(s_exc.AuthDeny, s_telepath.openurl, url, port=port)

            url = 'tcp://visi@localhost/auth'
            self.raises(s_exc.AuthDeny, s_telepath.openurl, url, port=port)

            url = 'tcp://visi:secretsauce@localhost/auth'
            with s_telepath.openurl(url, port=port) as proxy:
                self.eq(17, proxy.getFooBar(10, 7))

    def test_telepath_server_badvers(self):

        with self.getTestDmon() as dmon:

            dmon.televers = (0, 0)

            host, port = dmon.listen('tcp://127.0.0.1:0/')

            self.raises(s_exc.BadMesgVers, s_telepath.openurl, 'tcp://127.0.0.1/', port=port)
