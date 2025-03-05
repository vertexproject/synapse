import os
import ssl
import socket
import asyncio
import logging
import threading

from unittest import mock

import cryptography.hazmat.primitives.hashes as c_hashes

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.share as s_share
import synapse.lib.certdir as s_certdir
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

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

    def genbeep(self):
        yield self.beep()

class Foo:

    def __init__(self):
        self.sleepg_evt = asyncio.Event()
        self.simplesleep_evt = asyncio.Event()

    def bar(self, x, y):
        return x + y

    def baz(self, x, y):
        raise ValueError('derp')

    def echo(self, x):
        return x

    def echosize(self, array: list[bytes]):
        total = sum([len(bytz) for bytz in array])
        return total

    def speed(self):
        return

    async def sleepg(self, t=60):
        self.sleepg_evt.clear()
        yield ('init', {})
        try:
            await asyncio.sleep(t)
        except asyncio.CancelledError:
            self.sleepg_evt.set()
            raise
        yield ('fini', {})

    async def simplesleep(self):
        self.simplesleep_evt.set()
        await asyncio.sleep(10)
        return 42

    def genr(self):
        yield 10
        yield 20
        yield 30

    def genrboom(self):
        yield 10
        yield 20
        raise s_exc.SynErr(mesg='derp')

    async def agenrboom(self):
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


class TeleApi:

    def __init__(self, item, link):
        self.item = item
        self.link = link

    def getFooBar(self, x, y):
        return x - y

    def genGetFooBar(self, x, y):
        yield self.getFooBar(x, y)

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

    async def getTeleFeats(self):
        return {
            'aware': 1,
        }

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

        urls = (
            'aha://visi@foo.bar.com',
            'ssl://visi@foo.bar.com?hostname=woot',
            'aha://visi@127.0.0.1/foo/bar&hostname=hehe',
            'ssl://127.0.0.1:2222/&hostname=hehe?ca=haha',
            'tcp://visi:secret@localhost:2929/foo/bar&certname=hehe',
        )

        for url in urls:
            self.eq(url, s_telepath.zipurl(s_telepath.chopurl(url)))

        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            await self.asyncraises(s_exc.BadUrl, s_telepath.openurl('noscheme/foo'))

            with self.raises(s_exc.BadArg):
                await s_telepath.openurl(10)

            prox = await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1])

            # Some bookkeeping data about the connection is available
            # from the daemon related to the session's objects and
            # connection information.
            snfo = await dmon.getSessInfo()
            self.len(1, snfo)
            self.eq(snfo[0].get('items'), {None: 'synapse.tests.test_telepath.Foo'})
            conninfo = snfo[0].get('conninfo')
            self.isinstance(conninfo, dict)
            self.eq(conninfo.get('family'), 'tcp')
            self.eq(conninfo.get('ipver'), 'ipv4')
            # The prox's local sock.getsockname() corresponds to the
            # server's sock.getpeername()
            self.eq(conninfo.get('addr'), prox.link.sock.getsockname())

            # Prox exposes remote synapse version
            self.eq(prox._getSynVers(), s_version.version)

            # Prox exposes remote synapse commit hash
            self.eq(prox._getSynCommit(), s_version.commit)

            # Prox exposes reflected classes
            self.eq(prox._getClasses(),
                    ('synapse.tests.test_telepath.Foo',))

            # Add an additional prox.fini handler.
            prox.onfini(evt.set)

            with mock.patch('synapse.lib.link.MAXWRITE', 2):

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
            self.eq((0, 1, 2), await s_t_utils.alist(genr))

            # check async generator explodes channel
            genr = prox.agenrboom()
            await self.asyncraises(s_exc.SynErr, genr.list())

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

            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1]) as prox:
                self.eq((10, 20, 30), await s_coro.executor(sync))

    def test_telepath_sync_genr_break(self):

        try:
            acm = self.getTestCoreAndProxy()
            core, proxy = s_glob.sync(acm.__aenter__())

            form = 'test:int'

            q = '[' + ' '.join([f'{form}={i}' for i in range(10)]) + ' ]'

            # This puts a link into the link pool
            msgs = list(proxy.storm(q, opts={'show': ('node',)}))
            self.len(12, msgs)

            evt = threading.Event()

            # Get the link from the pool, add the fini callback and put it back
            link = s_glob.sync(proxy.getPoolLink())
            link.onfini(evt.set)
            s_glob.sync(proxy._putPoolLink(link))

            # Grab the fresh link from the pool so our original link is up next again
            link2 = s_glob.sync(proxy.getPoolLink())
            s_glob.sync(proxy._putPoolLink(link2))

            q = f'{form} | sleep 0.1'

            # Break from the generator right away, causing a
            # GeneratorExit in the GenrHelp object __iter__ method.
            mesg = None
            for mesg in proxy.storm(q):
                break
            # Ensure the query did yield an object
            self.nn(mesg)

            # Ensure the link we have a reference too was torn down
            self.true(evt.wait(4))
            self.true(link.isfini)

        finally:
            s_glob.sync(acm.__aexit__(None, None, None))

    async def test_telepath_no_sess(self):

        foo = Foo()
        evt = asyncio.Event()

        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            await self.asyncraises(s_exc.BadUrl, s_telepath.openurl('noscheme/foo'))

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1]) as prox:

                prox.sess = None

                # Add an additional prox.fini handler.
                prox.onfini(evt.set)

                # check a standard return value
                self.eq(30, await prox.bar(10, 20))

                # check a coroutine return value
                self.eq(25, await prox.corovalu(10, 5))

                # check a generator return channel
                genr = await prox.genr()
                self.eq((10, 20, 30), await s_t_utils.alist(genr))

                # check an async generator return channel
                genr = prox.corogenr(3)
                self.eq((0, 1, 2), await s_t_utils.alist(genr))

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

    async def test_telepath_tls_certhash(self):

        self.thisHostMustNot(platform='darwin')

        foo = Foo()

        with self.getTestDir() as dirn:

            path = (s_common.gendir(dirn, 'dmoncerts'),)
            certdir = s_certdir.CertDir(path=path)

            async with await s_daemon.Daemon.anit(certdir=certdir) as dmon:

                hostname = socket.gethostname()

                certdir.genCaCert('loopy')
                hostkey, hostcert = certdir.genHostCert(hostname, signas='loopy')
                self.none(certdir.getHostCertHash('newp.newp.newp'))

                certhash = s_common.ehex(hostcert.fingerprint(c_hashes.SHA256()))

                host, port = await dmon.listen(f'ssl://{hostname}:0')
                dmon.share('foo', foo)

                certtext = await s_coro.executor(ssl.get_server_certificate, (hostname, port))
                cert = certdir._loadCertByts(certtext.encode())

                # host cert is *NOT* signed by a CA that client recognizes
                with self.raises(ssl.SSLCertVerificationError):
                    await s_telepath.openurl(f'ssl://{hostname}/foo', port=port)

                with self.raises(s_exc.LinkBadCert):
                    await s_telepath.openurl(f'ssl://{hostname}/foo', port=port, certhash='asdfasdf')

                # still not, but we specify a certhash for the exact server certificate
                async with await s_telepath.openurl(f'ssl://{hostname}/foo', port=port, certhash=certhash) as foo:
                    self.eq('woot', await foo.echo('woot'))

    async def test_telepath_ssl_client_cert(self):

        foo = Foo()
        async with self.getTestDmon() as dmon:

            dmon.certdir.genCaCert('userca')
            dmon.certdir.genUserCert('visi', signas='userca')
            dmon.certdir.genUserCert('visi@localhost', signas='userca')

            addr, port = await dmon.listen('ssl://127.0.0.1:0/?ca=userca&hostname=localhost')
            dmon.share('foo', foo)

            with self.raises(s_exc.LinkShutDown):
                await s_telepath.openurl(f'ssl://localhost/foo', port=port, certdir=dmon.certdir)

            async with await s_telepath.openurl(f'ssl://localhost/foo?certname=visi', port=port, certdir=dmon.certdir) as proxy:
                self.eq(20, await proxy.bar(15, 5))

            async with await s_telepath.openurl(f'ssl://visi@localhost/foo', port=port, certdir=dmon.certdir) as proxy:
                self.eq(20, await proxy.bar(15, 5))

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

                # The daemon's session information for a TLS link
                # its own family.
                sessions = await dmon.getSessInfo()
                self.len(1, sessions)
                self.eq(sessions[0].get('conninfo').get('family'), 'tls')

    async def test_telepath_tls_sni(self):

        self.thisHostMustNot(platform='darwin')

        foo = Foo()
        async with self.getTestDmon() as dmon:

            dmon.certdir.genHostCert('hehe', signas='ca')
            dmon.certdir.genHostCert('haha', signas='ca')
            dmon.certdir.genHostCert('nolisten')

            dmon.share('foo', foo)
            addr = await dmon.listen(f'ssl://127.0.0.1:0?hostname=hehe,haha')

            async with await s_telepath.openurl(f'ssl://127.0.0.1/foo?hostname=hehe', port=addr[1]) as prox:
                self.eq(30, await prox.bar(10, 20))

            async with await s_telepath.openurl(f'ssl://127.0.0.1/foo?hostname=haha', port=addr[1]) as prox:
                self.eq(30, await prox.bar(10, 20))

            # Default does not match expected hostname
            with self.raises(s_exc.BadCertHost) as cm:
                url = f'ssl://127.0.0.1/foo?hostname=nolisten'
                async with await s_telepath.openurl(url, port=addr[1]) as prox:
                    pass
            mesg = cm.exception.get('mesg')
            self.eq(mesg, 'Expected: nolisten Got: hehe')

    async def test_telepath_surrogate(self):

        foo = Foo()
        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1]) as prox:
                bads = '\u01cb\ufffd\ud842\ufffd\u0012'
                t0 = ('1234', {'key': bads})

                # Shovel a malformed UTF8 string with an unpaired surrogate over telepath
                ret = await prox.echo(t0)
                self.eq(ret, t0)

    async def test_telepath_async(self):

        foo = Foo()

        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1]) as prox:

                genr = prox.corogenr(3)
                self.eq([0, 1, 2], [x async for x in genr])

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

            await self.asyncraises(s_exc.LinkShutDown, aitr.__anext__())
            start_event.set()

            # Test that a coroutine about to await on an async proxy method doesn't become "stuck" by awaiting on a
            # just-fini'd object method

            # Give the longwaiter a chance to run
            await asyncio.sleep(.1)

            await self.asyncraises(s_exc.IsFini, asyncio.wait_for(task, timeout=2))

    async def test_telepath_asyncgenr_early_term(self):

        foo = Foo()

        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            # Test with and without session (telepath v2 and v1)
            for do_sess in (True, False):
                retn = []

                async with await s_telepath.openurl('tcp://127.0.0.1/foo', port=dmon.addr[1]) as prox:
                    if not do_sess:
                        prox.sess = None

                    with self.raises(s_exc.LinkShutDown):

                        genr = prox.corogenr(1000)
                        async for i in genr:
                            retn.append(i)
                            if i == 2:
                                # yank out the ethernet cable
                                await list(dmon.links)[0].fini()

                self.eq(retn, [0, 1, 2])

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

                # Ensure the session tracks the reference to the TeleApi object
                sess = dmon.sessions[list(dmon.sessions.keys())[0]]
                self.isinstance(sess.getSessItem(None), TeleApi)
                # And that data is available from the session helper API
                snfo = await dmon.getSessInfo()
                self.len(1, snfo)
                self.eq(snfo[0].get('items'), {None: 'synapse.tests.test_telepath.TeleApi'})

                self.true(proxy._hasTeleFeat('aware'))
                self.false(proxy._hasTeleFeat('aware', vers=2))
                self.false(proxy._hasTeleFeat('newp'))

                self.true(proxy._hasTeleMeth('getFooBar'))
                self.false(proxy._hasTeleMeth('getBarBaz'))

                self.eq(10, await proxy.getFooBar(20, 10))
                self.eq([10], [m async for m in await proxy.genGetFooBar(20, 10)])

                # check a custom share works
                obj = await proxy.customshare()
                self.eq(999, await obj.boo(999))

                # Ensure the Share object is placed into the
                # session for the daemon.
                self.len(2, sess.items)
                key = [k for k in sess.items.keys() if k][0]
                self.isinstance(sess.getSessItem(key), CustomShare)

                # make another customshare reference which will be
                # tracked by the Sess object
                evt = asyncio.Event()
                async with await proxy.customshare():
                    self.len(3, sess.items)
                    _key = [k for k in sess.items.keys() if k and k != key][0]
                    _cshare = sess.getSessItem(_key)
                    self.isinstance(_cshare, CustomShare)
                    _cshare.onfini(evt.set)

                # and that item is removed from the sess on the
                # _share fini by the client
                self.true(await asyncio.wait_for(evt.wait(), 6))
                self.len(2, sess.items)
                self.nn(sess.getSessItem(key))

                # ensure that the share is represented in the session info via
                # the helper APIs as well
                snfo = await dmon.getSessInfo()
                self.len(1, snfo)
                self.eq(snfo[0].get('items'),
                        {None: 'synapse.tests.test_telepath.TeleApi',
                         key: 'synapse.tests.test_telepath.CustomShare'})

                # and we can still use the first obj we made
                ret = await s_t_utils.alist(obj.custgenr(3))
                self.eq(ret, [0, 1, 2])

            # check that a dynamic share works
            async with await self.getTestProxy(dmon, 'woke/up') as proxy:
                self.isin('synapse.tests.test_telepath.Beep', proxy._getClasses())
                self.notin('synapse.tests.test_telepath.TeleApi', proxy._getClasses())
                self.eq('up: beep', await proxy.beep())
                self.eq(['up: beep'], [m async for m in await proxy.genbeep()])
                # Telepath features are a function of the base object, not the result of getTeleApi
                self.true(proxy._hasTeleFeat('aware'))
                self.false(proxy._hasTeleFeat('aware', vers=2))
                self.false(proxy._hasTeleFeat('newp'))

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

            host, port = dmon.addr
            dmon.share(name, item)

            with self.getTestDir() as dirn:

                url = f'tcp://{host}:{port}/{name}'
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

            host, port = dmon.addr
            dmon.share('*', Foo())

            async with await s_telepath.openurl(f'tcp://{host}:{port}/') as prox:
                self.eq('hiya', await prox.echo('hiya'))

    async def test_url_cell(self):

        with self.getTestDir(chdir=True) as dirn:

            path = os.path.join(dirn, 'cell')
            sockpath = os.path.join(path, 'sock')

            async with await s_cell.Cell.anit(path) as cell:

                # test a relative cell:// url
                async with await s_telepath.openurl('cell://cell') as prox:
                    self.eq('cell', await prox.getCellType())
                    # unix path information is available from the session information.
                    snfo = await cell.dmon.getSessInfo()
                    self.eq(snfo[0].get('conninfo'),
                            {'family': 'unix',
                             'addr': sockpath})

                # test an absolute cell:// url
                async with await s_telepath.openurl(f'cell://{path}') as prox:
                    self.eq('cell', await prox.getCellType())
                    # unix path information is available from the session information.
                    snfo = await cell.dmon.getSessInfo()
                    self.eq(snfo[0].get('conninfo'),
                            {'family': 'unix',
                             'addr': sockpath})

    async def test_ipv6(self):
        if s_common.envbool('CIRCLECI'):
            self.skip('ipv6 listener is not supported in circleci')

        foo = Foo()

        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)
            try:
                addr = await dmon.listen('tcp://[::1]:0/')
            except (asyncio.CancelledError, OSError):
                raise
            host, port = addr[0], addr[1]

            async with await s_telepath.openurl(f'tcp://{host}/foo',
                                                port=port) as prox:
                # Ensure that ipv6 is returned via session info
                snfo = await dmon.getSessInfo()
                conninfo = snfo[0].get('conninfo')
                self.eq(conninfo, {'family': 'tcp',
                                   'ipver': 'ipv6',
                                   'addr': prox.link.sock.getsockname()})

                # check a standard return value
                self.eq(30, await prox.bar(10, 20))

    async def test_telepath_client_failover(self):

        class TestFail:
            def __init__(self):
                self.count = 0

            async def dostuff(self, x):
                self.count += 1
                return x + 10

        dmon0 = await s_daemon.Daemon.anit()
        dmon1 = await s_daemon.Daemon.anit()

        addr0 = await dmon0.listen('tcp://127.0.0.1:0/')
        addr1 = await dmon1.listen('tcp://127.0.0.1:0/')

        url0 = f'tcp://user:password@127.0.0.1:{addr0[1]}/foo'
        url1 = f'tcp://127.0.0.1:{addr1[1]}/foo'

        fail0 = TestFail()
        fail1 = TestFail()

        dmon0.share('foo', fail0)
        dmon1.share('foo', fail1)

        urls = (url0, url1)

        async with await s_telepath.open(urls) as targ:

            await targ.waitready()

            prox00 = await targ.proxy(timeout=12)
            self.eq(110, await prox00.dostuff(100))

            self.eq(1, fail0.count)
            self.eq(0, fail1.count)

            await dmon0.fini()
            self.true(await prox00.waitfini(10))

            prox01 = await targ.proxy(timeout=12)
            self.eq(110, await prox01.dostuff(100))
            self.eq(1, fail0.count)
            self.eq(1, fail1.count)

        async with await s_telepath.open(urls) as targ:

            with self.getAsyncLoggerStream('synapse.telepath', 'Connect call failed') as stream:

                await targ.waitready()

                # Verify the password doesn't leak into the log
                self.true(await stream.wait(2))
                stream.seek(0)
                mesgs = stream.read()
                self.notin('password', mesgs)

            prox00 = await targ.proxy(timeout=12)
            self.eq(110, await prox00.dostuff(100))

            self.eq(1, fail0.count)
            self.eq(2, fail1.count)

        async with await s_telepath.open(url1) as targ:
            await targ.waitready(timeout=12)
            prox00 = await targ.proxy(timeout=12)
            self.eq(110, await prox00.dostuff(100))

        async def onlink(proxy, urlinfo):
            self.eq(110, await proxy.dostuff(100))
            _url = s_telepath.zipurl(urlinfo)
            logger.info(f'Connected to url={_url}')

        with self.getAsyncLoggerStream('synapse.tests.test_telepath',
                                       f'Connected to url=tcp://127.0.0.1:{addr1[1]}/foo') as stream:
            async with await s_telepath.open(url1, onlink=onlink) as targ:
                self.true(await stream.wait(timeout=12))

        # Coverage
        async def badonlink(proxy, urlinfo):
            raise ValueError('oopsie')

        with self.getAsyncLoggerStream('synapse.telepath', 'onlink: ') as stream:
            async with await s_telepath.open(url1, onlink=badonlink) as targ:
                self.true(await stream.wait(timeout=12))

        await dmon0.fini()
        await dmon1.fini()

    async def test_telepath_poolsize(self):

        # While test_telepath_sync_genr_break also touches the link pool,
        # it doesn't validate the pool size or automatic link teardown
        # behavior when a extra link is placed into the pool.
        foo = Foo()

        async with self.getTestDmon() as dmon:
            dmon.share('foo', foo)
            url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'

            # Validate the Proxy behavior then the client override
            prox = await s_telepath.openurl(url)  # type: Foo

            # Start with no links
            self.len(0, prox.links)
            self.eq(await prox.echo(1), 1)

            # We now have one link - spin up a generator to grab it
            self.len(1, prox.links)
            l0 = prox.links[0]
            genr = await prox.genr()  # type: s_coro.GenrHelp
            self.eq(await genr.genr.__anext__(), 10)

            # A new link is in the pool
            self.len(1, prox.links)

            # and upon exhuastion, the first link is put back
            self.eq(await genr.list(), (20, 30))
            self.len(2, prox.links)
            self.true(prox.links[1] is l0)

            # Grabbing a link will still spin up another since we are below low watermark
            genr = await prox.genr()  # type: s_coro.GenrHelp
            self.eq(await genr.genr.__anext__(), 10)

            self.len(2, prox.links)

            self.eq(await genr.list(), (20, 30))
            self.len(3, prox.links)

            # Fill up pool above low watermark
            genrs = [await prox.genr() for _ in range(2)]
            [await genr.list() for genr in genrs]
            self.len(5, prox.links)

            # Grabbing a link no longer spins up a replacement
            genr = await prox.genr()  # type: s_coro.GenrHelp
            self.eq(await genr.genr.__anext__(), 10)
            self.len(4, prox.links)

            self.eq(await genr.list(), (20, 30))
            self.len(5, prox.links)

            # Tear down a link by hand and place it back
            # into the pool - that will fail b/c the link
            # has been down down.
            l1 = await prox.getPoolLink()
            self.len(4, prox.links)
            await l1.fini()
            await prox._putPoolLink(l1)
            self.len(4, prox.links)

            # And all our links are torn down on fini
            await prox.fini()
            self.len(4, prox.links)
            for link in list(prox.links):
                self.true(await link.waitfini(1))
            self.len(0, prox.links)

        with mock.patch('synapse.telepath.LINK_CULL_INTERVAL', 1):
            async with self.getTestDmon() as dmon:
                dmon.share('foo', foo)
                url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'

                prox = await s_telepath.openurl(url)

                # Fill up pool above high watermark
                genrs = [await prox.genr() for _ in range(13)]
                [await genr.list() for genr in genrs]
                self.len(13, prox.links)

                # Add a fini'd proxy for coverage
                prox2 = await s_telepath.openurl(url)
                await prox2.fini()
                prox2._all_proxies.add(prox2)

                wait = prox.waiter(1, 'pool:link:fini')
                self.len(1, await wait.wait(timeout=5))
                self.len(12, prox.links)

    async def test_link_fini_breaking_tasks(self):
        foo = Foo()

        async with self.getTestDmon() as dmon:
            dmon.share('foo', foo)
            url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'

            async with await s_telepath.openurl(url) as proxy:

                with self.getAsyncLoggerStream('synapse.daemon',
                                               'task sleepg') as stream:

                    # Fire up an async generator which will yield a message then
                    # wait for a while so that our break will tear it down
                    async for mesg in proxy.sleepg(t=60):
                        self.eq(mesg, ('init', {}))
                        break

                    # Ensure that the sleepg function got canceled.
                    self.true(await asyncio.wait_for(foo.sleepg_evt.wait(), timeout=6))
                    # Ensure we logged the cancellation.
                    self.true(await stream.wait(6))

    async def test_link_fini_breaking_tasks2(self):
        '''
        Similar to the previous test, except tears down a proxy that another task is using
        '''
        foo = Foo()
        async with self.getTestDmon() as dmon:
            dmon.share('foo', foo)
            url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'
            prox = await s_telepath.openurl(url)  # type: Foo

            async def doit():
                retn = await prox.simplesleep()
                return retn

            task = dmon.schedCoro(doit())
            self.true(await s_coro.event_wait(foo.simplesleep_evt, 2))
            await prox.fini()

            await self.asyncraises(s_exc.LinkShutDown, task)

    async def test_telepath_pipeline(self):

        foo = Foo()
        async with self.getTestDmon() as dmon:

            dmon.share('foo', foo)

            async def genr():
                yield s_common.todo('bar', 10, 30)
                yield s_common.todo('bar', 20, 30)
                yield s_common.todo('bar', 30, 30)

            url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'
            async with await s_telepath.openurl(url) as proxy:

                self.eq(20, await proxy.bar(10, 10))
                self.eq(1, len(proxy.links))

                vals = []
                async for retn in proxy.getPipeline(genr()):
                    vals.append(s_common.result(retn))

                self.eq(vals, (40, 50, 60))

                self.eq(2, len(proxy.links))
                self.eq(160, await proxy.bar(80, 80))

                async def boomgenr():
                    yield s_common.todo('bar', 10, 30)
                    raise s_exc.NoSuchIden()

                with self.raises(s_exc.NoSuchIden):
                    async for retn in proxy.getPipeline(boomgenr()):
                        pass

                # This test must remain at the end of the with block
                async def sleeper():
                    yield s_common.todo('bar', 10, 30)
                    await asyncio.sleep(3)

                with self.raises(s_exc.LinkShutDown):
                    async for retn in proxy.getPipeline(sleeper()):
                        vals.append(s_common.result(retn))
                        await proxy.fini()

    async def test_telepath_client_onlink_exc(self):

        cnts = {
            'ok': 0,
            'exc': 0,
            'loops': 0,
            'inits': 0
        }
        evnt = asyncio.Event()
        loopevent = asyncio.Event()
        origfire = s_telepath.Client._fireLinkLoop
        originit = s_telepath.Client._initTeleLink

        tgt = {'n': 3}

        async def countLinkLoops(self):
            cnts['loops'] += 1
            if cnts['loops'] > tgt.get('n'):
                loopevent.set()
            await origfire(self)

        async def countInitLinks(self, url):
            cnts['inits'] += 1
            if cnts['inits'] > tgt.get('n'):
                evnt.set()

            await originit(self, url)

        async def onLinkOk(p):
            cnts['ok'] += 1

        async def onlinkFail(p):
            await p.fini()

        async def onlinkExc(p):
            cnts['exc'] += 1
            raise s_exc.SynErr(mesg='ohhai')

        foo = Foo()

        async with self.getTestDmon() as dmon:
            dmon.share('foo', foo)
            url = f'tcp://127.0.0.1:{dmon.addr[1]}/foo'

            async with await s_telepath.Client.anit(url) as targ:
                proxy = await targ.proxy(timeout=2)
                await targ.onlink(onLinkOk)
                self.ge(cnts['ok'], 1)
                with self.raises(s_exc.SynErr):
                    await targ.onlink(onlinkExc)
                self.ge(cnts['exc'], 1)

            with mock.patch('synapse.telepath.Client._fireLinkLoop', countLinkLoops):
                with mock.patch('synapse.telepath.Client._initTeleLink', countInitLinks):
                    async with await s_telepath.Client.anit(url, onlink=onlinkFail) as targ:
                        fut = asyncio.gather(asyncio.wait_for(evnt.wait(), timeout=6),
                                             asyncio.wait_for(loopevent.wait(), timeout=6))
                        self.eq((True, True), await fut)
                        self.ge(cnts['loops'], 4)
                        self.ge(cnts['inits'], 4)

                    evnt.clear()
                    loopevent.clear()
                    tgt['n'] = 4

                    async with await s_telepath.Client.anit(url, onlink=onlinkExc) as targ:
                        fut = asyncio.gather(asyncio.wait_for(evnt.wait(), timeout=30),
                                             asyncio.wait_for(loopevent.wait(), timeout=30),)
                        self.eq((True, True), await fut)
                        self.ge(cnts['loops'], 5)
                        self.ge(cnts['inits'], 5)

    async def test_client_method_reset(self):
        class Foo:
            def __init__(self):
                self.a = 1

            async def foo(self):
                return self.a

            async def bar(self):
                for i in range(self.a):
                    yield i

        class Bar:
            def bar(self):
                return 'bar'

        foo = Foo()
        bar = Bar()

        with self.getTestDir() as dirn:
            url = f'cell://{dirn}'
            url = url + ':obj'
            surl = os.path.join(f'unix://{dirn}', 'sock')

            async with await s_telepath.Client.anit(url) as prox:
                async with self.getTestDmon() as dmon:
                    dmon.share('obj', foo)
                    await dmon.listen(surl)

                    self.none(await prox.waitready())
                    self.eq(await prox.foo(), 1)

                    # The .bar function is a genrmeth
                    self.eq(await prox.bar().list(), [0],)
                    self.eq(prox._t_named_meths, {'foo', 'bar'})

                    # Disable the dmon and wait for the proxy to have been fini'd
                    dmon.schedCoro(dmon.setReady(False))
                    self.true(await prox._t_proxy.waitfini(10))

                    # Swap out the object and reconnect
                    dmon.share('obj', bar)
                    await dmon.setReady(True)
                    self.none(await prox.waitready())
                    self.eq(prox._t_named_meths, set())

                    # .foo is gone
                    with self.raises(s_exc.NoSuchMeth):
                        self.eq(await prox.foo(), 1)
                    # The type of the .bar function changed so it is
                    # no longer a genrmeth and can be called directly
                    self.eq(await prox.bar(), 'bar')
                    # We still have foo and bar as named meths
                    self.eq(prox._t_named_meths, {'foo', 'bar'})

    async def test_telepath_loadenv(self):
        with self.getTestDir() as dirn:

            certpath = s_common.gendir(dirn, 'certs')
            newppath = s_common.genpath(dirn, 'newps')

            conf = {
                'version': 1,
                'aha:servers': [
                    'tcp://localhost:9999/',
                ],
                'certdirs': [
                    certpath,
                    newppath,
                ],
            }

            path = s_common.genpath(dirn, 'telepath.yaml')
            s_common.yamlsave(conf, path)

            fini = await s_telepath.loadTeleEnv(path)
            await fini()

            self.none(await s_telepath.loadTeleEnv(newppath))

            conf['version'] = 99
            s_common.yamlsave(conf, path)
            self.none(await s_telepath.loadTeleEnv(path))

    async def test_telepath_default_port(self):
        # Test default ports for dmon listening AND telepath connections.
        async with await s_daemon.Daemon.anit() as dmon:
            url = 'tcp://127.0.0.1/'
            try:
                addr, port = await dmon.listen(url)
            except OSError as e:
                if e.errno == 98:
                    self.skip('Port 27492 already bound, skipping test.')
                else:
                    raise
            self.eq(port, 27492)

            foo = Foo()
            dmon.share('foo', foo)

            furl = 'tcp://127.0.0.1/foo'
            async with await s_telepath.openurl(furl) as proxy:
                self.isin('synapse.tests.test_telepath.Foo', proxy._getClasses())
                self.eq(await proxy.echo('oh hi mark!'), 'oh hi mark!')

    async def test_tls_support_and_ciphers(self):

        self.thisHostMustNot(platform='darwin')

        foo = Foo()

        async with self.getTestDmon() as dmon:
            # As a workaround to a Python bug (https://bugs.python.org/issue30945) that prevents localhost:0 from
            # being connected via TLS, make a certificate for whatever my hostname is and sign it with the test CA
            # key.
            hostname = socket.gethostname()

            dmon.certdir.genHostCert(hostname, signas='ca')

            _, port = await dmon.listen(f'ssl://{hostname}:0')

            dmon.share('foo', foo)

            # Ensure tls listener is working before trying downgraded versions
            async with await s_telepath.openurl(f'ssl://{hostname}/foo', port=port) as prox:
                self.eq(30, await prox.bar(10, 20))

                # This will generate a large msgpack object which can cause
                # openssl to have malloc failures. Prior to the write chunking
                # changes, this would cause a generally fatal error to any
                # processes which rely on the calls work, such as mirror loops.
                blob = b'V' * s_const.mebibyte * 256
                nblobs = 8
                total = nblobs * len(blob)
                blobarray = []
                for i in range(nblobs):
                    blobarray.append(blob)
                self.eq(await prox.echosize(blobarray), total)

            sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
            with self.raises((ssl.SSLError, ConnectionResetError)):
                link = await s_link.connect(hostname, port=port, ssl=sslctx)

            sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_1)
            with self.raises((ssl.SSLError, ConnectionResetError)):
                link = await s_link.connect(hostname, port=port, ssl=sslctx)

            sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            sslctx.set_ciphers('ADH-AES256-SHA')
            with self.raises(ssl.SSLError):
                link = await s_link.connect(hostname, port=port, ssl=sslctx)

            sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            sslctx.set_ciphers('AES256-GCM-SHA384')
            with self.raises(ConnectionResetError):
                link = await s_link.connect(hostname, port=port, ssl=sslctx)

            sslctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
            sslctx.set_ciphers('DHE-RSA-AES256-SHA256')
            with self.raises(ConnectionResetError):
                link = await s_link.connect(hostname, port=port, ssl=sslctx)
