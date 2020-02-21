import os

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

class EchoAuthApi(s_cell.CellApi):

    def isadmin(self):
        return self.user.isAdmin()

    async def icando(self, *path):
        await self._reqUserAllowed(path)
        return True

class EchoAuth(s_cell.Cell):
    cellapi = EchoAuthApi

    async def answer(self):
        return 42

    async def badanswer(self):
        raise s_exc.BadArg(mesg='ad hominem')

    async def stream(self, doraise=False):
        yield 1
        yield 2
        if doraise:
            raise s_exc.BadTime(mesg='call again later')


class CellTest(s_t_utils.SynTest):

    async def test_cell_auth(self):

        with self.getTestDir() as dirn:

            async with await EchoAuth.anit(dirn) as echo:

                echo.dmon.share('echo00', echo)
                root = await echo.auth.getUserByName('root')
                await root.setPasswd('secretsauce')

                self.eq('root', echo.getUserName(root.iden))
                self.eq('<unknown>', echo.getUserName('derp'))

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
                    self.true(await proxy.allowed(('hehe', 'haha')))

                    # Auth data is reflected in the Dmon session
                    resp = await proxy.getDmonSessions()
                    self.len(1, resp)
                    info = resp[0]
                    self.eq(info.get('items'), {None: 'synapse.tests.test_lib_cell.EchoAuthApi'})
                    self.eq(info.get('user').get('name'), 'root')
                    self.eq(info.get('user').get('iden'), root.iden)

                user = await echo.auth.addUser('visi')
                await user.setPasswd('foo')
                await user.addRule((True, ('foo', 'bar')))
                testrole = await echo.auth.addRole('testrole')
                await echo.auth.addRole('privrole')
                await user.grant('testrole')

                visi_url = f'tcp://visi:foo@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(visi_url) as proxy:  # type: EchoAuthApi
                    self.true(await proxy.allowed(('foo', 'bar')))
                    self.false(await proxy.isadmin())
                    self.false(await proxy.allowed(('hehe', 'haha')))

                    # User can get authinfo data for themselves and their roles
                    uatm = await proxy.getUserInfo('visi')
                    self.eq(uatm.get('name'), 'visi')
                    self.eq(uatm.get('iden'), user.iden)
                    self.eq(uatm.get('roles'), ('all', 'testrole'))
                    self.eq(uatm.get('rules'), ((True, ('foo', 'bar')),))
                    ratm = await proxy.getRoleInfo('testrole')
                    self.eq(ratm.get('name'), 'testrole')
                    self.eq(ratm.get('iden'), testrole.iden)

                    # User cannot get authinfo for other items since they are
                    # not an admin or do not have those roles.
                    await self.asyncraises(s_exc.AuthDeny, proxy.getUserInfo('root'))
                    await self.asyncraises(s_exc.AuthDeny, proxy.getRoleInfo('privrole'))

                    # Basic auth checks
                    self.true(await proxy.icando('foo', 'bar'))
                    await self.asyncraises(s_exc.AuthDeny, proxy.icando('foo', 'newp'))

                    # happy path perms
                    await user.addRule((True, ('hive:set', 'foo', 'bar')))
                    await user.addRule((True, ('hive:get', 'foo', 'bar')))
                    await user.addRule((True, ('hive:pop', 'foo', 'bar')))

                    val = await echo.setHiveKey(('foo', 'bar'), 'thefirstval')
                    self.eq(None, val)

                    # check that we get the old val back
                    val = await echo.setHiveKey(('foo', 'bar'), 'wootisetit')
                    self.eq('thefirstval', val)

                    val = await echo.getHiveKey(('foo', 'bar'))
                    self.eq('wootisetit', val)

                    val = await echo.popHiveKey(('foo', 'bar'))
                    self.eq('wootisetit', val)

                    val = await echo.setHiveKey(('foo', 'bar', 'baz'), 'a')
                    val = await echo.setHiveKey(('foo', 'bar', 'faz'), 'b')
                    val = await echo.setHiveKey(('foo', 'bar', 'haz'), 'c')
                    val = await echo.listHiveKey(('foo', 'bar'))
                    self.eq(('baz', 'faz', 'haz'), val)

                    # visi user can change visi user pass
                    await proxy.setUserPasswd('visi', 'foobar')
                    # non admin visi user cannot change root user pass
                    with self.raises(s_exc.AuthDeny):
                        await proxy.setUserPasswd('root', 'coolstorybro')
                    # cannot change a password for a non existent user
                    with self.raises(s_exc.NoSuchUser):
                        await proxy.setUserPasswd('newp', 'new[')

                # New password works
                visi_url = f'tcp://visi:foobar@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(visi_url) as proxy:  # type: EchoAuthApi
                    info = await proxy.getCellUser()
                    self.eq(info.get('name'), 'visi')

                async with await s_telepath.openurl(root_url) as proxy:  # type: EchoAuthApi

                    # root user can change visi user pass
                    await proxy.setUserPasswd('visi', 'foo')
                    visi_url = f'tcp://visi:foo@127.0.0.1:{port}/echo00'

                    await proxy.setUserLocked('visi', True)
                    info = await proxy.getUserInfo('visi')
                    self.true(info.get('locked'))
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserLocked('visi', False)
                    info = await proxy.getUserInfo('visi')
                    self.false(info.get('locked'))
                    async with await s_telepath.openurl(visi_url) as visi_proxy:
                        self.false(await visi_proxy.isadmin())

                async with await s_telepath.openurl(root_url) as proxy:  # type: EchoAuthApi

                    await self.asyncraises(s_exc.NoSuchUser,
                                           proxy.setUserArchived('newp', True))
                    await proxy.setUserArchived('visi', True)
                    info = await proxy.getUserInfo('visi')
                    self.true(info.get('archived'))
                    self.true(info.get('locked'))
                    users = await proxy.getAuthUsers()
                    self.len(1, users)
                    users = await proxy.getAuthUsers(archived=True)
                    self.len(2, users)
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserArchived('visi', False)
                    info = await proxy.getUserInfo('visi')
                    self.false(info.get('archived'))
                    self.true(info.get('locked'))
                    users = await proxy.getAuthUsers(archived=True)
                    self.len(2, users)

                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                await echo.setHiveKey(('foo', 'bar'), [1, 2, 3, 4])
                self.eq([1, 2, 3, 4], await echo.getHiveKey(('foo', 'bar')))
                self.isin('foo', await echo.listHiveKey())
                self.eq(['bar'], await echo.listHiveKey(('foo',)))
                await echo.popHiveKey(('foo', 'bar'))
                self.eq([], await echo.listHiveKey(('foo',)))

                # Ensure we can delete a rule by its item and index position
                async with echo.getLocalProxy() as proxy:  # type: EchoAuthApi
                    rule = (True, ('hive:set', 'foo', 'bar'))
                    self.isin(rule, user.info.get('rules'))
                    await proxy.delUserRule('visi', rule)
                    self.notin(rule, user.info.get('rules'))
                    # Removing a non-existing rule by *rule* has no consequence
                    await proxy.delUserRule('visi', rule)

                    rule = user.info.get('rules')[0]
                    self.isin(rule, user.info.get('rules'))
                    await proxy.delUserRule('visi', rule)
                    self.notin(rule, user.info.get('rules'))

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

    async def test_cell_authpasswd(self):
        conf = {
            'auth:passwd': 'cottoncandy',
        }
        pconf = {'user': 'root', 'passwd': 'cottoncandy'}

        with self.getTestDir() as dirn:

            s_common.yamlsave(conf, dirn, 'cell.yaml')
            async with await EchoAuth.anit(dirn) as echo:

                # start a regular network listener so we can auth
                host, port = await echo.dmon.listen('tcp://127.0.0.1:0/')
                async with await s_telepath.openurl(f'tcp://127.0.0.1:{port}/', **pconf) as proxy:

                    self.true(await proxy.isadmin())
                    self.true(await proxy.allowed(('hehe', 'haha')))

                url = f'tcp://root@127.0.0.1:{port}/'
                await self.asyncraises(s_exc.AuthDeny, s_telepath.openurl(url))

            os.unlink(s_common.genpath(dirn, 'cell.yaml'))
            # Pass the auth data in via conf directly
            async with await EchoAuth.anit(dirn,
                                           conf={'auth:passwd': 'pennywise'}) as echo:

                # start a regular network listener so we can auth
                host, port = await echo.dmon.listen('tcp://127.0.0.1:0/')
                url = f'tcp://root:pennywise@127.0.0.1:{port}/'
                async with await s_telepath.openurl(url) as proxy:

                    self.true(await proxy.isadmin())
                    self.true(await proxy.allowed(('hehe', 'haha')))

        # Ensure the cell and its auth have been fini'd
        self.true(echo.isfini)
        self.true(echo.auth.isfini)
        root = await echo.auth.getUserByName('root')
        self.true(root.isfini)

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
                    snfo = await prox.getDmonSessions()
                    self.len(1, snfo)
                    self.eq(snfo[0].get('user').get('name'), 'root')

                    with self.raises(s_exc.NoSuchUser):
                        await prox.setCellUser(s_common.guid())

                    user = await prox.addAuthUser('visi')

                    self.true(await prox.setCellUser(user['iden']))
                    self.eq('visi', (await prox.getCellUser())['name'])

                    # setCellUser propagates his change to the Daemon Sess object.
                    # But we have to use the daemon directly to get that info
                    snfo = await cell.dmon.getSessInfo()
                    self.len(1, snfo)
                    self.eq(snfo[0].get('user').get('name'), 'visi')

                    with self.raises(s_exc.AuthDeny):
                        await prox.setCellUser(s_common.guid())

    async def test_cell_hiveboot(self):

        with self.getTestDir() as dirn:

            tree = {
                'kids': {
                    'hehe': {'value': 'haha'},
                }
            }

            bootpath = os.path.join(dirn, 'hiveboot.yaml')

            s_common.yamlsave(tree, bootpath)

            async with await s_cell.Cell.anit(dirn) as cell:
                self.eq('haha', await cell.hive.get(('hehe',)))

            # test that the file does not load again
            tree['kids']['redbaloons'] = {'value': 99}
            s_common.yamlsave(tree, bootpath)

            async with await s_cell.Cell.anit(dirn) as cell:
                self.none(await cell.hive.get(('redbaloons',)))

    async def test_cell_dyncall(self):

        with self.getTestDir() as dirn:
            async with await EchoAuth.anit(dirn) as cell, cell.getLocalProxy() as prox:
                cell.dynitems['self'] = cell
                self.eq(42, await prox.dyncall('self', s_common.todo('answer')))
                await self.asyncraises(s_exc.BadArg, prox.dyncall('self', s_common.todo('badanswer')))

                self.eq([1, 2], await s_t_utils.alist(await prox.dyncall('self', s_common.todo('stream'))))

                todo = s_common.todo('stream', doraise=True)
                await self.agenraises(s_exc.BadTime, await prox.dyncall('self', todo))
