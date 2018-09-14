import synapse.cells as s_cells
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.certdir as s_certdir
import synapse.lib.link as s_link

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

class DaemonTest(s_t_utils.ASynTest):

    async def test_daemon_certdir(self):

        # ensure the test env by checking for certs
        async with self.getTestDmon() as dmon:
            path = s_common.genpath(dmon.dirn, 'certs')
            self.eq(s_certdir.defdir, path)

        self.ne(s_certdir.defdir, path)

    async def test_daemon_boot(self):
        # get a localhost:0 dmon with an EchoCell "echo00"
        async with self.getTestDmon(mirror='dmonboot') as dmon:

            self.nn(dmon.shared.get('echo00'))
            self.nn(dmon.mods.get('synapse.tests.test_daemon'))

            host, port = dmon.addr

            breakpoint()
            with await s_telepath.openurl('tcp:///echo00', host=host, port=port) as prox:

                self.eq('woot', prox.ping('woot'))

    async def test_daemon_timeout(self):

        self.skip('TODO: port to test_telepath')

        # TODO move me test_telepath

        daemon = await s_daemon.Daemon.anit()
        link = daemon.listen('tcp://127.0.0.1:0/?timeout=0.1')

        relay = s_link.getLinkRelay(link)
        sock = relay.connect()

        self.eq(sock.recvobj(), None)

        sock.fini()
        await daemon.fini()
