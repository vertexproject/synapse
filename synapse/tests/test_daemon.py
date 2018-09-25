import synapse.cells as s_cells
import synapse.common as s_common
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

    async def test_daemon_boot(self):
        # get a localhost:0 dmon with an EchoCell "echo00"
        async with self.getTestDmon(mirror='dmonboot') as dmon:

            self.nn(dmon.shared.get('echo00'))
            self.nn(dmon.mods.get('synapse.tests.test_daemon'))

            host, port = dmon.addr

            async with await s_telepath.openurl('tcp:///echo00', host=host, port=port) as prox:

                self.eq('woot', await prox.ping('woot'))
