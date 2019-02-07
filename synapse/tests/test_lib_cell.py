import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

class EchoAuthApi(s_cell.CellApi):

    def isadmin(self):
        return self.user.admin

    def allowed(self, perm):
        return self.user.allowed(perm)

class EchoAuth(s_cell.Cell):
    cellapi = EchoAuthApi

s_cells.add('echoauth', EchoAuth)

class CellTest(s_t_utils.SynTest):

    async def test_cell_auth(self):

        # test out built in cell auth
        async with self.getTestDmon(mirror='cellauth') as dmon:

            echo = dmon.shared.get('echo00')
            self.nn(echo)

            host, port = dmon.addr

            url = f'tcp://{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://fake@{host}:{port}/echo00'
            await self.asyncraises(s_exc.NoSuchUser, s_telepath.openurl(url))

            url = f'tcp://root@{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://root:newpnewp@{host}:{port}/echo00'
            await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            url = f'tcp://root:secretsauce@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:
                self.true(await proxy.isadmin())
                self.true(await proxy.allowed(('hehe', 'haha')))

            user = await echo.auth.addUser('visi')
            await user.setPasswd('foo')
            await user.addRule((True, ('foo', 'bar')))

            url = f'tcp://visi:foo@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:
                self.true(await proxy.allowed(('foo', 'bar')))
                self.false(await proxy.isadmin())
                self.false(await proxy.allowed(('hehe', 'haha')))

    async def test_cell_hive(self):

        # test out built in cell auth
        async with self.getTestDmon(mirror='cellauth') as dmon:
            host, port = dmon.addr
            url = f'tcp://root:secretsauce@{host}:{port}/echo00'
            async with await s_telepath.openurl(url) as proxy:

                await proxy.setHiveKey(('foo', 'bar'), [1, 2, 3, 4])
                self.eq([1, 2, 3, 4], await proxy.getHiveKey(('foo', 'bar')))
                self.isin('foo', await proxy.listHiveKey())
                self.eq(['bar'], await proxy.listHiveKey(('foo', )))
                await proxy.popHiveKey(('foo', 'bar'))
                self.eq([], await proxy.listHiveKey(('foo', )))

    async def test_cell_unix_sock(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy() as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))
