import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.telepath as s_telepath

import synapse.lib.share as s_share
import synapse.tests.common as s_test

from synapse.tests.utils import SyncToAsyncCMgr

class Boom:
    pass

class CustomShare(s_share.Share):
    typename = 'customshare'

    async def _runShareLoop(self):
        await asyncio.sleep(10)

    def boo(self, x):
        return x

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

    async def longasync(self):
        await s_glob.plex.sleep(5)
        return 42

    async def corogenr(self, x):
        for i in range(x):
            yield i
            await s_glob.plex.sleep(0.1)

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

    def customshare(self):
        return CustomShare(self.link, 42)

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
        evt = threading.Event()

        with self.getTestDmon() as dmon:

            addr = dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            self.raises(s_exc.BadUrl, s_telepath.openurl, 'noscheme/foo')

            # called via synchelp...
            prox = s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1])
            # Add an additional prox.fini handler.
            prox.onfini(evt.set)

            self.false(prox.iAmLoop())

            # check a standard return value
            self.eq(30, prox.bar(10, 20))

            # check a coroutine return value
            self.eq(25, prox.corovalu(10, 5))

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

        # Fini'ing a daemon fini's proxies connected to it.
        self.true(evt.wait(2))
        self.true(prox.isfini)

    @s_glob.synchelp
    async def test_telepath_async(self):
        foo = Foo()

        async with SyncToAsyncCMgr(self.getTestDmon) as dmon:
            addr = await s_glob.plex.executor(dmon.listen, 'tcp://127.0.0.1:0')
            dmon.share('foo', foo)
            prox = await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1])
            genr = prox.corogenr(3)
            self.eq([0, 1, 2], [x async for x in await genr])
            # To act the same as a local object, would be:
            # self.eq([0, 1, 2], [x async for x in genr])

            aitr = (await prox.corogenr(3)).__aiter__()
            await aitr.__anext__()

            start_event = asyncio.Event(loop=s_glob.plex.loop)

            async def longwaiter():
                coro = prox.longasync()
                await start_event.wait()
                await coro

            fut = s_glob.plex.loop.create_task(longwaiter())

        await self.asyncraises(StopAsyncIteration, aitr.__anext__())
        start_event.set()

        # Test that a coroutine about to await on an async proxy method doesn't become "stuck" by awaiting on a
        # just-fini'd object method

        # Give the longwaiter a chance to run
        await s_glob.plex.sleep(.1)

        await self.asyncraises(s_exc.IsFini, asyncio.wait_for(fut, timeout=2, loop=s_glob.plex.loop))

    def test_telepath_aware(self):

        item = TeleAware()

        with self.getTestDmon() as dmon:
            dmon.share('woke', item)
            proxy = dmon._getTestProxy('woke')
            self.eq(10, proxy.getFooBar(20, 10))

            # check a custom share works
            obj = proxy.customshare()
            self.eq(999, obj.boo(999))

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
