import os
import sys
import time
import signal
import asyncio
import tarfile
import multiprocessing

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.link as s_link
import synapse.lib.version as s_version
import synapse.lib.hiveauth as s_hiveauth
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.crypto.passwd as s_passwd

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

# Defective versions of spawned backup processes
def _sleeperProc(pipe, srcdir, dstdir, lmdbpaths, logconf):
    time.sleep(3.0)

def _sleeper2Proc(pipe, srcdir, dstdir, lmdbpaths, logconf):
    time.sleep(2.0)

def _exiterProc(pipe, srcdir, dstdir, lmdbpaths, logconf):
    pipe.send('captured')
    sys.exit(1)

def _backupSleep(path, linkinfo):
    time.sleep(3.0)

async def _doEOFBackup(path):
    return

async def _iterBackupEOF(path, linkinfo):
    link = await s_link.fromspawn(linkinfo)
    await s_daemon.t2call(link, _doEOFBackup, (path,), {})
    link.writer.write_eof()
    await link.fini()

def _backupEOF(path, linkinfo):
    asyncio.run(_iterBackupEOF(path, linkinfo))

def lock_target(dirn, evt1):  # pragma: no cover
    '''
    Function to make a cell in a directory and wait to be shut down.
    Used as a Process target for advisory locking tests.

    Args:
        dirn (str): Cell directory.
        evt1 (multiprocessing.Event): event to twiddle
    '''
    async def main():
        cell = await s_cell.Cell.anit(dirn)
        await cell.addSignalHandlers()
        evt1.set()
        await cell.waitfini(timeout=60)

    asyncio.run(main())
    sys.exit(137)

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

async def altAuthCtor(cell):
    authconf = cell.conf.get('auth:conf')
    assert authconf['foo'] == 'bar'
    authconf['baz'] = 'faz'
    return await s_cell.Cell._initCellHiveAuth(cell)

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

                # setRoles() allows arbitrary role ordering
                extra_role = await echo.auth.addRole('extrarole')
                await visi.setRoles((extra_role.iden, testrole.iden, echo.auth.allrole.iden))
                visi_url = f'tcp://visi:foobar@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(visi_url) as proxy:  # type: EchoAuthApi
                    uatm = await proxy.getUserInfo('visi')
                    self.eq(uatm.get('roles'), ('extrarole', 'testrole', 'all',))

                    # setRoles are wholesale replacements
                    await visi.setRoles((echo.auth.allrole.iden, testrole.iden))
                    uatm = await proxy.getUserInfo('visi')
                    self.eq(uatm.get('roles'), ('all', 'testrole'))

                # coverage test - nops short circuit
                await visi.setRoles((echo.auth.allrole.iden, testrole.iden))

                # grants must have the allrole in place
                with self.raises(s_exc.BadArg):
                    await visi.setRoles((extra_role.iden, testrole.iden))

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
                self.true(await prox.isCellActive())

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
                self.false(await proxy.isRoleAllowed('newpnewp', ('foo', 'bar')))

                await proxy.setUserProfInfo(visi.iden, 'hehe', 'haha')
                self.eq('haha', await proxy.getUserProfInfo(visi.iden, 'hehe'))
                await proxy.setUserProfInfo(visi.iden, 'woah', 'dude')
                self.eq('haha', (await proxy.getUserProfile(visi.iden))['hehe'])
                self.eq('haha', await proxy.popUserProfInfo(visi.iden, 'hehe'))
                self.eq('newp', await proxy.popUserProfInfo(visi.iden, 'hehe', default='newp'))
                self.eq({'woah': 'dude'}, await proxy.getUserProfile(visi.iden))

                iden = s_common.guid(('foo', 101))
                udef = await proxy.addUser('foo', iden=iden)
                self.eq(udef.get('iden'), iden)

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

        async with self.getTestCell(s_cell.Cell) as cell:

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

            async with self.getTestCell(s_cell.Cell, dirn=dirn) as cell:
                self.eq('haha', await cell.hive.get(('hehe',)))

            # test that the file does not load again
            tree['kids']['redballoons'] = {'value': 99}
            s_common.yamlsave(tree, bootpath)

            async with self.getTestCell(s_cell.Cell, dirn=dirn) as cell:
                self.none(await cell.hive.get(('redballoons',)))

        # Do a full hive dump/load
        with self.getTestDir() as dirn:
            dir0 = s_common.genpath(dirn, 'cell00')
            dir1 = s_common.genpath(dirn, 'cell01')
            async with self.getTestCell(s_cell.Cell, dirn=dir0, conf={'auth:passwd': 'root'}) as cell00:
                await cell00.hive.set(('beeps',), [1, 2, 'three'])

                tree = await cell00.saveHiveTree()
                s_common.yamlsave(tree, dir1, 'hiveboot.yaml')
                with s_common.genfile(dir1, 'cell.guid') as fd:
                    _ = fd.write(cell00.iden.encode())

            async with self.getTestCell(s_cell.Cell, dirn=dir1) as cell01:
                resp = await cell01.hive.get(('beeps',))
                self.isinstance(resp, tuple)
                self.eq(resp, (1, 2, 'three'))

            self.eq(cell00.iden, cell01.iden)

    async def test_cell_getinfo(self):
        async with self.getTestCore() as cell:
            cell.COMMIT = 'mycommit'
            cell.VERSION = (1, 2, 3)
            cell.VERSTRING = '1.2.3'
            async with cell.getLocalProxy() as prox:
                info = await prox.getCellInfo()
                # Cell information
                cnfo = info.get('cell')
                snfo = info.get('synapse')
                self.eq(cnfo.get('commit'), 'mycommit')
                self.eq(cnfo.get('version'), (1, 2, 3))
                self.eq(cnfo.get('verstring'), '1.2.3')
                self.eq(cnfo.get('type'), 'cortex')
                self.true(cnfo.get('active'))
                # A Cortex populated cellvers
                self.isin('cortex:defaults', cnfo.get('cellvers', {}))

                # Synapse information
                self.eq(snfo.get('version'), s_version.version)
                self.eq(snfo.get('verstring'), s_version.verstring),
                self.eq(snfo.get('commit'), s_version.commit)

    async def test_cell_dyncall(self):

        with self.getTestDir() as dirn:
            async with await EchoAuth.anit(dirn) as cell, cell.getLocalProxy() as prox:
                cell.dynitems['self'] = cell
                self.eq(42, await prox.dyncall('self', s_common.todo('answer')))
                await self.asyncraises(s_exc.BadArg, prox.dyncall('self', s_common.todo('badanswer')))

                self.eq([1, 2], await s_t_utils.alist(await prox.dyncall('self', s_common.todo('stream'))))

                todo = s_common.todo('stream', doraise=True)
                await self.agenraises(s_exc.BadTime, await prox.dyncall('self', todo))

                items = []
                todo = s_common.todo('stream', doraise=False)
                async for item in prox.dyniter('self', todo):
                    items.append(item)
                self.eq(items, [1, 2])

                # Sad path
                with self.raises(s_exc.NoSuchIden):
                    await cell.dyncall('newp', s_common.todo('getCellInfo'))
                with self.raises(s_exc.NoSuchIden):
                    async for _ in cell.dyniter('newp', s_common.todo('getCellInfo')):
                        pass

    async def test_cell_promote(self):

        async with self.getTestCell(s_cell.Cell) as cell:
            async with cell.getLocalProxy() as proxy:
                with self.raises(s_exc.BadConfValu):
                    await proxy.promote()

    async def test_cell_anon(self):

        conf = {'auth:anon': 'anon'}
        async with self.getTestCell(s_cell.Cell, conf=conf) as cell:
            anon = await cell.auth.addUser('anon')
            await cell.auth.rootuser.setPasswd('secret')
            host, port = await cell.dmon.listen('tcp://127.0.0.1:0')
            async with await s_telepath.openurl('tcp://127.0.0.1/', port=port) as prox:
                info = await prox.getCellUser()
                self.eq(anon.iden, info.get('iden'))

            await anon.setLocked(True)
            with self.raises(s_exc.AuthDeny):
                await s_telepath.openurl('tcp://127.0.0.1/', port=port)

            await cell.auth.delUser(anon.iden)
            with self.raises(s_exc.AuthDeny):
                await s_telepath.openurl('tcp://127.0.0.1/', port=port)

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
            async with self.getTestCell(s_cell.Cell, dirn=dir0, conf=conf) as cell00, \
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
            async with self.getTestCell(s_cell.Cell, dirn=dir1, conf=conf) as cell01, \
                    cell01.getLocalProxy() as prox01:
                self.false(cell01.nexsroot.donexslog)

                await prox01.addUser('test')

                task = cell01.schedCoro(coro(prox01, 0))
                yielded, data = await asyncio.wait_for(task, 6)
                self.false(yielded)
                self.eq(data, [])

    async def test_cell_nexusenable(self):

        with self.getTestDir() as dirn:

            conf = {'nexslog:en': False}
            async with self.getTestCell(s_cell.Cell, dirn=dirn, conf=conf) as cell:
                self.eq(0, await cell.getNexsIndx())
                await cell.addUser('test00')
                self.eq(2, await cell.getNexsIndx())

            # create a first entry that will be greater than the slab starting index
            conf = {'nexslog:en': True}
            async with self.getTestCell(s_cell.Cell, dirn=dirn, conf=conf) as cell:
                self.eq(2, await cell.getNexsIndx())
                await cell.addUser('test01')
                self.eq(4, await cell.getNexsIndx())

            # restart checks seqn consistency
            conf = {'nexslog:en': True}
            async with self.getTestCell(s_cell.Cell, dirn=dirn, conf=conf) as cell:
                self.eq(4, await cell.getNexsIndx())
                await cell.addUser('test02')
                self.eq(6, await cell.getNexsIndx())

    async def test_cell_nexuscull(self):

        with self.getTestDir() as dirn, self.withNexusReplay():

            dirn00 = s_common.genpath(dirn, 'cell00')
            dirn01 = s_common.genpath(dirn, 'cell01')

            conf = {
                'nexslog:en': True,
            }
            async with self.getTestCell(s_cell.Cell, dirn=dirn00, conf=conf) as cell:

                async with cell.getLocalProxy() as prox:

                    # test backup running
                    ind = await prox.getNexsIndx()
                    cell.backuprunning = True
                    await self.asyncraises(s_exc.SlabInUse, prox.rotateNexsLog())
                    await self.asyncraises(s_exc.SlabInUse, prox.cullNexsLog(0))
                    await self.asyncraises(s_exc.SlabInUse, prox.trimNexsLog())
                    cell.backuprunning = False
                    self.eq(ind, await prox.getNexsIndx())

                    # trim can run on empty log since it generates two events
                    self.eq(0, await prox.trimNexsLog())

                    for i in range(5):
                        await prox.setHiveKey(('foo', 'bar'), i)

                    ind = await prox.getNexsIndx()
                    offs = await prox.rotateNexsLog()
                    self.eq(ind + 1, offs)
                    self.eq(ind + 1, await prox.getNexsIndx())

                    # last entry that goes into log is rotate
                    ent = await cell.nexsroot.nexslog.last()
                    self.eq('nexslog:rotate', ent[1][1])

                    # tail is empty
                    self.len(0, [x for x in cell.nexsroot.nexslog.tailseqn.iter(0)])

                    # can't cull because need >= 1 entry
                    self.false(await prox.cullNexsLog(offs))

                    # but now we've generated another nexus event from no-op cull
                    # so we can cull
                    ind = await prox.getNexsIndx()
                    self.true(await prox.cullNexsLog(offs))

                    # last entry in nexus log is cull
                    retn = await alist(cell.nexsroot.nexslog.iter(0))
                    self.len(1, retn)
                    self.eq(ind, retn[0][0])
                    self.eq('nexslog:cull', retn[0][1][1])

                    for i in range(6, 10):
                        await prox.setHiveKey(('foo', 'bar'), i)

                    # trim
                    ind = await prox.getNexsIndx()
                    self.eq(ind, await prox.trimNexsLog())
                    self.eq(ind + 2, await prox.getNexsIndx())  # two entries for rotate, cull

                    retn = await cell.nexsroot.nexslog.last()
                    self.eq('nexslog:cull', retn[1][1])

                    self.eq(ind + 2, await prox.trimNexsLog())

                    for i in range(10, 15):
                        await prox.setHiveKey(('foo', 'bar'), i)

            # nexus log exists but logging is disabled
            conf['nexslog:en'] = False
            async with self.getTestCell(s_cell.Cell, dirn=dirn00, conf=conf) as cell:

                async with cell.getLocalProxy() as prox:

                    # trim raises because we cannot cull at the rotated offset
                    await self.asyncraises(s_exc.BadConfValu, prox.trimNexsLog())

                    # we can still manually cull
                    offs = await prox.rotateNexsLog()
                    rngs = cell.nexsroot.nexslog._ranges
                    self.len(2, rngs)
                    self.true(await prox.cullNexsLog(offs - 2))

                    # rotated log still exists on disk
                    self.nn(await cell.nexsroot.nexslog.get(rngs[-1] - 1))

            # nexus fully disabled
            async with self.getTestCell(s_cell.Cell, dirn=dirn01) as cell:

                async with cell.getLocalProxy() as prox:

                    self.eq(0, await prox.getNexsIndx())

                    self.eq(0, await prox.rotateNexsLog())
                    self.false(await prox.cullNexsLog(3))
                    await self.asyncraises(s_exc.BadConfValu, prox.trimNexsLog())

    async def test_cell_nexusrotate(self):

        with self.getTestDir() as dirn, self.withNexusReplay():

            conf = {
                'nexslog:en': True,
            }
            async with await s_cell.Cell.anit(dirn, conf=conf) as cell:

                await cell.setHiveKey(('foo', 'bar'), 0)
                await cell.setHiveKey(('foo', 'bar'), 1)

                await cell.rotateNexsLog()

                self.len(2, cell.nexsroot.nexslog._ranges)
                self.eq(0, cell.nexsroot.nexslog.tailseqn.size)

            async with await s_cell.Cell.anit(dirn, conf=conf) as cell:

                self.len(2, cell.nexsroot.nexslog._ranges)
                self.eq(0, cell.nexsroot.nexslog.tailseqn.size)

                await cell.setHiveKey(('foo', 'bar'), 2)

                # new item is added to the right log
                self.len(2, cell.nexsroot.nexslog._ranges)
                self.eq(1, cell.nexsroot.nexslog.tailseqn.size)

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

    async def test_cell_system_info(self):
        with self.getTestDir() as dirn:
            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')

            async with self.getTestCore(dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:
                    info = await proxy.getSystemInfo()
                    for prop in ('osversion', 'pyversion'):
                        self.nn(info.get(prop))

                    for prop in ('volsize', 'volfree', 'celluptime', 'cellrealdisk',
                                 'cellapprdisk', 'totalmem', 'availmem'):
                        self.lt(0, info.get(prop))

            conf = {'backup:dir': backdirn}
            async with self.getTestCore(conf=conf, dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:
                    info = await proxy.getSystemInfo()
                    for prop in ('osversion', 'pyversion'):
                        self.nn(info.get(prop))

                    for prop in ('volsize', 'volfree', 'backupvolsize', 'backupvolfree', 'celluptime', 'cellrealdisk',
                                 'cellapprdisk', 'totalmem', 'availmem'):
                        self.lt(0, info.get(prop))

    async def test_cell_hiveapi(self):

        async with self.getTestCore() as core:

            await core.setHiveKey(('foo', 'bar'), 10)
            await core.setHiveKey(('foo', 'baz'), 30)

            async with core.getLocalProxy() as proxy:
                self.eq((), await proxy.getHiveKeys(('lulz',)))
                self.eq((('bar', 10), ('baz', 30)), await proxy.getHiveKeys(('foo',)))

    async def test_cell_confprint(self):

        async with self.withSetLoggingMock():

            with self.getTestDir() as dirn:

                conf = {
                    'dmon:listen': 'tcp://127.0.0.1:0',
                    'https:port': 0,
                }
                s_common.yamlsave(conf, dirn, 'cell.yaml')

                with self.getAsyncLoggerStream('synapse.lib.cell') as stream:
                    async with await s_cell.Cell.initFromArgv([dirn]):
                        pass
                stream.seek(0)
                buf = stream.read()
                self.isin('...cell API (telepath): tcp://127.0.0.1:0', buf)
                self.isin('...cell API (https): 0', buf)

                conf = {
                    'dmon:listen': None,
                    'https:port': None,
                }
                s_common.yamlsave(conf, dirn, 'cell.yaml')

                with self.getAsyncLoggerStream('synapse.lib.cell') as stream:
                    async with await s_cell.Cell.initFromArgv([dirn]):
                        pass
                stream.seek(0)
                buf = stream.read()
                self.isin(f'...cell API (telepath): cell://root@{dirn}:*', buf)
                self.isin('...cell API (https): disabled', buf)

    async def test_cell_initargv_conf(self):
        async with self.withSetLoggingMock():
            with self.setTstEnvars(SYN_CELL_NEXSLOG_EN='true',
                                   SYN_CELL_DMON_LISTEN='null',
                                   SYN_CELL_HTTPS_PORT='null',
                                   SYN_CELL_AUTH_PASSWD='notsecret',
                                   ):
                with self.getTestDir() as dirn:
                    s_common.yamlsave({'dmon:listen': 'tcp://0.0.0.0:0/',
                                       'aha:name': 'some:cell'},
                                      dirn, 'cell.yaml')
                    s_common.yamlsave({'nexslog:async': True},
                                      dirn, 'cell.mods.yaml')
                    async with await s_cell.Cell.initFromArgv([dirn, '--auth-passwd', 'secret']) as cell:
                        # config order for booting from initArgV
                        # 0) cell.mods.yaml
                        # 1) cmdline
                        # 2) envars
                        # 3) cell.yaml
                        self.true(cell.conf.reqConfValu('nexslog:en'))
                        self.true(cell.conf.reqConfValu('nexslog:async'))
                        self.none(cell.conf.reqConfValu('dmon:listen'))
                        self.none(cell.conf.reqConfValu('https:port'))
                        self.eq(cell.conf.reqConfValu('aha:name'), 'some:cell')
                        root = cell.auth.rootuser
                        self.true(await root.tryPasswd('secret'))

                # Overrides file wins out over everything else in conflicts
                with self.getTestDir() as dirn:
                    s_common.yamlsave({'nexslog:en': False}, dirn, 'cell.mods.yaml')
                    async with await s_cell.Cell.initFromArgv([dirn]) as cell:
                        self.false(cell.conf.reqConfValu('nexslog:en'))
                        # We can remove the valu from the overrides file with the pop API
                        # This is NOT reactive API which causes the whole behavior
                        # of the cell to suddenly change. This is intended to be used with
                        # code that is aware of changing configuration values.
                        cell.popCellConf('nexslog:en')
                        overrides = s_common.yamlload(dirn, 'cell.mods.yaml')
                        self.eq({}, overrides)

    async def test_initargv_failure(self):
        if not os.path.exists('/dev/null'):
            self.skip('Test requires /dev/null to exist.')

        async with self.withSetLoggingMock():
            with self.getAsyncLoggerStream('synapse.lib.cell',
                                           'Error starting cell at /dev/null') as stream:
                with self.raises(FileExistsError):
                    async with await s_cell.Cell.initFromArgv(['/dev/null']):
                        pass
                self.true(await stream.wait(timeout=6))

            # Bad configs can also cause a failure.
            with self.getTestDir() as dirn:
                with self.getAsyncLoggerStream('synapse.lib.cell',
                                               'Error while bootstrapping cell config') as stream:
                    with self.raises(s_exc.BadConfValu) as cm:
                        with self.setTstEnvars(SYN_CELL_AUTH_PASSWD="true"):  # interpreted as a yaml bool true
                            async with await s_cell.Cell.initFromArgv([dirn, ]):
                                pass
                    self.eq(cm.exception.get('name'), 'auth:passwd')
                self.true(await stream.wait(timeout=6))

    async def test_cell_backup(self):

        with self.getTestDir() as dirn:
            s_common.yamlsave({'backup:dir': dirn}, dirn, 'cell.yaml')
            with self.raises(s_exc.BadConfValu):
                async with self.getTestCore(dirn=dirn) as core:
                    pass

        with self.getTestDir() as dirn:

            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')

            conf = {'backup:dir': backdirn}
            s_common.yamlsave(conf, coredirn, 'cell.yaml')

            async with self.getTestCore(dirn=coredirn) as core:

                async with core.getLocalProxy() as proxy:

                    info = await proxy.getBackupInfo()
                    self.none(info['currduration'])
                    self.none(info['laststart'])
                    self.none(info['lastend'])
                    self.none(info['lastduration'])
                    self.none(info['lastsize'])
                    self.none(info['lastupload'])
                    self.none(info['lastexception'])

                    with self.raises(s_exc.BadArg):
                        await proxy.runBackup('../woot')

                    with mock.patch.object(s_cell.Cell, 'BACKUP_SPAWN_TIMEOUT', 0.1):
                        with mock.patch.object(s_cell.Cell, '_backupProc', staticmethod(_sleeperProc)):
                            await self.asyncraises(s_exc.SynErr, proxy.runBackup())

                    info = await proxy.getBackupInfo()
                    errinfo = info.get('lastexception')
                    laststart1 = info['laststart']
                    self.eq(errinfo['err'], 'SynErr')

                    # Test runners can take an unusually long time to spawn a process
                    with mock.patch.object(s_cell.Cell, 'BACKUP_SPAWN_TIMEOUT', 8.0):

                        with mock.patch.object(s_cell.Cell, '_backupProc', staticmethod(_sleeper2Proc)):
                            await self.asyncraises(s_exc.SynErr, proxy.runBackup())

                        info = await proxy.getBackupInfo()
                        laststart2 = info['laststart']
                        self.ne(laststart1, laststart2)
                        errinfo = info.get('lastexception')
                        self.eq(errinfo['err'], 'SynErr')

                        with mock.patch.object(s_cell.Cell, '_backupProc', staticmethod(_exiterProc)):
                            await self.asyncraises(s_exc.SpawnExit, proxy.runBackup())

                        info = await proxy.getBackupInfo()
                        laststart3 = info['laststart']
                        self.ne(laststart2, laststart3)
                        errinfo = info.get('lastexception')
                        self.eq(errinfo['err'], 'SpawnExit')

                    # Create rando slabs inside cell dir
                    slabpath = s_common.genpath(coredirn, 'randoslab')
                    async with await s_lmdbslab.Slab.anit(slabpath):
                        pass

                    slabpath = s_common.genpath(coredirn, 'randodirn', 'randoslab2')
                    async with await s_lmdbslab.Slab.anit(slabpath):
                        pass

                    name = await proxy.runBackup()
                    self.eq((name,), await proxy.getBackups())

                    srcreal, _ = s_common.getDirSize(coredirn)
                    backupdir = s_common.reqdir(backdirn, name)
                    backreal, _ = s_common.getDirSize(backupdir)
                    self.le(backreal, srcreal)

                    info = await proxy.getBackupInfo()
                    self.none(info['currduration'])
                    laststart4 = info['laststart']
                    self.ne(laststart3, laststart4)
                    self.true(0 < info['lastsize'] <= srcreal)
                    self.nn(info['lastend'])
                    self.lt(0, info['lastduration'])
                    self.none(info['lastexception'])
                    self.none(info['lastupload'])

                    # look inside backup
                    backups = await proxy.getBackups()
                    self.len(1, backups)
                    backupdir = s_common.reqdir(backdirn, backups[0])
                    s_common.reqpath(backupdir, 'cell.yaml')
                    s_common.reqpath(backupdir, 'randoslab', 'data.mdb')
                    s_common.reqpath(backupdir, 'randodirn', 'randoslab2', 'data.mdb')

                    await proxy.delBackup(name)
                    self.eq((), await proxy.getBackups())
                    self.false(os.path.exists(backupdir))

                    name = await proxy.runBackup(name='foo/bar')

                    with self.raises(s_exc.BadArg):
                        await proxy.delBackup(name='foo')

                    self.true(os.path.isdir(os.path.join(backdirn, 'foo', 'bar')))
                    self.eq(('foo/bar',), await proxy.getBackups())

                    with self.raises(s_exc.BadArg):
                        await proxy.runBackup(name='foo/bar')

    async def test_cell_tls_client(self):

        with self.getTestDir() as dirn:

            async with self.getTestCryo(dirn=dirn) as cryo:

                cryo.certdir.genCaCert('localca')
                cryo.certdir.genHostCert('localhost', signas='localca')
                cryo.certdir.genUserCert('root@localhost', signas='localca')
                cryo.certdir.genUserCert('newp@localhost', signas='localca')

                root = await cryo.auth.addUser('root@localhost')
                await root.setAdmin(True)

            async with self.getTestCryo(dirn=dirn) as cryo:

                addr, port = await cryo.dmon.listen('ssl://0.0.0.0:0?hostname=localhost&ca=localca')

                async with await s_telepath.openurl(f'ssl://root@127.0.0.1:{port}?hostname=localhost') as proxy:
                    self.eq(cryo.iden, await proxy.getCellIden())

                with self.raises(s_exc.BadCertHost):
                    url = f'ssl://root@127.0.0.1:{port}?hostname=borked.localhost'
                    async with await s_telepath.openurl(url) as proxy:
                        pass

                with self.raises(s_exc.NoSuchUser) as cm:
                    url = f'ssl://newp@127.0.0.1:{port}?hostname=localhost'
                    async with await s_telepath.openurl(url) as proxy:
                        pass
                self.eq(cm.exception.get('user'), 'newp@localhost')

    async def test_cell_auth_ctor(self):
        conf = {
            'auth:ctor': 'synapse.tests.test_lib_cell.altAuthCtor',
            'auth:conf': {
                'foo': 'bar',
            },
        }
        with self.getTestDir() as dirn:
            async with await s_cell.Cell.anit(dirn, conf=conf) as cell:
                self.eq('faz', cell.conf.get('auth:conf')['baz'])
                await cell.auth.addUser('visi')

    async def test_cell_onepass(self):

        async with self.getTestCell(s_cell.Cell) as cell:

            await cell.auth.rootuser.setPasswd('root')

            visi = await cell.auth.addUser('visi')

            thost, tport = await cell.dmon.listen('tcp://127.0.0.1:0')
            hhost, hport = await cell.addHttpsPort(0, host='127.0.0.1')

            async with self.getHttpSess(port=hport) as sess:
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue')
                answ = await resp.json()
                self.eq('err', answ['status'])
                self.eq('NotAuthenticated', answ['code'])

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:

                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue')
                answ = await resp.json()
                self.eq('err', answ['status'])
                self.eq('SchemaViolation', answ['code'])

                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', json={'user': 'newp'})
                answ = await resp.json()
                self.eq('err', answ['status'])

                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', json={'user': visi.iden})
                answ = await resp.json()
                self.eq('ok', answ['status'])

                onepass = answ['result']

            async with await s_telepath.openurl(f'tcp://visi:{onepass}@127.0.0.1:{tport}') as proxy:
                await proxy.getCellIden()

            with self.raises(s_exc.AuthDeny):
                async with await s_telepath.openurl(f'tcp://visi:{onepass}@127.0.0.1:{tport}') as proxy:
                    pass

            # purposely give a negative expire for test...
            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', json={'user': visi.iden, 'duration': -1000})
                answ = await resp.json()
                self.eq('ok', answ['status'])
                onepass = answ['result']

            with self.raises(s_exc.AuthDeny):
                async with await s_telepath.openurl(f'tcp://visi:{onepass}@127.0.0.1:{tport}') as proxy:
                    pass

    async def test_cell_activecoro(self):

        evt0 = asyncio.Event()
        evt1 = asyncio.Event()
        evt2 = asyncio.Event()
        evt3 = asyncio.Event()
        evt4 = asyncio.Event()

        async def coro():
            try:
                evt0.set()
                await evt1.wait()
                evt2.set()
                await evt3.wait()

            except asyncio.CancelledError:
                evt4.set()
                raise

        async with self.getTestCell(s_cell.Cell) as cell:

            # Note: cell starts active, so coro should immediate run
            cell.addActiveCoro(coro)

            async def step():
                await asyncio.wait_for(evt0.wait(), timeout=2)

                # step him through...
                evt1.set()
                await asyncio.wait_for(evt2.wait(), timeout=2)

                evt0.clear()
                evt1.clear()
                evt3.set()

                await asyncio.wait_for(evt0.wait(), timeout=2)

            await step()

            self.none(await cell.delActiveCoro('notacoro'))

            # Make sure a fini'd base takes its activecoros with it
            async with await s_base.Base.anit() as base:
                cell.addActiveCoro(coro, base=base)
                self.len(2, cell.activecoros)

            self.len(1, cell.activecoros)

            self.raises(s_exc.IsFini, cell.addActiveCoro, coro, base=base)

            # now deactivate and it gets cancelled
            await cell.setCellActive(False)
            await asyncio.wait_for(evt4.wait(), timeout=2)

            evt0.clear()
            evt1.clear()
            evt2.clear()
            evt3.clear()
            evt4.clear()

            # make him active post-init and confirm
            await cell.setCellActive(True)
            await step()

            self.none(await cell.delActiveCoro(s_common.guid()))

    async def test_cell_stream_backup(self):

        with self.getTestDir() as dirn:

            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')
            bkuppath = os.path.join(dirn, 'bkup.tar.gz')
            bkuppath2 = os.path.join(dirn, 'bkup2.tar.gz')
            bkuppath3 = os.path.join(dirn, 'bkup3.tar.gz')
            bkuppath4 = os.path.join(dirn, 'bkup4.tar.gz')
            bkuppath5 = os.path.join(dirn, 'bkup5.tar.gz')

            conf = {'backup:dir': backdirn}
            s_common.yamlsave(conf, coredirn, 'cell.yaml')

            async with self.getTestCore(dirn=coredirn) as core:

                core.certdir.genCaCert('localca')
                core.certdir.genHostCert('localhost', signas='localca')
                core.certdir.genUserCert('root@localhost', signas='localca')

                root = await core.auth.addUser('root@localhost')
                await root.setAdmin(True)

                nodes = await core.nodes('[test:str=streamed]')
                self.len(1, nodes)

                async with core.getLocalProxy() as proxy:

                    with self.raises(s_exc.BadArg):
                        async for msg in proxy.iterBackupArchive('nope'):
                            pass

                    await proxy.runBackup(name='bkup')

                    with mock.patch('synapse.lib.cell._iterBackupProc', _backupSleep):
                        arch = s_t_utils.alist(proxy.iterBackupArchive('bkup'))
                        with self.raises(asyncio.TimeoutError):
                            await asyncio.wait_for(arch, timeout=0.1)

                        async def _fakeBackup(self, name=None, wait=True):
                            s_common.gendir(os.path.join(backdirn, name))

                        with mock.patch.object(s_cell.Cell, 'runBackup', _fakeBackup):
                            arch = s_t_utils.alist(proxy.iterNewBackupArchive('nobkup'))
                            with self.raises(asyncio.TimeoutError):
                                await asyncio.wait_for(arch, timeout=0.1)

                        async def _slowFakeBackup(self, name=None, wait=True):
                            s_common.gendir(os.path.join(backdirn, name))
                            await asyncio.sleep(3.0)

                        with mock.patch.object(s_cell.Cell, 'runBackup', _slowFakeBackup):
                            arch = s_t_utils.alist(proxy.iterNewBackupArchive('nobkup2'))
                            with self.raises(asyncio.TimeoutError):
                                await asyncio.wait_for(arch, timeout=0.1)

                        evt0 = asyncio.Event()
                        evt1 = asyncio.Event()
                        orig = s_cell.Cell.iterNewBackupArchive

                        async def _slowFakeBackup2(self, name=None, wait=True):
                            evt0.set()
                            s_common.gendir(os.path.join(backdirn, name))
                            await asyncio.sleep(3.0)

                        async def _iterNewDup(self, user, name=None, remove=False):
                            try:
                                await orig(self, user, name=name, remove=remove)
                            except asyncio.CancelledError:
                                evt1.set()
                                raise

                        with mock.patch.object(s_cell.Cell, 'runBackup', _slowFakeBackup2):
                            with mock.patch.object(s_cell.Cell, 'iterNewBackupArchive', _iterNewDup):
                                arch = s_t_utils.alist(proxy.iterNewBackupArchive('dupbackup', remove=True))
                                task = core.schedCoro(arch)
                                await asyncio.wait_for(evt0.wait(), timeout=2)

                        fail = s_t_utils.alist(proxy.iterNewBackupArchive('alreadystreaming', remove=True))
                        await self.asyncraises(s_exc.BackupAlreadyRunning, fail)
                        task.cancel()
                        await asyncio.wait_for(evt1.wait(), timeout=2)

                    with self.raises(s_exc.BadArg):
                        async for msg in proxy.iterNewBackupArchive('bkup'):
                            pass

                    # Get an existing backup
                    with open(bkuppath, 'wb') as bkup:
                        async for msg in proxy.iterBackupArchive('bkup'):
                            bkup.write(msg)

                    # Create a new backup
                    nodes = await core.nodes('[test:str=freshbkup]')
                    self.len(1, nodes)

                    with open(bkuppath2, 'wb') as bkup2:
                        async for msg in proxy.iterNewBackupArchive('bkup2'):
                            bkup2.write(msg)

                    self.eq(('bkup', 'bkup2'), sorted(await proxy.getBackups()))
                    self.true(os.path.isdir(os.path.join(backdirn, 'bkup2')))

                    # Create a new backup and remove after
                    nodes = await core.nodes('[test:str=lastbkup]')
                    self.len(1, nodes)

                    with open(bkuppath3, 'wb') as bkup3:
                        async for msg in proxy.iterNewBackupArchive('bkup3', remove=True):
                            bkup3.write(msg)

                    self.eq(('bkup', 'bkup2'), sorted(await proxy.getBackups()))
                    self.false(os.path.isdir(os.path.join(backdirn, 'bkup3')))

                    # Create a new backup without a name param
                    nodes = await core.nodes('[test:str=noname]')
                    self.len(1, nodes)

                    with open(bkuppath4, 'wb') as bkup4:
                        async for msg in proxy.iterNewBackupArchive(remove=True):
                            bkup4.write(msg)

                    self.eq(('bkup', 'bkup2'), sorted(await proxy.getBackups()))

                    # Start another backup while one is already running
                    bkup = s_t_utils.alist(proxy.iterNewBackupArchive('runbackup', remove=True))
                    task = core.schedCoro(bkup)
                    await asyncio.sleep(0)

                    fail = s_t_utils.alist(proxy.iterNewBackupArchive('alreadyrunning', remove=True))
                    await self.asyncraises(s_exc.BackupAlreadyRunning, fail)
                    await asyncio.wait_for(task, 5)

            with tarfile.open(bkuppath, 'r:gz') as tar:
                tar.extractall(path=dirn)

            bkupdirn = os.path.join(dirn, 'bkup')
            async with self.getTestCore(dirn=bkupdirn) as core:
                nodes = await core.nodes('test:str=streamed')
                self.len(1, nodes)

                nodes = await core.nodes('test:str=freshbkup')
                self.len(0, nodes)

            with tarfile.open(bkuppath2, 'r:gz') as tar:
                tar.extractall(path=dirn)

            bkupdirn2 = os.path.join(dirn, 'bkup2')
            async with self.getTestCore(dirn=bkupdirn2) as core:
                nodes = await core.nodes('test:str=freshbkup')
                self.len(1, nodes)

            with tarfile.open(bkuppath3, 'r:gz') as tar:
                tar.extractall(path=dirn)

            bkupdirn3 = os.path.join(dirn, 'bkup3')
            async with self.getTestCore(dirn=bkupdirn3) as core:
                nodes = await core.nodes('test:str=lastbkup')
                self.len(1, nodes)

            with tarfile.open(bkuppath4, 'r:gz') as tar:
                bkupname = os.path.commonprefix(tar.getnames())
                tar.extractall(path=dirn)

            bkupdirn4 = os.path.join(dirn, bkupname)
            async with self.getTestCore(dirn=bkupdirn4) as core:
                nodes = await core.nodes('test:str=noname')
                self.len(1, nodes)

            # Test backup over SSL
            async with self.getTestCore(dirn=coredirn) as core:

                nodes = await core.nodes('[test:str=ssl]')
                addr, port = await core.dmon.listen('ssl://0.0.0.0:0?hostname=localhost&ca=localca')

                async with await s_telepath.openurl(f'ssl://root@127.0.0.1:{port}?hostname=localhost') as proxy:
                    with open(bkuppath5, 'wb') as bkup5:
                        async for msg in proxy.iterNewBackupArchive(remove=True):
                            bkup5.write(msg)

                    with mock.patch('synapse.lib.cell._iterBackupProc', _backupEOF):
                        await s_t_utils.alist(proxy.iterNewBackupArchive('eof', remove=True))

            with tarfile.open(bkuppath5, 'r:gz') as tar:
                bkupname = os.path.commonprefix(tar.getnames())
                tar.extractall(path=dirn)

            bkupdirn5 = os.path.join(dirn, bkupname)
            async with self.getTestCore(dirn=bkupdirn5) as core:
                nodes = await core.nodes('test:str=ssl')
                self.len(1, nodes)

    async def test_inaugural_users(self):

        conf = {
            'inaugural': {
                'users': [
                    {
                        'name': 'foo@bar.mynet.com',
                        'email': 'foo@barcorp.com',
                        'roles': [
                            'user'
                        ],
                        'rules': [
                            [False, ['thing', 'del']],
                            [True, ['thing', ]],
                        ],
                    },
                    {
                        'name': 'sally@bar.mynet.com',
                        'admin': True,
                    },
                ],
                'roles': [
                    {
                        'name': 'user',
                        'rules': [
                            [True, ['foo', 'bar']],
                            [True, ['foo', 'duck']],
                            [False, ['newp', ]],
                        ]
                    },
                ]
            }
        }

        async with self.getTestCell(s_cell.Cell, conf=conf) as cell:  # type: s_cell.Cell
            iden = s_common.guid((cell.iden, 'auth', 'user', 'foo@bar.mynet.com'))
            user = cell.auth.user(iden)  # type: s_hiveauth.HiveUser
            self.eq(user.name, 'foo@bar.mynet.com')
            self.eq(user.pack().get('email'), 'foo@barcorp.com')
            self.false(user.isAdmin())
            self.true(user.allowed(('thing', 'cool')))
            self.false(user.allowed(('thing', 'del')))
            self.true(user.allowed(('thing', 'duck', 'stuff')))
            self.false(user.allowed(('newp', 'secret')))

            iden = s_common.guid((cell.iden, 'auth', 'user', 'sally@bar.mynet.com'))
            user = cell.auth.user(iden)  # type: s_hiveauth.HiveUser
            self.eq(user.name, 'sally@bar.mynet.com')
            self.true(user.isAdmin())

        # Cannot use root
        conf = {
            'inaugural': {
                'users': [
                    {'name': 'root',
                     'admin': False,
                     }
                ]
            }
        }
        with self.raises(s_exc.BadConfValu):
            async with self.getTestCell(s_cell.Cell, conf=conf) as cell:  # type: s_cell.Cell
                pass

        # Cannot use all
        conf = {
            'inaugural': {
                'roles': [
                    {'name': 'all',
                     'rules': [
                         [True, ['floop', 'bloop']],
                     ]}
                ]
            }
        }
        with self.raises(s_exc.BadConfValu):
            async with self.getTestCell(s_cell.Cell, conf=conf) as cell:  # type: s_cell.Cell
                pass

        # Colliding with aha:admin will fail
        conf = {
            'inaugural': {
                'users': [
                    {'name': 'bob@foo.bar.com'}
                ]
            },
            'aha:admin': 'bob@foo.bar.com',
        }
        with self.raises(s_exc.DupUserName):
            async with self.getTestCell(s_cell.Cell, conf=conf) as cell:  # type: s_cell.Cell
                pass

    async def test_advisory_locking(self):
        # fcntl not supported on windows
        self.thisHostMustNot(platform='windows')

        with self.getTestDir() as dirn:

            ctx = multiprocessing.get_context('spawn')

            evt1 = ctx.Event()

            proc = ctx.Process(target=lock_target, args=(dirn, evt1,))
            proc.start()

            self.true(evt1.wait(timeout=10))

            with self.raises(s_exc.FatalErr) as cm:
                async with await s_cell.Cell.anit(dirn) as cell:
                    pass

            self.eq(cm.exception.get('mesg'),
                    'Cannot start the cell, another process is already running it.')

            os.kill(proc.pid, signal.SIGTERM)
            proc.join(timeout=10)
            self.eq(proc.exitcode, 137)

    async def test_cell_backup_default(self):

        async with self.getTestCore() as core:

            await core.runBackup('foo')
            await core.runBackup('bar')

            foopath = s_common.genpath(core.dirn, 'backups', 'foo')
            barpath = s_common.genpath(core.dirn, 'backups', 'bar')

            self.true(os.path.isdir(foopath))
            self.true(os.path.isdir(barpath))

            foonest = s_common.genpath(core.dirn, 'backups', 'bar', 'backups')
            self.false(os.path.isdir(foonest))

    async def test_mirror_badiden(self):
        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'cell00')
            path01 = s_common.gendir(dirn, 'coll01')

            conf00 = {'dmon:listen': 'tcp://127.0.0.1:0/',
                      'https:port': 0,
                      'nexslog:en': True,
                      }
            async with self.getTestCell(s_cell.Cell, dirn=path00, conf=conf00) as cell00:

                conf01 = {'dmon:listen': 'tcp://127.0.0.1:0/',
                          'https:port': 0,
                          'mirror': cell00.getLocalUrl(),
                          'nexslog:en': True,
                          }

                # Create the bad cell with its own guid
                async with self.getTestCell(s_cell.Cell, dirn=path01, conf={'nexslog:en': True}) as cell01:
                    pass

                with self.getAsyncLoggerStream('synapse.lib.nexus',
                                               'has different iden') as stream:
                    async with self.getTestCell(s_cell.Cell, dirn=path01, conf=conf01) as cell01:
                        await stream.wait(timeout=2)
                        self.true(await cell01.waitfini(6))

    async def test_backup_restore(self):

        async with self.getTestAxon(conf={'auth:passwd': 'root'}) as axon:
            addr, port = await axon.addHttpsPort(0)
            url = f'https+insecure://root:root@localhost:{port}/api/v1/axon/files/by/sha256/'

            # Make our first backup
            async with self.getTestCore() as core:
                self.len(1, await core.nodes('[inet:ipv4=1.2.3.4]'))

                # Punch in a value to the cell.yaml to ensure it persists
                core.conf['storm:log'] = True
                core.conf.reqConfValid()
                s_common.yamlmod({'storm:log': True}, core.dirn, 'cell.yaml')

                async with await axon.upload() as upfd:

                    async with core.getLocalProxy() as prox:

                        async for chunk in prox.iterNewBackupArchive():
                            await upfd.write(chunk)

                        size, sha256 = await upfd.save()
                        await asyncio.sleep(0)

            furl = f'{url}{s_common.ehex(sha256)}'

            # Happy test for URL based restore.
            with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl):
                with self.getTestDir() as cdir:
                    # Restore works
                    with self.getAsyncLoggerStream('synapse.lib.cell',
                                                   'Restoring cortex from SYN_RESTORE_HTTPS_URL') as stream:
                        async with await s_cortex.Cortex.initFromArgv([cdir]) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))
                            self.true(core.conf.get('storm:log'))

                    # Turning the service back on with the restore URL is fine too.
                    with self.getAsyncLoggerStream('synapse.lib.cell') as stream:
                        async with await s_cortex.Cortex.initFromArgv([cdir]) as core:
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

                            # Take a backup of the cell with the restore.done file in place
                            async with await axon.upload() as upfd:
                                async with core.getLocalProxy() as prox:
                                    async for chunk in prox.iterNewBackupArchive():
                                        await upfd.write(chunk)

                                    size, sha256r = await upfd.save()
                                    await asyncio.sleep(0)

                    stream.seek(0)
                    logs = stream.read()
                    self.notin('Restoring from url', logs)

                    # grab the restore iden for later use
                    rpath = s_common.genpath(cdir, 'restore.done')
                    with s_common.genfile(rpath) as fd:
                        doneiden = fd.read().decode().strip()
                    self.true(s_common.isguid(doneiden))

                    # Restoring into a directory that has been used previously should wipe out
                    # all of the existing content of that directory. Remove the restore.done file
                    # to force the restore from happening again.
                    os.unlink(rpath)
                    with self.getAsyncLoggerStream('synapse.lib.cell',
                                                   'Removing existing') as stream:
                        async with await s_cortex.Cortex.initFromArgv([cdir]) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

            # Restore a backup which has an existing restore.done file in it - that marker file will get overwritten
            furl2 = f'{url}{s_common.ehex(sha256r)}'
            with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl2):
                with self.getTestDir() as cdir:
                    # Restore works
                    with self.getAsyncLoggerStream('synapse.lib.cell',
                                                   'Restoring cortex from SYN_RESTORE_HTTPS_URL') as stream:
                        async with await s_cortex.Cortex.initFromArgv([cdir]) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

                    rpath = s_common.genpath(cdir, 'restore.done')
                    with s_common.genfile(rpath) as fd:
                        second_doneiden = fd.read().decode().strip()
                        self.true(s_common.isguid(second_doneiden))
                    self.ne(doneiden, second_doneiden)

    async def test_passwd_regression(self):
        # Backwards compatibility test for shadowv2
        # Cell was created prior to the shadowv2 password change.
        with self.getRegrDir('cells', 'passwd-2.109.0') as dirn:
            async with self.getTestCell(s_cell.Cell, dirn=dirn) as cell:  # type: s_cell.Cell
                root = await cell.auth.getUserByName('root')
                shadow = root.info.get('passwd')
                self.isinstance(shadow, tuple)
                self.len(2, shadow)

                # Old password works and is migrated to the new password scheme
                self.false(await root.tryPasswd('newp'))
                self.true(await root.tryPasswd('root'))
                shadow = root.info.get('passwd')
                self.isinstance(shadow, dict)
                self.eq(shadow.get('type'), s_passwd.DEFAULT_PTYP)

                # Logging back in works
                self.true(await root.tryPasswd('root'))

                user = await cell.auth.getUserByName('user')

                # User can login with their regular password.
                shadow = user.info.get('passwd')
                self.isinstance(shadow, tuple)
                self.true(await user.tryPasswd('secret1234'))
                shadow = user.info.get('passwd')
                self.isinstance(shadow, dict)

                # User has a 10 year duration onepass value available.
                onepass = '0f327906fe0221a7f582744ad280e1ca'
                self.true(await user.tryPasswd(onepass))
                self.false(await user.tryPasswd(onepass))

                # Passwords can be changed as well.
                await user.setPasswd('hehe')
                self.true(await user.tryPasswd('hehe'))
                self.false(await user.tryPasswd('secret1234'))

        # Pre-nexus changes of root via auth:passwd work too.
        with self.getRegrDir('cells', 'passwd-2.109.0') as dirn:
            conf = {'auth:passwd': 'supersecretpassword'}
            async with self.getTestCell(s_cell.Cell, dirn=dirn, conf=conf) as cell:  # type: s_cell.Cell
                root = await cell.auth.getUserByName('root')
                shadow = root.info.get('passwd')
                self.isinstance(shadow, dict)
                self.eq(shadow.get('type'), s_passwd.DEFAULT_PTYP)
                self.false(await root.tryPasswd('root'))
                self.true(await root.tryPasswd('supersecretpassword'))
