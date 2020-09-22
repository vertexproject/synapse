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
