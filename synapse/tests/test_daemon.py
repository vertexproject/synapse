import asyncio

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.stormsvc as s_stormsvc

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.tests.utils as s_t_utils

class Foo:
    def woot(self):
        return 10

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
