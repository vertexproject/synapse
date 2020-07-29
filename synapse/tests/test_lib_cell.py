import os
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
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

                visi = await echo.auth.addUser('visi')
                await visi.setPasswd('foo')
                await visi.addRule((True, ('foo', 'bar')))
                testrole = await echo.auth.addRole('testrole')
                await echo.auth.addRole('privrole')
                await visi.grant(testrole.iden)

                visi_url = f'tcp://visi:foo@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(visi_url) as proxy:  # type: EchoAuthApi
                    self.true(await proxy.allowed(('foo', 'bar')))
                    self.false(await proxy.isadmin())
                    self.false(await proxy.allowed(('hehe', 'haha')))

                    # User can get authinfo data for themselves and their roles
                    uatm = await proxy.getUserInfo('visi')
                    self.eq(uatm.get('name'), 'visi')
                    self.eq(uatm.get('iden'), visi.iden)
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
                    await visi.addRule((True, ('hive:set', 'foo', 'bar')))
                    await visi.addRule((True, ('hive:get', 'foo', 'bar')))
                    await visi.addRule((True, ('hive:pop', 'foo', 'bar')))

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
                    await proxy.setUserPasswd(visi.iden, 'foobar')
                    # non admin visi user cannot change root user pass
                    with self.raises(s_exc.AuthDeny):
                        await proxy.setUserPasswd(echo.auth.rootuser.iden, 'coolstorybro')
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
                    await proxy.setUserPasswd(visi.iden, 'foo')
                    visi_url = f'tcp://visi:foo@127.0.0.1:{port}/echo00'

                    await proxy.setUserLocked(visi.iden, True)
                    info = await proxy.getUserInfo('visi')
                    self.true(info.get('locked'))
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserLocked(visi.iden, False)
                    info = await proxy.getUserInfo('visi')
                    self.false(info.get('locked'))
                    async with await s_telepath.openurl(visi_url) as visi_proxy:
                        self.false(await visi_proxy.isadmin())

                async with await s_telepath.openurl(root_url) as proxy:  # type: EchoAuthApi

                    await self.asyncraises(s_exc.NoSuchUser,
                                           proxy.setUserArchived('newp', True))
                    await proxy.setUserArchived(visi.iden, True)
                    info = await proxy.getUserInfo('visi')
                    self.true(info.get('archived'))
                    self.true(info.get('locked'))
                    users = await proxy.getAuthUsers()
                    self.len(1, users)
                    users = await proxy.getAuthUsers(archived=True)
                    self.len(2, users)
                    await self.asyncraises(s_exc.AuthDeny,
                                           s_telepath.openurl(visi_url))

                    await proxy.setUserArchived(visi.iden, False)
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
                    self.isin(rule, visi.info.get('rules'))
                    await proxy.delUserRule(visi.iden, rule)
                    self.notin(rule, visi.info.get('rules'))
                    # Removing a non-existing rule by *rule* has no consequence
                    await proxy.delUserRule(visi.iden, rule)

                    rule = visi.info.get('rules')[0]
                    self.isin(rule, visi.info.get('rules'))
                    await proxy.delUserRule(visi.iden, rule)
                    self.notin(rule, visi.info.get('rules'))

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

    async def test_cell_userapi(self):

        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')
            await visi.addRule((True, ('foo', 'bar')))

            async with core.getLocalProxy() as proxy:

                self.none(await proxy.tryUserPasswd('newpnewp', 'newp'))
                self.none(await proxy.tryUserPasswd('visi', 'newp'))
                udef = await proxy.tryUserPasswd('visi', 'secret')
                self.eq(visi.iden, udef['iden'])

                self.true(await proxy.isUserAllowed(visi.iden, ('foo', 'bar')))
                self.false(await proxy.isUserAllowed(visi.iden, ('hehe', 'haha')))
                self.false(await proxy.isUserAllowed('newpnewp', ('hehe', 'haha')))

                await proxy.setUserProfInfo(visi.iden, 'hehe', 'haha')
                self.eq('haha', await proxy.getUserProfInfo(visi.iden, 'hehe'))
                self.eq('haha', (await proxy.getUserProfile(visi.iden))['hehe'])

    async def test_longpath(self):
        # This is similar to the DaemonTest::test_unixsock_longpath
        # but exercises the long-path failure inside of the cell's daemon
        # instead.
        with self.getTestDir() as dirn:
            extrapath = 108 * 'A'
            longdirn = s_common.genpath(dirn, extrapath)
            with self.getAsyncLoggerStream('synapse.lib.cell', 'LOCAL UNIX SOCKET WILL BE UNAVAILABLE') as stream:
                async with self.getTestCell(s_cell.Cell, dirn=longdirn) as cell:
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

                    visi = await prox.addUser('visi')

                    self.true(await prox.setCellUser(visi['iden']))
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

        # Do a full hive dump/load
        with self.getTestDir() as dirn:
            dir0 = s_common.genpath(dirn, 'cell00')
            dir1 = s_common.genpath(dirn, 'cell01')
            async with await s_cell.Cell.anit(dir0, {'auth:passwd': 'root'}) as cell00:
                await cell00.hive.set(('beeps',), [1, 2, 'three'])

                tree = await cell00.saveHiveTree()
                s_common.yamlsave(tree, dir1, 'hiveboot.yaml')
                with s_common.genfile(dir1, 'cell.guid') as fd:
                    _ = fd.write(cell00.iden.encode())

            async with await s_cell.Cell.anit(dir1) as cell01:
                resp = await cell01.hive.get(('beeps',))
                self.isinstance(resp, tuple)
                self.eq(resp, (1, 2, 'three'))

            self.eq(cell00.iden, cell01.iden)

    async def test_cell_dyncall(self):

        with self.getTestDir() as dirn:
            async with await EchoAuth.anit(dirn) as cell, cell.getLocalProxy() as prox:
                cell.dynitems['self'] = cell
                self.eq(42, await prox.dyncall('self', s_common.todo('answer')))
                await self.asyncraises(s_exc.BadArg, prox.dyncall('self', s_common.todo('badanswer')))

                self.eq([1, 2], await s_t_utils.alist(await prox.dyncall('self', s_common.todo('stream'))))

                todo = s_common.todo('stream', doraise=True)
                await self.agenraises(s_exc.BadTime, await prox.dyncall('self', todo))

    async def test_cell_promote(self):

        with self.getTestDir() as dirn:
            async with await s_cell.Cell.anit(dirn) as cell:
                async with cell.getLocalProxy() as proxy:
                    with self.raises(s_exc.BadConfValu):
                        await proxy.promote()

    async def test_cell_nexuschanges(self):

        with self.getTestDir() as dirn:

            dir0 = s_common.genpath(dirn, 'cell00')
            dir1 = s_common.genpath(dirn, 'cell01')

            async def coro(prox, offs):
                retn = []
                yielded = False
                async for offset, data in prox.getNexusChanges(offs):
                    yielded = True
                    nexsiden, act, args, kwargs, meta = data
                    if nexsiden == 'auth:auth' and act == 'user:add':
                        retn.append(args)
                        break
                return yielded, retn

            conf = {
                'nexslog:en': True,
                'nexslog:async': True,
                'dmon:listen': 'tcp://127.0.0.1:0/',
                'https:port': 0,
            }
            async with await s_cell.Cell.anit(dir0, conf=conf) as cell00, \
                    cell00.getLocalProxy() as prox00:

                self.true(cell00.nexsroot.map_async)
                self.true(cell00.nexsroot.donexslog)

                await prox00.addUser('test')
                self.true(await prox00.getNexsIndx() > 0)

                # We should have a set of auth:auth changes to find
                task = cell00.schedCoro(coro(prox00, 0))
                yielded, data = await asyncio.wait_for(task, 6)
                self.true(yielded)
                usernames = [args[1] for args in data]
                self.eq(usernames, ['test'])

            # Disable change logging for this cell.
            conf = {'nexslog:en': False}
            async with await s_cell.Cell.anit(dir1, conf=conf) as cell01, \
                    cell01.getLocalProxy() as prox01:
                self.false(cell01.nexsroot.donexslog)

                await prox01.addUser('test')

                task = cell01.schedCoro(coro(prox01, 0))
                yielded, data = await asyncio.wait_for(task, 6)
                self.false(yielded)
                self.eq(data, [])

    async def test_cell_authv2(self):

        async with self.getTestCore() as core:

            visi = await core.addUser('visi')
            ninjas = await core.addRole('ninjas')

            async with core.getLocalProxy() as proxy:

                self.len(2, await proxy.getUserDefs())
                self.len(2, await proxy.getRoleDefs())

                self.nn(await proxy.getUserDef(visi['iden']))
                self.nn(await proxy.getRoleDef(ninjas['iden']))

                await proxy.setUserRules(visi['iden'], ((True, ('foo', 'bar')),))
                await proxy.setRoleRules(ninjas['iden'], ((True, ('hehe', 'haha')),))

                await proxy.addUserRole(visi['iden'], ninjas['iden'])
                await proxy.setUserEmail(visi['iden'], 'visi@vertex.link')

                visi = await proxy.getUserDefByName('visi')
                self.eq(visi['email'], 'visi@vertex.link')

                self.true(await proxy.isUserAllowed(visi['iden'], ('foo', 'bar')))
                self.true(await proxy.isUserAllowed(visi['iden'], ('hehe', 'haha')))

                with self.raises(s_exc.BadArg):
                    await proxy.delUserRole(visi['iden'], core.auth.allrole.iden)

                with self.raises(s_exc.BadArg):
                    await proxy.delRole(core.auth.allrole.iden)

                with self.raises(s_exc.BadArg):
                    await proxy.delUser(core.auth.rootuser.iden)

                await proxy.delUser(visi['iden'])
                await proxy.delRole(ninjas['iden'])

    async def test_cell_diag_info(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy() as proxy:
                diag = await proxy.getDiagInfo()
                slab = diag['slabs'][0]
                self.nn(slab['path'])
                self.nn(slab['xactops'])
                self.nn(slab['mapsize'])
                self.nn(slab['readonly'])
                self.nn(slab['lockmemory'])
                self.nn(slab['recovering'])

    async def test_cell_hiveapi(self):

        async with self.getTestCore() as core:

            await core.setHiveKey(('foo', 'bar'), 10)
            await core.setHiveKey(('foo', 'baz'), 30)

            async with core.getLocalProxy() as proxy:
                self.eq((), await proxy.getHiveKeys(('lulz',)))
                self.eq((('bar', 10), ('baz', 30)), await proxy.getHiveKeys(('foo',)))

    async def test_cell_confprint(self):

        with self.withSetLoggingMock():

            with self.getTestDir() as dirn:

                conf = {
                    'dmon:listen': 'tcp://127.0.0.1:0',
                    'https:port': 0,
                }
                s_common.yamlsave(conf, dirn, 'cell.yaml')

                outp = self.getTestOutp()
                async with await s_cell.Cell.initFromArgv([dirn], outp=outp) as cell:
                    outp.expect('...cell API (telepath): tcp://127.0.0.1:0')
                    outp.expect('...cell API (https): 0')

                conf = {
                    'dmon:listen': 'tcp://127.0.0.1:0',
                    'https:port': None,
                }
                s_common.yamlsave(conf, dirn, 'cell.yaml')

                outp = self.getTestOutp()
                async with await s_cell.Cell.initFromArgv([dirn], outp=outp) as cell:
                    outp.expect('...cell API (telepath): tcp://127.0.0.1:0')
                    outp.expect('...cell API (https): disabled')
