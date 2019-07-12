
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

class EchoAuthApi(s_cell.CellApi):

    def isadmin(self):
        return self.user.admin

    async def icando(self, *path):
        await self._reqUserAllowed(*path)
        return True

class EchoAuth(s_cell.Cell):
    cellapi = EchoAuthApi

class CellTest(s_t_utils.SynTest):

    async def test_cell_auth(self):

        with self.getTestDir() as dirn:

            async with await EchoAuth.anit(dirn) as echo:

                echo.insecure = False
                echo.dmon.share('echo00', echo)
                root = echo.auth.getUserByName('root')
                await root.setPasswd('secretsauce')

                host, port = await echo.dmon.listen('tcp://127.0.0.1:0/')

                url = f'tcp://127.0.0.1:{port}/echo00'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

                url = f'tcp://fake@127.0.0.1:{port}/echo00'
                await self.asyncraises(s_exc.NoSuchUser, s_telepath.openurl(url))

                url = f'tcp://root@127.0.0.1:{port}/echo00'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

                url = f'tcp://root:newpnewp@127.0.0.1:{port}/echo00'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

                root_url = f'tcp://root:secretsauce@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(root_url) as proxy:
                    self.true(await proxy.isadmin())
                    self.true(await proxy.allowed('hehe', 'haha'))

                user = await echo.auth.addUser('visi')
                await user.setPasswd('foo')
                await user.addRule((True, ('foo', 'bar')))

                visi_url = f'tcp://visi:foo@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(visi_url) as proxy:  # type: EchoAuthApi
                    self.true(await proxy.allowed('foo', 'bar'))
                    self.false(await proxy.isadmin())
                    self.false(await proxy.allowed('hehe', 'haha'))

                    self.true(await proxy.icando('foo', 'bar'))
                    await self.asyncraises(s_exc.AuthDeny, proxy.icando('foo', 'newp'))

                    await self.asyncraises(s_exc.AuthDeny, proxy.listHiveKey(('faz',)))
                    await self.asyncraises(s_exc.AuthDeny, proxy.getHiveKey(('faz',)))
                    await self.asyncraises(s_exc.AuthDeny, proxy.setHiveKey(('faz',), 'bar'))
                    await self.asyncraises(s_exc.AuthDeny, proxy.popHiveKey(('faz',)))

                    # happy path perms
                    await user.addRule((True, ('hive:set', 'foo', 'bar')))
                    await user.addRule((True, ('hive:get', 'foo', 'bar')))
                    await user.addRule((True, ('hive:pop', 'foo', 'bar')))

                    val = await proxy.setHiveKey(('foo', 'bar'), 'thefirstval')
                    self.eq(None, val)

                    # check that we get the old val back
                    val = await proxy.setHiveKey(('foo', 'bar'), 'wootisetit')
                    self.eq('thefirstval', val)

                    val = await proxy.getHiveKey(('foo', 'bar'))
                    self.eq('wootisetit', val)

                    val = await proxy.popHiveKey(('foo', 'bar'))
                    self.eq('wootisetit', val)

                    val = await proxy.setHiveKey(('foo', 'bar', 'baz'), 'a')
                    val = await proxy.setHiveKey(('foo', 'bar', 'faz'), 'b')
                    val = await proxy.setHiveKey(('foo', 'bar', 'haz'), 'c')
                    val = await proxy.listHiveKey(('foo', 'bar'))
                    self.eq(('baz', 'faz', 'haz'), val)

                async with await s_telepath.openurl(root_url) as proxy:  # type: EchoAuthApi

                    await proxy.setUserLocked('visi', True)
                    info = await proxy.getAuthInfo('visi')
                    self.true(info[1].get('locked'))
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserLocked('visi', False)
                    info = await proxy.getAuthInfo('visi')
                    self.false(info[1].get('locked'))
                    async with await s_telepath.openurl(visi_url) as visi_proxy:
                        self.false(await visi_proxy.isadmin())

                async with await s_telepath.openurl(root_url) as proxy:  # type: EchoAuthApi

                    await self.asyncraises(s_exc.NoSuchUser,
                                           proxy.setUserArchived('newp', True))
                    await proxy.setUserArchived('visi', True)
                    info = await proxy.getAuthInfo('visi')
                    self.true(info[1].get('archived'))
                    self.true(info[1].get('locked'))
                    users = await proxy.getAuthUsers()
                    self.len(1, users)
                    users = await proxy.getAuthUsers(archived=True)
                    self.len(2, users)
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserArchived('visi', False)
                    info = await proxy.getAuthInfo('visi')
                    self.false(info[1].get('archived'))
                    self.true(info[1].get('locked'))
                    users = await proxy.getAuthUsers(archived=True)
                    self.len(2, users)

                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                async with echo.getLocalProxy() as proxy:  # type: EchoAuthApi

                    await proxy.setHiveKey(('foo', 'bar'), [1, 2, 3, 4])
                    self.eq([1, 2, 3, 4], await proxy.getHiveKey(('foo', 'bar')))
                    self.isin('foo', await proxy.listHiveKey())
                    self.eq(['bar'], await proxy.listHiveKey(('foo', )))
                    await proxy.popHiveKey(('foo', 'bar'))
                    self.eq([], await proxy.listHiveKey(('foo', )))

                # Ensure we can delete a rule by its item and index position
                async with echo.getLocalProxy() as proxy:  # type: EchoAuthApi
                    rule = (True, ('hive:set', 'foo', 'bar'))
                    self.isin(rule, user.rules)
                    await proxy.delAuthRule('visi', rule)
                    self.notin(rule, user.rules)
                    # Removing a non-existing rule by *rule* has no consequence
                    await proxy.delAuthRule('visi', rule)

                    rule = user.rules[0]
                    self.isin(rule, user.rules)
                    await proxy.delAuthRuleIndx('visi', 0)
                    self.notin(rule, user.rules)
                    # Sad path around cell deletion
                    await self.asyncraises(s_exc.BadArg, proxy.delAuthRuleIndx('visi', -1))
                    await self.asyncraises(s_exc.BadArg, proxy.delAuthRuleIndx('visi', 1000000))

    async def test_cell_unix_sock(self):

        async with self.getTestCore() as core:
            # This directs the connection through the cell:// handler.
            async with core.getLocalProxy() as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))

        # Explicit use of the unix:// handler
        async with self.getTestCore() as core:
            dirn = core.dirn
            url = f'unix://{dirn}/sock:cortex'
            async with await s_telepath.openurl(url) as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))
                iden = await prox.getCellIden()

            url = f'unix://{dirn}/sock:*'
            async with await s_telepath.openurl(url) as prox:
                self.eq(iden, await prox.getCellIden())

    async def test_cell_nonstandard_admin(self):
        boot = {
            'auth:admin': 'pennywise:cottoncandy',
            'type': 'echoauth',
        }
        pconf = {'user': 'pennywise', 'passwd': 'cottoncandy'}

        with self.getTestDir('cellauth') as dirn:

            s_common.yamlsave(boot, dirn, 'boot.yaml')
            async with await EchoAuth.anit(dirn) as echo:

                echo.insecure = False

                # start a regular network listener so we can auth
                host, port = await echo.dmon.listen('tcp://127.0.0.1:0/')
                async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}/', **pconf) as proxy:

                    self.true(await proxy.isadmin())
                    self.true(await proxy.allowed('hehe', 'haha'))

                url = f'tcp://root@127.0.0.1:{port}/'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

        # Ensure the cell and its auth have been fini'd
        self.true(echo.isfini)
        self.true(echo.auth.isfini)
        self.true(echo.auth.getUserByName('root').isfini)
        self.true(echo.auth.getUserByName('pennywise').isfini)

    async def test_longpath(self):
        # This is similar to the DaemonTest::test_unixsock_longpath
        # but exercises the long-path failure inside of the cell's daemon
        # instead.
        with self.getTestDir() as dirn:
            extrapath = 108 * 'A'
            longdirn = s_common.genpath(dirn, extrapath)
            with self.getAsyncLoggerStream('synapse.lib.cell', 'LOCAL UNIX SOCKET WILL BE UNAVAILABLE') as stream:
                async with await s_cell.Cell.anit(longdirn) as cell:
                    self.none(cell.dmon.addr)
                self.true(await stream.wait(1))

    async def test_cell_setuser(self):

        with self.getTestDir() as dirn:

            async with await s_cell.Cell.anit(dirn) as cell:

                async with cell.getLocalProxy() as prox:

                    self.eq('root', (await prox.getCellUser())['name'])

                    with self.raises(s_exc.NoSuchUser):
                        await prox.setCellUser(s_common.guid())

                    user = await prox.addAuthUser('visi')

                    self.true(await prox.setCellUser(user['iden']))
                    self.eq('visi', (await prox.getCellUser())['name'])

                    with self.raises(s_exc.AuthDeny):
                        await prox.setCellUser(s_common.guid())
