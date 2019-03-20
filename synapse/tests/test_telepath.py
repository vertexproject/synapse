import os
import ssl
import socket
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.share as s_share

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class Boom:
    pass

class CustomShare(s_share.Share):
    typename = 'customshare'

    async def _runShareLoop(self):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    def boo(self, x):
        return x

    async def custgenr(self, n):
        for i in range(n):
            yield i

class Beep:
    def __init__(self, path):
        self.path = path

    def beep(self):
        return f'{self.path}: beep'

class Foo:

    def __init__(self):
        self.genrwait = threading.Event()
        self.retnwait = threading.Event()
        self.genrexited = False

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

    def genrboom(self):
        yield 10
        yield 20
        raise s_exc.SynErr(mesg='derp')

    def raze(self):
        # test that SynErr makes it through
        raise s_exc.NoSuchMeth(name='haha')

    async def corovalu(self, x, y):
        return x * 2 + y

    async def longasync(self):
        await asyncio.sleep(5)
        return 42

    async def corogenr(self, x):
        for i in range(x):
            yield i
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                return

    def boom(self):
        return Boom()

    def genrexit(self):

        try:

            yield 1000
            self.genrwait.wait(timeout=2)
            yield 2000
            yield 3000

        except GeneratorExit:
            self.genrexited = True

        finally:
            self.retnwait.set()

class TeleApi:

    def __init__(self, item, link):
        self.item = item
        self.link = link

    def getFooBar(self, x, y):
        return x - y

    async def customshare(self):
        return await CustomShare.anit(self.link, 42)

class TeleAware(s_telepath.Aware):
    def __init__(self):
        s_telepath.Aware.__init__(self)
        self.beeps = {}

    def _initBeep(self, path):
        beep = self.beeps.get(path)
        if beep:
            return beep
        beep = Beep(path)
        self.beeps[path] = beep
        return beep

    def getTeleApi(self, link, mesg, path):
        if not path:
            return TeleApi(self, link)

        return self._initBeep(path[0])

class TeleAuth(s_telepath.Aware):

    def getTeleApi(self, link, mesg, path):

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

class TeleTest(s_t_utils.SynTest):

    async def test_telepath_basics(self):

        foo = Foo()
        evt = asyncio.Event()

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            await self.asyncraises(s_exc.BadUrl, s_telepath.openurl('noscheme/foo'))

            prox = await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1])

            # Add an additional prox.fini handler.
            prox.onfini(evt.set)

            # check a standard return value
            self.eq(30, await prox.bar(10, 20))

            # check a coroutine return value
            self.eq(25, await prox.corovalu(10, 5))

            # check a generator return channel
            genr = await prox.genr()
            self.true(isinstance(genr, s_coro.GenrHelp))
            self.eq((10, 20, 30), await genr.list())

            # check generator explodes channel
            genr = await prox.genrboom()
            await self.asyncraises(s_exc.SynErr, genr.list())

            # check an async generator return channel
            genr = prox.corogenr(3)
            self.true(isinstance(genr, s_telepath.GenrIter))
            self.eq((0, 1, 2), await alist(genr))

            await self.asyncraises(s_exc.NoSuchMeth, prox.raze())

            await self.asyncraises(s_exc.NoSuchMeth, prox.fake())

            await self.asyncraises(s_exc.SynErr, prox.boom())

        # Fini'ing a daemon fini's proxies connected to it.
        self.true(await s_coro.event_wait(evt, 2))
        self.true(prox.isfini)
        await self.asyncraises(s_exc.IsFini, prox.bar((10, 20)))

    async def test_telepath_sync_genr(self):

        foo = Foo()

        def sync():
            return [x for x in prox.genr()]

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1]) as prox:
                self.eq((10, 20, 30), await s_coro.executor(sync))

    async def test_telepath_no_sess(self):

        foo = Foo()
        evt = asyncio.Event()

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            await self.asyncraises(s_exc.BadUrl, s_telepath.openurl('noscheme/foo'))

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1]) as prox:

                prox.sess = None

                # Add an additional prox.fini handler.
                prox.onfini(evt.set)

                # check a standard return value
                self.eq(30, await prox.bar(10, 20))

                # check a coroutine return value
                self.eq(25, await prox.corovalu(10, 5))

                # check a generator return channel
                genr = await prox.genr()
                self.eq((10, 20, 30), await alist(genr))

                # check an async generator return channel
                genr = prox.corogenr(3)
                self.eq((0, 1, 2), await alist(genr))

                await self.asyncraises(s_exc.NoSuchMeth, prox.raze())

                await self.asyncraises(s_exc.NoSuchMeth, prox.fake())

                await self.asyncraises(s_exc.SynErr, prox.boom())

            # Fini'ing a daemon fini's proxies connected to it.
            self.true(await s_coro.event_wait(evt, 2))
            self.true(prox.isfini)
            await self.asyncraises(s_exc.IsFini, prox.bar((10, 20)))

    async def test_telepath_tls_bad_cert(self):
        self.thisHostMustNot(platform='darwin')

        foo = Foo()

        async with self.getTestDmon() as dmon:
            # As a workaround to a Python bug (https://bugs.python.org/issue30945) that prevents localhost:0 from
            # being connected via TLS, make a certificate for whatever my hostname is and sign it with the test CA
            # key.
            hostname = socket.gethostname()
            dmon.certdir.genHostCert(socket.gethostname())

            addr = await dmon.listen(f'ssl://{hostname}:0')
            dmon.share('foo', foo)

            # host cert is *NOT* signed by a CA that client recognizes
            await self.asyncraises(ssl.SSLCertVerificationError,
                                   s_telepath.openurl(f'ssl://{hostname}/foo', port=addr[1]))

    async def test_telepath_tls(self):
        self.thisHostMustNot(platform='darwin')

        foo = Foo()

        async with self.getTestDmon() as dmon:
            # As a workaround to a Python bug (https://bugs.python.org/issue30945) that prevents localhost:0 from
            # being connected via TLS, make a certificate for whatever my hostname is and sign it with the test CA
            # key.
            hostname = socket.gethostname()

            dmon.certdir.genHostCert(hostname, signas='ca')

            addr = await dmon.listen(f'ssl://{hostname}:0')

            dmon.share('foo', foo)

            async with await s_telepath.openurl(f'ssl://{hostname}/foo', port=addr[1]) as prox:
                self.eq(30, await prox.bar(10, 20))

    async def test_telepath_surrogate(self):

        foo = Foo()
        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1]) as prox:
                bads = '\u01cb\ufffd\ud842\ufffd\u0012'
                t0 = ('1234', {'key': bads})

                # Shovel a malformed UTF8 string with an unpaired surrogate over telepath
                ret = await prox.echo(t0)
                self.eq(ret, t0)

    async def test_telepath_async(self):

        foo = Foo()

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=addr[1]) as prox:

                genr = prox.corogenr(3)
                self.eq([0, 1, 2], [x async for x in genr])
                # To act the same as a local object, would be:
                # self.eq([0, 1, 2], [x async for x in genr])

                aitr = prox.corogenr('fred').__aiter__()
                await self.asyncraises(s_exc.SynErr, aitr.__anext__())

                aitr = prox.corogenr(3).__aiter__()
                await aitr.__anext__()

                start_event = asyncio.Event()

                async def longwaiter():
                    coro = prox.longasync()
                    await start_event.wait()
                    await coro

                task = dmon.schedCoro(longwaiter())

            await self.asyncraises(StopAsyncIteration, aitr.__anext__())
            start_event.set()

            # Test that a coroutine about to await on an async proxy method doesn't become "stuck" by awaiting on a
            # just-fini'd object method

            # Give the longwaiter a chance to run
            await asyncio.sleep(.1)

            await self.asyncraises(s_exc.IsFini, asyncio.wait_for(task, timeout=2))

    async def test_telepath_blocking(self):
        ''' Make sure that async methods on the same proxy don't block each other '''

        class MyClass():
            typename = 'myshare'

            def __init__(self):
                self.evnt = asyncio.Event()
                self.sema = asyncio.Semaphore(value=0)

            async def do_it(self):
                self.sema.release()
                await self.evnt.wait()

            async def wait_for_doits(self):
                await self.sema.acquire()
                await self.sema.acquire()
                self.evnt.set()

        bar = MyClass()

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')

            dmon.share('bar', bar)

            prox = await s_telepath.openurl('tcp://127.0.0.1/bar', port=addr[1])

            # Check proxy objects, and also make sure that it doesn't block on server

            tasks = [prox.do_it() for _ in range(2)]
            tasks.append(prox.wait_for_doits())
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
            await prox.fini()

    async def test_telepath_aware(self):

        item = TeleAware()

        async with self.getTestDmon() as dmon:
            dmon.share('woke', item)
            async with await self.getTestProxy(dmon, 'woke') as proxy:
                self.eq(10, await proxy.getFooBar(20, 10))

                # check a custom share works
                obj = await proxy.customshare()
                self.eq(999, await obj.boo(999))

                ret = await alist(obj.custgenr(3))
                self.eq(ret, [0, 1, 2])

            # check that a dynamic share works
            async with await self.getTestProxy(dmon, 'woke/up') as proxy:
                self.eq('up: beep', await proxy.beep())

    async def test_telepath_auth(self):

        item = TeleAuth()
        async with self.getTestDmon() as dmon:
            dmon.share('auth', item)
            host, port = dmon.addr

            url = 'tcp://localhost/auth'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url, port=port))

            url = 'tcp://visi@localhost/auth'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url, port=port))

            url = 'tcp://visi:secretsauce@localhost/auth'
            async with await s_telepath.openurl(url, port=port) as proxy:
                self.eq(17, await proxy.getFooBar(10, 7))

    async def test_telepath_server_badvers(self):

        async with self.getTestDmon() as dmon:

            dmon.televers = (0, 0)

            host, port = await dmon.listen('tcp://127.0.0.1:0/')

            await self.asyncraises(s_exc.BadMesgVers, s_telepath.openurl('tcp://127.0.0.1/', port=port))

    async def test_alias(self):

        item = TeleAware()
        name = 'item'

        async with self.getTestDmon() as dmon:

            addr = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share(name, item)

            with self.getTestDir() as dirn:

                url = f'tcp://{addr[0]}:{addr[1]}/{name}'
                beepbeep_alias = url + '/beepbeep'
                aliases = {name: url,
                           f'{name}/borp': beepbeep_alias}

                with self.setSynDir(dirn):

                    fp = s_common.getSynPath('aliases.yaml')
                    s_common.yamlsave(aliases, fp)

                    # None existent aliases return None
                    self.none(s_telepath.alias('newp'))
                    self.none(s_telepath.alias('newp/path'))

                    # An exact match wins
                    self.eq(s_telepath.alias(name), url)
                    self.eq(s_telepath.alias(f'{name}/borp'), beepbeep_alias)
                    # Dynamic aliases are valid.
                    self.eq(s_telepath.alias(f'{name}/beepbeep'), beepbeep_alias)

                    async with await s_telepath.openurl(name) as prox:
                        self.eq(10, await prox.getFooBar(20, 10))

                    # Check to see that we can connect to an aliased name
                    # with a dynamic share attached to it.
                    async with await s_telepath.openurl(f'{name}/bar') as prox:
                        self.eq('bar: beep', await prox.beep())

    async def test_default_name(self):

        async with self.getTestDmon() as dmon:

            addr, port = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('*', Foo())

            async with await s_telepath.openurl(f'tcp://{addr}:{port}/') as prox:
                self.eq('hiya', await prox.echo('hiya'))

    async def test_url_cell(self):

        with self.getTestDir(chdir=True) as dirn:

            path = os.path.join(dirn, 'cell')

            async with await s_cell.Cell.anit(path) as cell:

                # test a relative cell:// url
                async with await s_telepath.openurl('cell://cell') as prox:
                    self.eq('cell', await prox.getCellType())

                # test an absolute cell:// url
                async with await s_telepath.openurl(f'cell://{path}') as prox:
                    self.eq('cell', await prox.getCellType())
