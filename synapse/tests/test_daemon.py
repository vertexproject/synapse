import asyncio

import unittest.mock as mock

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormsvc as s_stormsvc

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.tests.utils as s_t_utils

class Foo:
    YIELD_PREFIX = b'\x92\xa8t2:yield\x81\xa4retn\x92\xc3'
    def woot(self):
        return 10

    def sync_iter(self, n):
        if n < 1:
            raise s_exc.BadArg(megs='N less than 1', valu=n)
        for i in range(n):
            yield i

    async def async_iter(self, n, boom=False):
        for i in self.sync_iter(n):
            yield i
        if boom:
            await asyncio.sleep(0)
            raise s_exc.BadState(megs='boom', valu=n)

    async def async_iter_direct(self, n, boom=False):
        # Must be detected as a generator
        if False:
            yield True
        link = s_scope.get('link')
        async for i in self.async_iter(n, boom=boom):
            mesg = self.YIELD_PREFIX + s_msgpack.en(i)
            await link.send(mesg)

class DaemonTest(s_t_utils.SynTest):

    async def test_unixsock_longpath(self):

        # Explicit failure for starting a daemon with a path too deep
        # this also covers a cell failure case since the cell may start
        # a daemon.
        # This fails because of limitations onf the path length for a UNIX
        # socket being no greater than what may be stored in a mbuf.
        # The maximum length is OS dependent; with Linux using 108 characters
        # and BSD's using 104.
        with self.getTestDir() as dirn:
            extrapath = 108 * 'A'
            longdirn = s_common.genpath(dirn, extrapath)
            listpath = f'unix://{s_common.genpath(longdirn, "sock")}'
            with self.getAsyncLoggerStream('synapse.daemon',
                                           'exceeds OS supported UNIX socket path length') as stream:

                async with await s_daemon.Daemon.anit() as dmon:
                    with self.raises(OSError):
                        await dmon.listen(listpath)

                self.true(await stream.wait(1))

    async def test_dmon_ready(self):

        async with await s_daemon.Daemon.anit() as dmon:

            host, port = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', Foo())

            async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}/foo') as foo:
                self.eq(10, await foo.woot())
                await dmon.setReady(False)
                await foo.waitfini(timeout=2)
                self.true(foo.isfini)

            with self.raises(s_exc.LinkShutDown):
                async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}/foo') as foo:
                    pass

    async def test_dmon_ahainfo(self):

        async with await s_daemon.Daemon.anit() as dmon:

            host, port = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('*', Foo())

            async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}') as proxy:
                self.eq(proxy._ahainfo, {})

        ahainfo = {'name': 'test.loop.vertex.link'}
        async with await s_daemon.Daemon.anit(ahainfo=ahainfo) as dmon:

            host, port = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('*', Foo())

            async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}') as proxy:
                self.eq(proxy._ahainfo, ahainfo)

    async def test_dmon_errors(self):

        async with self.getTestCell(s_cell.Cell, conf={'dmon:listen': 'tcp://0.0.0.0:0/', 'auth:anon': 'root'}) as cell:
            host, port = cell.sockaddr

            async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}') as prox:

                # Throw an exception when trying to handle mesg outright
                async with await prox.getPoolLink() as link:
                    with self.getAsyncLoggerStream('synapse.daemon', 'Dmon.onLinkMesg Handler: mesg=') as stream:
                        await link.tx(31337)
                        self.true(await stream.wait(timeout=6))

                # Valid format; do not know what the message is.
                async with await prox.getPoolLink() as link:
                    mesg = ('newp', {})
                    emsg = "Dmon.onLinkMesg Invalid mesg: mesg=('newp', {})"
                    with self.getAsyncLoggerStream('synapse.daemon', emsg) as stream:
                        await link.tx(mesg)
                        self.true(await stream.wait(timeout=6))

                # Invalid data casues a link to fail on rx
                async with await prox.getPoolLink() as link:
                    with self.getAsyncLoggerStream('synapse.lib.link', 'rx closed unexpectedly') as stream:
                        byts = b'\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03\xa6\xa3D\xd5\xdf%\xac\xa9\x92\xc3'
                        await link.send(byts)
                        self.true(await stream.wait(timeout=6))

                # bad t2:init message
                async with await prox.getPoolLink() as link:
                    mesg = ('t2:init', {})
                    emsg = "Error on t2:init:"
                    with self.getAsyncLoggerStream('synapse.daemon', emsg) as stream:
                        await link.tx(mesg)
                        self.true(await stream.wait(timeout=6))

    async def test_dmon_t2call_genr(self):

        # Ensure that t2call messages for generators are produced in the correct order.
        # Since we're patching Link.send, we get both the t2:init message AND the responses
        # from the daemon.

        async with await s_daemon.Daemon.anit() as dmon:

            host, port = await dmon.listen('tcp://127.0.0.1:0')
            dmon.share('foo', Foo())

            raw_msgs = []
            osend = s_link.Link.send

            async def psend(link, byts):
                raw_msgs.append(s_msgpack.un(byts))
                await osend(link, byts)

            async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}/foo') as foo:

                n = 3
                expv = [i for i in range(n)]
                msgs = []
                yield_msgs = [('t2:yield', {'retn': (True, i)}) for i in range(n)]
                genr_mesg = ('t2:genr', {})
                resp_mesgs = [genr_mesg] + yield_msgs + [('t2:yield', {'retn': None})]

                with mock.patch('synapse.lib.link.Link.send', psend):
                    async for i in await foo.sync_iter(n):
                        msgs.append(i)
                    self.eq(msgs, expv)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'sync_iter')
                self.eq(raw_msgs[1:], resp_mesgs)

                msgs.clear()
                raw_msgs.clear()
                with mock.patch('synapse.lib.link.Link.send', psend):
                    async for i in foo.async_iter(n):
                        msgs.append(i)
                    self.eq(msgs, expv)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'async_iter')
                self.eq(raw_msgs[1:], resp_mesgs)

                msgs.clear()
                raw_msgs.clear()
                with mock.patch('synapse.lib.link.Link.send', psend):
                    async for i in foo.async_iter_direct(n):
                        msgs.append(i)
                    self.eq(msgs, expv)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'async_iter_direct')
                self.eq(raw_msgs[1:], resp_mesgs)

                msgs.clear()
                raw_msgs.clear()

                with mock.patch('synapse.lib.link.Link.send', psend):
                    with self.raises(s_exc.BadArg):
                        async for i in foo.async_iter_direct(-1):
                            msgs.append(i)
                        self.eq(msgs, expv)
                self.len(0, msgs)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'async_iter_direct')
                self.eq(raw_msgs[1], ('t2:genr', {}))
                self.eq(raw_msgs[2][0], 't2:yield')
                self.eq(raw_msgs[2][1]['retn'][0], False)  # indicates the BadArg error

                msgs.clear()
                raw_msgs.clear()
                with mock.patch('synapse.lib.link.Link.send', psend):
                    with self.raises(s_exc.BadState):
                        async for i in foo.async_iter(n, boom=True):
                            msgs.append(i)
                        self.eq(msgs, expv)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'async_iter')
                self.eq(raw_msgs[1], genr_mesg)
                self.eq(raw_msgs[2:2 + n], yield_msgs)
                self.eq(raw_msgs[-1][1]['retn'][0], False)  # indicates the BadState error

                msgs.clear()
                raw_msgs.clear()
                with mock.patch('synapse.lib.link.Link.send', psend):
                    with self.raises(s_exc.BadState):
                        async for i in foo.async_iter_direct(n, boom=True):
                            msgs.append(i)
                        self.eq(msgs, expv)
                self.eq(raw_msgs[0][0], 't2:init')
                self.eq(raw_msgs[0][1]['todo'][0], 'async_iter_direct')
                self.eq(raw_msgs[1], genr_mesg)
                self.eq(raw_msgs[2:2 + n], yield_msgs)
                self.eq(raw_msgs[-1][1]['retn'][0], False)  # indicates the BadState error

class SvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = 'foo'
    _storm_svc_pkgs = (  # type:  ignore
        {
            'name': 'foo',
            'version': (0, 0, 1),
            'modules': (
                {
                    'name': 'foo.mod',
                    'storm': '''
                        $x = (3)

                        function run_all() {
                            for $item in $lib.service.get($modconf.svciden).run() {
                                {}
                            }
                            return ($lib.null)
                        }

                        function run_break() {
                            for $i in $lib.service.get($modconf.svciden).run() {
                                if ($i > $x) { return($lib.null) }
                            }
                            return($lib.null)
                        }

                        function run_err() {
                            for $i in $lib.service.get($modconf.svciden).run() {
                                if ($i > $x) { [inet:newp=3] }
                            }
                            return($lib.null)
                        }
                    '''
                },
            ),
        },
    )

    async def run(self):
        async for item in self.cell.run():
            yield item


class Svc(s_cell.Cell):
    cellapi = SvcApi

    async def initServiceStorage(self):
        self.events = []

    async def run(self):
        event = asyncio.Event()
        self.events.append(event)
        try:
            for i in range(100):
                yield i
                await asyncio.sleep(0)
        finally:
            event.set()


class GenrCloseTest(s_t_utils.SynTest):

    async def test_close(self):

        async with self.getTestCoreProxSvc(Svc) as (core, core_prox, svc):

            # storm exits early
            await core.stormlist('$lib.import(foo.mod).run_break()')
            self.true(await s_coro.event_wait(svc.events[0], timeout=1))

            # storm raises part way through iterating
            await core.stormlist('$lib.import(foo.mod).run_err()')
            self.true(await s_coro.event_wait(svc.events[1], timeout=1))

            # storm normal case
            await core.stormlist('$lib.import(foo.mod).run_all()')
            self.true(await s_coro.event_wait(svc.events[2], timeout=1))

            async with svc.getLocalProxy() as svc_prox:

                # telepath exits early
                async for i in svc_prox.run():
                    if i > 3:
                        break
                self.true(await s_coro.event_wait(svc.events[3], timeout=1))

                # telepath normal case
                async for i in svc_prox.run():
                    pass
                self.true(await s_coro.event_wait(svc.events[4], timeout=1))

            # python
            async for i in svc.run():
                if i > 3:
                    break
            self.true(await s_coro.event_wait(svc.events[5], timeout=1))
