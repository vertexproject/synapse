import synapse.cells as s_cells
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.certdir as s_certdir

import synapse.tests.utils as s_t_utils

class Newp: pass

class EchoApi(s_cell.CellApi):

    def ping(self, mesg):
        return mesg

    def newp(self):
        return Newp()

class EchoCell(s_cell.Cell):

    cellapi = EchoApi

s_cells.add('echo', EchoCell)

class DaemonTest(s_t_utils.SynTest):

    async def test_daemon_certdir(self):

        # ensure the test env by checking for certs
        async with self.getTestDmon() as dmon:
            path = s_common.genpath(dmon.dirn, 'certs')
            self.eq(s_certdir.defdir, path)

        self.ne(s_certdir.defdir, path)

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
                await self.asyncraises(OSError, s_daemon.Daemon.anit(longdirn, conf={'listen': listpath}))
                self.true(await stream.wait(1))
