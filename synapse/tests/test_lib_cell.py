import http
import os
import ssl
import sys
import time
import base64
import signal
import socket
import asyncio
import tarfile
import collections
import multiprocessing

from unittest import mock

import cryptography.x509 as c_x509

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.auth as s_auth
import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.link as s_link
import synapse.lib.drive as s_drive
import synapse.lib.nexus as s_nexus
import synapse.lib.config as s_config
import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.crypto.passwd as s_passwd
import synapse.lib.platforms.linux as s_linux

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

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

def reload_target(dirn, evt1, evt2):  # pragma: no cover
    '''
    Function to make a cell in a directory and wait to be shut down.
    Used as a Process target for reload SIGHUP locking tests.

    Args:
        dirn (str): Cell directory.
        evt1 (multiprocessing.Event): event to signal the cell is ready to receive sighup
        evt2 (multiprocessing.Event): event to signal the cell has been reset
    '''
    async def main():
        cell = await s_t_utils.ReloadCell.anit(dirn)
        await cell.addSignalHandlers()
        await cell.addTestReload()
        cell._reloadevt = evt2
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

    @s_cell.adminapi()
    async def adminOnly(self):
        return True

    @s_cell.adminapi(log=True)
    async def adminOnlyLog(self, arg1, arg2, **kwargs):
        return arg1, arg2, kwargs

class EchoAuth(s_cell.Cell):
    cellapi = EchoAuthApi
    # non-default commit / version / verstring
    COMMIT = 'mycommit'
    VERSION = (1, 2, 3)
    VERSTRING = '1.2.3'

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

    maxusers = cell.conf.get('max:users')

    seed = s_common.guid((cell.iden, 'hive', 'auth'))

    auth = await s_auth.Auth.anit(
        cell.slab,
        'auth',
        seed=seed,
        nexsroot=cell.getCellNexsRoot(),
        maxusers=maxusers
    )

    auth.link(cell.dist)

    def finilink():
        auth.unlink(cell.dist)

    cell.onfini(finilink)
    cell.onfini(auth.fini)
    return auth

testDataSchema_v0 = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string'},
        'size': {'type': 'number'},
        'stuff': {'type': ['number', 'null'], 'default': None}
    },
    'required': ['type', 'size', 'stuff'],
    'additionalProperties': False,
}

testDataSchema_v1 = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string'},
        'size': {'type': 'number'},
        'stuff': {'type': ['number', 'null'], 'default': None},
        'woot': {'type': 'string'},
    },
    'required': ['type', 'size', 'woot'],
    'additionalProperties': False,
}

class CellTest(s_t_utils.SynTest):

    async def test_cell_drive(self):

        with self.getTestDir() as dirn:
            async with self.getTestCell(dirn=dirn) as cell:

                with self.raises(s_exc.BadName):
                    s_drive.reqValidName('A' * 512)

                info = {'name': 'users'}
                pathinfo = await cell.addDriveItem(info)

                info = {'name': 'root'}
                pathinfo = await cell.addDriveItem(info, path='users')

                with self.raises(s_exc.DupIden):
                    await cell.drive.addItemInfo(pathinfo[-1], path='users')

                rootdir = pathinfo[-1].get('iden')
                self.eq(0, pathinfo[-1].get('kids'))

                info = {'name': 'win32k.sys', 'type': 'hehe'}
                with self.raises(s_exc.NoSuchType):
                    info = await cell.addDriveItem(info, reldir=rootdir)

                infos = [i async for i in cell.getDriveKids(s_drive.rootdir)]
                self.len(1, infos)
                self.eq(1, infos[0].get('kids'))
                self.eq('users', infos[0].get('name'))

                # TODO how to handle iden match with additional property mismatch

                self.true(await cell.drive.setTypeSchema('woot', testDataSchema_v0, vers=0))
                self.true(await cell.drive.setTypeSchema('woot', testDataSchema_v0, vers=1))
                self.false(await cell.drive.setTypeSchema('woot', testDataSchema_v0, vers=1))

                with self.raises(s_exc.BadVersion):
                    await cell.drive.setTypeSchema('woot', testDataSchema_v0, vers=0)

                info = {'name': 'win32k.sys', 'type': 'woot'}
                info = await cell.addDriveItem(info, reldir=rootdir)

                iden = info[-1].get('iden')

                tick = s_common.now()
                rootuser = cell.auth.rootuser.iden

                with self.raises(s_exc.SchemaViolation):
                    versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
                    await cell.setDriveData(iden, versinfo, {'newp': 'newp'})

                versinfo = {'version': (1, 1, 0), 'updated': tick + 10, 'updater': rootuser}
                info, versinfo = await cell.setDriveData(iden, versinfo, {'type': 'haha', 'size': 20, 'stuff': 12})
                self.eq(info.get('version'), (1, 1, 0))
                self.eq(versinfo.get('version'), (1, 1, 0))

                versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
                info, versinfo = await cell.setDriveData(iden, versinfo, {'type': 'hehe', 'size': 0, 'stuff': 13})
                self.eq(info.get('version'), (1, 1, 0))
                self.eq(versinfo.get('version'), (1, 0, 0))

                versinfo10, data10 = await cell.getDriveData(iden, vers=(1, 0, 0))
                self.eq(versinfo10.get('updated'), tick)
                self.eq(versinfo10.get('updater'), rootuser)
                self.eq(versinfo10.get('version'), (1, 0, 0))

                versinfo11, data11 = await cell.getDriveData(iden, vers=(1, 1, 0))
                self.eq(versinfo11.get('updated'), tick + 10)
                self.eq(versinfo11.get('updater'), rootuser)
                self.eq(versinfo11.get('version'), (1, 1, 0))

                versions = [vers async for vers in cell.getDriveDataVersions(iden)]
                self.len(2, versions)
                self.eq(versions[0], versinfo11)
                self.eq(versions[1], versinfo10)

                info = await cell.delDriveData(iden, vers=(0, 0, 0))

                versions = [vers async for vers in cell.getDriveDataVersions(iden)]
                self.len(2, versions)
                self.eq(versions[0], versinfo11)
                self.eq(versions[1], versinfo10)

                info = await cell.delDriveData(iden, vers=(1, 1, 0))
                self.eq(info.get('updated'), tick)
                self.eq(info.get('version'), (1, 0, 0))

                info = await cell.delDriveData(iden, vers=(1, 0, 0))
                self.eq(info.get('size'), 0)
                self.eq(info.get('version'), (0, 0, 0))
                self.none(info.get('updated'))
                self.none(info.get('updater'))

                # repopulate a couple data versions to test migration and delete
                versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
                info, versinfo = await cell.setDriveData(iden, versinfo, {'type': 'hehe', 'size': 0, 'stuff': 14})
                versinfo = {'version': (1, 1, 0), 'updated': tick + 10, 'updater': rootuser}
                info, versinfo = await cell.setDriveData(iden, versinfo, {'type': 'haha', 'size': 17, 'stuff': 15})
                self.eq(versinfo, (await cell.getDriveData(iden))[0])

                # This will be done by the cell in a cell storage version migration...
                async def migrate_v1(info, versinfo, data):
                    data['woot'] = 'woot'
                    return data

                await cell.drive.setTypeSchema('woot', testDataSchema_v1, migrate_v1)

                versinfo, data = await cell.getDriveData(iden, vers=(1, 0, 0))
                self.eq('woot', data.get('woot'))

                versinfo, data = await cell.getDriveData(iden, vers=(1, 1, 0))
                self.eq('woot', data.get('woot'))

                with self.raises(s_exc.NoSuchIden):
                    await cell.reqDriveInfo('d7d6107b200e2c039540fc627bc5537d')

                with self.raises(s_exc.TypeMismatch):
                    await cell.getDriveInfo(iden, typename='newp')

                self.nn(await cell.getDriveInfo(iden))
                self.len(2, [vers async for vers in cell.getDriveDataVersions(iden)])

                await cell.delDriveData(iden)
                self.len(1, [vers async for vers in cell.getDriveDataVersions(iden)])

                await cell.delDriveInfo(iden)

                self.none(await cell.getDriveInfo(iden))
                self.len(0, [vers async for vers in cell.getDriveDataVersions(iden)])

                with self.raises(s_exc.NoSuchPath):
                    await cell.getDrivePath('users/root/win32k.sys')

                pathinfo = await cell.addDrivePath('foo/bar/baz')
                self.len(3, pathinfo)
                self.eq('foo', pathinfo[0].get('name'))
                self.eq(1, pathinfo[0].get('kids'))
                self.eq('bar', pathinfo[1].get('name'))
                self.eq(1, pathinfo[1].get('kids'))
                self.eq('baz', pathinfo[2].get('name'))
                self.eq(0, pathinfo[2].get('kids'))

                self.eq(pathinfo, await cell.addDrivePath('foo/bar/baz'))

                baziden = pathinfo[2].get('iden')
                self.eq(pathinfo, await cell.drive.getItemPath(baziden))

                info = await cell.setDriveInfoPerm(baziden, {'users': {rootuser: 3}, 'roles': {}})
                self.eq(3, info['perm']['users'][rootuser])

                with self.raises(s_exc.NoSuchIden):
                    # s_drive.rootdir is all 00s... ;)
                    await cell.setDriveInfoPerm(s_drive.rootdir, {'users': {}, 'roles': {}})

                await cell.addDrivePath('hehe/haha')
                pathinfo = await cell.setDriveInfoPath(baziden, 'hehe/haha/hoho')

                self.eq('hoho', pathinfo[-1].get('name'))
                self.eq(baziden, pathinfo[-1].get('iden'))

                self.true(await cell.drive.hasPathInfo('hehe/haha/hoho'))
                self.false(await cell.drive.hasPathInfo('foo/bar/baz'))

                pathinfo = await cell.getDrivePath('foo/bar')
                self.eq(0, pathinfo[-1].get('kids'))

                pathinfo = await cell.getDrivePath('hehe/haha')
                self.eq(1, pathinfo[-1].get('kids'))

                with self.raises(s_exc.DupName):
                    iden = pathinfo[-2].get('iden')
                    name = pathinfo[-1].get('name')
                    cell.drive.reqFreeStep(iden, name)

                walks = [item async for item in cell.drive.walkPathInfo('hehe')]
                self.len(3, walks)
                # confirm walked paths are yielded depth first...
                self.eq('hoho', walks[0].get('name'))
                self.eq('haha', walks[1].get('name'))
                self.eq('hehe', walks[2].get('name'))

                iden = walks[2].get('iden')
                walks = [item async for item in cell.drive.walkItemInfo(iden)]
                self.len(3, walks)
                self.eq('hoho', walks[0].get('name'))
                self.eq('haha', walks[1].get('name'))
                self.eq('hehe', walks[2].get('name'))

                self.none(cell.drive.getTypeSchema('newp'))

                cell.drive.validators.pop('woot')
                self.nn(cell.drive.getTypeValidator('woot'))

                # move to root dir
                pathinfo = await cell.setDriveInfoPath(baziden, 'zipzop')
                self.len(1, pathinfo)
                self.eq(s_drive.rootdir, pathinfo[-1].get('parent'))

                pathinfo = await cell.setDriveInfoPath(baziden, 'hehe/haha/hoho')
                self.len(3, pathinfo)

            async with self.getTestCell(dirn=dirn) as cell:
                data = {'type': 'woot', 'size': 20, 'stuff': 12, 'woot': 'woot'}
                # explicitly clear out the cache JsValidators, otherwise we get the cached, pre-msgpack
                # version of the validator, which will be correct and skip the point of this test.
                s_config._JsValidators.clear()
                cell.drive.reqValidData('woot', data)

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

                    # @adminApi methods are allowed
                    self.true(await proxy.adminOnly())
                    mesg = "Executing [EchoAuthApi.adminOnlyLog] as [root] with args [(1, 2)[{'three': 4}]"
                    with self.getStructuredAsyncLoggerStream('synapse.lib.cell', mesg) as stream:
                        self.eq(await proxy.adminOnlyLog(1, 2, three=4), (1, 2, {'three': 4}))
                        self.true(await stream.wait(timeout=10))
                    msgs = stream.jsonlines()
                    self.len(1, msgs)
                    self.eq('EchoAuthApi.adminOnlyLog', msgs[0].get('wrapped_func'))

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

                    with self.raises(s_exc.NoSuchUser):
                        await proxy.getUserInfo('newp')

                    # @adminApi methods are not allowed
                    with self.raises(s_exc.AuthDeny) as cm:
                        await proxy.adminOnly()
                    self.eq(cm.exception.get('mesg'), 'User is not an admin [visi]')
                    self.eq(cm.exception.get('user'), visi.iden)
                    self.eq(cm.exception.get('username'), visi.name)
                    with self.raises(s_exc.AuthDeny) as cm:
                        await proxy.adminOnlyLog(1, 2, three=4)

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

                # onepass support in the cell
                async with await s_telepath.openurl(root_url) as proxy:
                    onep = await proxy.genUserOnepass(visi.iden)

                onep_url = f'tcp://visi:{onep}@127.0.0.1:{port}/echo00'
                async with await s_telepath.openurl(onep_url) as proxy:  # type: EchoAuthApi
                    udef = await proxy.getCellUser()
                    self.eq(visi.iden, udef.get('iden'))

                with self.raises(s_exc.AuthDeny):
                    async with await s_telepath.openurl(onep_url) as proxy:  # type: EchoAuthApi
                        pass

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

                self.eq(echo.getDmonUser(), echo.auth.rootuser.iden)

                with self.raises(s_exc.NeedConfValu):
                    await echo.reqAhaProxy()

    async def test_cell_unix_sock(self):

        async with self.getTestCore() as core:
            # This directs the connection through the cell:// handler.
            async with core.getLocalProxy() as prox:
                user = await prox.getCellUser()
                self.eq('root', user.get('name'))
                self.true(await prox.isCellActive())

            with self.raises(s_exc.NoSuchUser):
                url = f'cell://{core.dirn}/?user=newp'
                async with await s_telepath.openurl(url) as prox:
                    pass

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
                visiiden = visi.get('iden')

                self.true(await prox.setCellUser(visiiden))
                self.eq('visi', (await prox.getCellUser())['name'])

                # setCellUser propagates his change to the Daemon Sess object.
                # But we have to use the daemon directly to get that info
                snfo = await cell.dmon.getSessInfo()
                self.len(1, snfo)
                self.eq(snfo[0].get('user').get('name'), 'visi')

                with self.raises(s_exc.AuthDeny):
                    await prox.setCellUser(s_common.guid())

            # Cannot change to a locked user
            await cell.setUserLocked(visiiden, True)
            async with cell.getLocalProxy() as prox:
                with self.raises(s_exc.AuthDeny):
                    await prox.setCellUser(visiiden)

    async def test_cell_getinfo(self):
        async with self.getTestCore() as cell:
            cell.COMMIT = 'mycommit'
            cell.VERSION = (1, 2, 3)
            cell.VERSTRING = '1.2.3'

            cell.features.update({
                'testvalu': 2
            })

            http_info = []
            host, port = await cell.addHttpsPort(0)
            http_info.append({'host': host, 'port': port})
            host, port = await cell.addHttpsPort(0, host='127.0.0.1')
            http_info.append({'host': host, 'port': port})

            async with cell.getLocalProxy() as prox:
                info = await prox.getCellInfo()
                # Cell information
                cnfo = info.get('cell')
                snfo = info.get('synapse')
                self.eq(cnfo.get('commit'), 'mycommit')
                self.eq(cnfo.get('version'), (1, 2, 3))
                self.eq(cnfo.get('verstring'), '1.2.3')
                self.eq(cnfo.get('type'), 'cortex')
                self.isin('nexsindx', cnfo)
                self.ge(cnfo.get('nexsindx'), 0)
                self.true(cnfo.get('active'))
                self.false(cnfo.get('uplink'))
                self.none(cnfo.get('mirror', True))
                # A Cortex populated cellvers
                self.isin('cortex:defaults', cnfo.get('cellvers', {}))

                self.eq(info.get('features'), cell.features)
                self.eq(info.get('features', {}).get('testvalu'), 2)

                # Defaults aha data is
                self.eq(cnfo.get('aha'), {'name': None, 'leader': None, 'network': None})

                # Synapse information
                self.eq(snfo.get('version'), s_version.version)
                self.eq(snfo.get('verstring'), s_version.verstring),
                self.eq(snfo.get('commit'), s_version.commit)

                netw = cnfo.get('network')
                https = netw.get('https')
                self.eq(https, http_info)

        # Mirrors & ready flags
        async with self.getTestAha() as aha:  # type: s_aha.AhaCell

            with self.getTestDir() as dirn:
                cdr0 = s_common.genpath(dirn, 'cell00')
                cdr1 = s_common.genpath(dirn, 'cell01')
                cell00 = await aha.enter_context(self.addSvcToAha(aha, '00.cell', EchoAuth,
                                                                  dirn=cdr0))  # type: EchoAuth
                # Ensure we have a nexus transaction
                await cell00.sync()
                cell01 = await aha.enter_context(self.addSvcToAha(aha, '01.cell', EchoAuth,
                                                                  dirn=cdr1,
                                                                  provinfo={'mirror': 'cell'}))  # type: EchoAuth

                self.true(await asyncio.wait_for(cell01.nexsroot.ready.wait(), timeout=12))
                await cell01.sync()

                cnfo0 = await cell00.getCellInfo()
                cnfo1 = await cell01.getCellInfo()
                self.true(cnfo0['cell']['ready'])
                self.false(cnfo0['cell']['uplink'])
                self.none(cnfo0['cell']['mirror'])
                self.eq(cnfo0['cell']['version'], (1, 2, 3))

                self.true(cnfo1['cell']['ready'])
                self.true(cnfo1['cell']['uplink'])
                self.eq(cnfo1['cell']['mirror'], 'aha://root@cell...')
                self.eq(cnfo1['cell']['version'], (1, 2, 3))

                self.eq(cnfo0['cell']['nexsindx'], cnfo1['cell']['nexsindx'])

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
                    retn = await s_t_utils.alist(cell.nexsroot.nexslog.iter(0))
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

                def1 = await core.getUserDef(visi['iden'])
                def2 = await core.getUserDef(visi['iden'])
                self.false(def1['authgates'] is def2['authgates'])
                self.eq(def1, def2)

                visi = await proxy.getUserDefByName('visi')
                self.eq(visi['email'], 'visi@vertex.link')

                def1 = await core.getRoleDef(ninjas['iden'])
                def2 = await core.getRoleDef(ninjas['iden'])
                self.false(def1['authgates'] is def2['authgates'])
                self.eq(def1, def2)

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
                self.nn(slab['readahead'])
                self.nn(slab['lockmemory'])
                self.nn(slab['recovering'])

    async def test_cell_system_info(self):
        with self.getTestDir() as dirn:
            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')

            async with self.getTestCore(dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:
                    info = await proxy.getSystemInfo()
                    for prop in ('osversion', 'pyversion', 'sysctls', 'tmpdir'):
                        self.nn(info.get(prop))

                    for prop in ('volsize', 'volfree', 'celluptime', 'cellrealdisk',
                                 'cellapprdisk', 'totalmem', 'availmem'):
                        self.lt(0, info.get(prop))

            conf = {'backup:dir': backdirn}
            async with self.getTestCore(conf=conf, dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:
                    info = await proxy.getSystemInfo()
                    for prop in ('osversion', 'pyversion', 'sysctls', 'tmpdir'):
                        self.nn(info.get(prop))

                    for prop in ('volsize', 'volfree', 'backupvolsize', 'backupvolfree', 'celluptime', 'cellrealdisk',
                                 'cellapprdisk', 'totalmem', 'availmem'):
                        self.lt(0, info.get(prop))

    async def test_cell_hiveapi(self):

        async with self.getTestCell() as cell:

            await cell.setHiveKey(('foo', 'bar'), 10)
            await cell.setHiveKey(('foo', 'baz'), 30)

            async with cell.getLocalProxy() as proxy:
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
                self.isin(f'...cell API (telepath): tcp://0.0.0.0:27492', buf)
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
                        self.true(cell.conf.req('nexslog:en'))
                        self.true(cell.conf.req('nexslog:async'))
                        self.none(cell.conf.req('dmon:listen'))
                        self.none(cell.conf.req('https:port'))
                        self.eq(cell.conf.req('aha:name'), 'some:cell')
                        root = cell.auth.rootuser
                        self.true(await root.tryPasswd('secret'))

                # Overrides file wins out over everything else in conflicts
                with self.getTestDir() as dirn:
                    s_common.yamlsave({'nexslog:en': False}, dirn, 'cell.mods.yaml')
                    async with await s_cell.Cell.initFromArgv([dirn]) as cell:
                        self.false(cell.conf.req('nexslog:en'))
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
                            await self.asyncraises(s_exc.SynErr, proxy.runBackup('_sleeperProc'))

                    info = await proxy.getBackupInfo()
                    errinfo = info.get('lastexception')
                    laststart1 = info['laststart']
                    self.eq(errinfo['err'], 'SynErr')
                    self.eq(errinfo['errinfo']['mesg'], 'backup subprocess start timed out')

                    # Test runners can take an unusually long time to spawn a process
                    with mock.patch.object(s_cell.Cell, 'BACKUP_SPAWN_TIMEOUT', 8.0):

                        with mock.patch.object(s_cell.Cell, '_backupProc', staticmethod(_sleeper2Proc)):
                            await self.asyncraises(s_exc.SynErr, proxy.runBackup('_sleeper2Proc'))

                        info = await proxy.getBackupInfo()
                        laststart2 = info['laststart']
                        self.ne(laststart1, laststart2)
                        errinfo = info.get('lastexception')
                        self.eq(errinfo['err'], 'SynErr')
                        self.eq(errinfo['errinfo']['mesg'], 'backup subprocess start timed out')

                    with mock.patch.object(s_cell.Cell, '_backupProc', staticmethod(_exiterProc)):
                        await self.asyncraises(s_exc.SpawnExit, proxy.runBackup('_exiterProc'))

                    info = await proxy.getBackupInfo()
                    laststart3 = info['laststart']
                    self.ne(laststart2, laststart3)
                    errinfo = info.get('lastexception')
                    self.eq(errinfo['err'], 'SpawnExit')
                    self.eq(errinfo['errinfo']['code'], 1)

                    # Create rando slabs inside cell dir
                    slabpath = s_common.genpath(coredirn, 'randoslab')
                    async with await s_lmdbslab.Slab.anit(slabpath):
                        pass

                    slabpath = s_common.genpath(coredirn, 'randodirn', 'randoslab2')
                    async with await s_lmdbslab.Slab.anit(slabpath):
                        pass

                    await proxy.delBackup('_sleeperProc')
                    await proxy.delBackup('_sleeper2Proc')
                    await proxy.delBackup('_exiterProc')

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

                    _ntuple_stat = collections.namedtuple('stat', 'st_dev st_mode st_blocks st_size')
                    _ntuple_diskusage = collections.namedtuple('usage', 'total used free')

                    def lowspace(dirn):
                        cellsize = s_common.getDirSize(coredirn)
                        return _ntuple_diskusage(1, cellsize, 1)

                    realstat = os.stat
                    def diffdev(dirn):
                        real = realstat(dirn)
                        if dirn == coredirn:
                            return _ntuple_stat(1, real.st_mode, real.st_blocks, real.st_size)
                        elif dirn == backdirn:
                            return _ntuple_stat(2, real.st_mode, real.st_blocks, real.st_size)
                        return real

                    with mock.patch('shutil.disk_usage', lowspace):
                        await self.asyncraises(s_exc.LowSpace, proxy.runBackup())

                        with mock.patch('os.stat', diffdev):
                            await self.asyncraises(s_exc.LowSpace, proxy.runBackup())

                user = await core.auth.getUserByName('root')
                with self.raises(s_exc.SynErr) as cm:
                    await core.iterNewBackupArchive(user)
                self.isin('This API must be called via a CellApi', cm.exception.get('mesg'))

            async def err(*args, **kwargs):
                raise RuntimeError('boom')

            async with self.getTestCore(dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:

                    with mock.patch('synapse.lib.coro.executor', err):
                        with self.raises(s_exc.SynErr) as cm:
                            await proxy.runBackup('partial')
                        self.eq(cm.exception.get('errx'), 'RuntimeError')

                    self.isin('partial', await proxy.getBackups())

                    await proxy.delBackup(name='partial')
                    self.notin('partial', await proxy.getBackups())

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
                self.eq(cm.exception.get('username'), 'newp@localhost')

                # add newp
                unfo = await cryo.addUser('newp@localhost')
                async with await s_telepath.openurl(f'ssl://newp@127.0.0.1:{port}?hostname=localhost') as proxy:
                    self.eq(cryo.iden, await proxy.getCellIden())

                # Lock newp
                await cryo.setUserLocked(unfo.get('iden'), True)
                with self.raises(s_exc.AuthDeny) as cm:
                    url = f'ssl://newp@127.0.0.1:{port}?hostname=localhost'
                    async with await s_telepath.openurl(url) as proxy:
                        pass

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
                await cell._storCellAuthMigration()

    async def test_cell_auth_userlimit(self):
        maxusers = 3
        conf = {
            'max:users': maxusers
        }

        async with self.getTestCell(s_cell.Cell, conf=conf) as cell:
            await cell.auth.addUser('visi1')
            await cell.auth.addUser('visi2')
            await cell.auth.addUser('visi3')
            with self.raises(s_exc.HitLimit) as exc:
                await cell.auth.addUser('visi4')
            self.eq(f'Cell at maximum number of users ({maxusers}).', exc.exception.get('mesg'))

            # Archive user and add new user
            visi1 = await cell.auth.getUserByName('visi1')
            await visi1.setArchived(True)

            await cell.auth.addUser('visi4')

            with self.raises(s_exc.HitLimit):
                await cell.auth.addUser('visi5')

            # Try to unarchive user while we're at the limit
            with self.raises(s_exc.HitLimit):
                await visi1.setArchived(False)

            # Lock user and add new user
            visi2 = await cell.auth.getUserByName('visi2')
            await visi2.setLocked(True)

            await cell.auth.addUser('visi5')

            with self.raises(s_exc.HitLimit):
                await cell.auth.addUser('visi6')

            # Delete user and add new user
            visi3 = await cell.auth.getUserByName('visi3')
            await cell.auth.delUser(visi3.iden)

            await cell.auth.addUser('visi6')

            with self.raises(s_exc.HitLimit):
                await cell.auth.addUser('visi7')

        with self.setTstEnvars(SYN_CELL_MAX_USERS=str(maxusers)):
            with self.getTestDir() as dirn:
                argv = [dirn, '--https', '0', '--telepath', 'tcp://0.0.0.0:0']
                async with await s_cell.Cell.initFromArgv(argv) as cell:
                    await cell.auth.addUser('visi1')
                    await cell.auth.addUser('visi2')
                    await cell.auth.addUser('visi3')
                    with self.raises(s_exc.HitLimit) as exc:
                        await cell.auth.addUser('visi4')
                    self.eq(f'Cell at maximum number of users ({maxusers}).', exc.exception.get('mesg'))

        with self.raises(s_exc.BadConfValu) as exc:
            async with self.getTestCell(s_cell.Cell, conf={'max:users': -1}) as cell:
                pass
        self.eq('Invalid config for max:users, data must be bigger than or equal to 0', exc.exception.get('mesg'))

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
                            self.true(core.backupstreaming)
                            bkup3.write(msg)

                    async def streamdone():
                        while core.backupstreaming:
                            await asyncio.sleep(0.1)

                    task = core.schedCoro(streamdone())
                    try:
                        await asyncio.wait_for(task, 5)
                    except TimeoutError:
                        raise TimeoutError('Timeout waiting for streaming backup cleanup of bkup3 to complete.')

                    self.eq(('bkup', 'bkup2'), sorted(await proxy.getBackups()))
                    self.false(os.path.isdir(os.path.join(backdirn, 'bkup3')))

                    # Create a new backup without a name param
                    nodes = await core.nodes('[test:str=noname]')
                    self.len(1, nodes)

                    with open(bkuppath4, 'wb') as bkup4:
                        async for msg in proxy.iterNewBackupArchive(remove=True):
                            bkup4.write(msg)

                    task = core.schedCoro(streamdone())
                    try:
                        await asyncio.wait_for(task, 5)
                    except TimeoutError:
                        raise TimeoutError('Timeout waiting for streaming backup cleanup of bkup4 to complete.')

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
            user = cell.auth.user(iden)  # type: s_auth.User
            self.eq(user.name, 'foo@bar.mynet.com')
            self.eq(user.pack().get('email'), 'foo@barcorp.com')
            self.false(user.isAdmin())
            self.true(user.allowed(('thing', 'cool')))
            self.false(user.allowed(('thing', 'del')))
            self.true(user.allowed(('thing', 'duck', 'stuff')))
            self.false(user.allowed(('newp', 'secret')))

            iden = s_common.guid((cell.iden, 'auth', 'user', 'sally@bar.mynet.com'))
            user = cell.auth.user(iden)  # type: s_auth.User
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

            self.true(evt1.wait(timeout=30))

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
                        self.true(await cell01.nexsroot.waitfini(6))

    async def test_backup_restore_base(self):

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
                        argv = [cdir, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                        async with await s_cortex.Cortex.initFromArgv(argv) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))
                            self.true(core.conf.get('storm:log'))

                    # Turning the service back on with the restore URL is fine too.
                    with self.getAsyncLoggerStream('synapse.lib.cell') as stream:
                        argv = [cdir, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                        async with await s_cortex.Cortex.initFromArgv(argv) as core:
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
                        argv = [cdir, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                        async with await s_cortex.Cortex.initFromArgv(argv) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

            # Restore a backup which has an existing restore.done file in it - that marker file will get overwritten
            furl2 = f'{url}{s_common.ehex(sha256r)}'
            with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl2):
                with self.getTestDir() as cdir:
                    # Restore works
                    with self.getAsyncLoggerStream('synapse.lib.cell',
                                                   'Restoring cortex from SYN_RESTORE_HTTPS_URL') as stream:
                        argv = [cdir, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                        async with await s_cortex.Cortex.initFromArgv(argv) as core:
                            self.true(await stream.wait(6))
                            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))

                    rpath = s_common.genpath(cdir, 'restore.done')
                    with s_common.genfile(rpath) as fd:
                        second_doneiden = fd.read().decode().strip()
                        self.true(s_common.isguid(second_doneiden))
                    self.ne(doneiden, second_doneiden)

    async def test_cell_mirrorboot_failure(self):
        async with self.getTestAha() as aha:  # type: s_aha.AhaCell

            with self.getTestDir() as dirn:
                cdr0 = s_common.genpath(dirn, 'cell00')
                cdr1 = s_common.genpath(dirn, 'cell01')

                async with self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=cdr0) as cell00:

                    conf = {'mirror': 'aha://cell...'}
                    with self.raises(s_exc.FatalErr) as cm:
                        async with self.getTestCell(conf=conf, dirn=cdr1) as cell01:
                            self.fail('Cell01 should never boot')
                    self.isin('No aha:provision configuration has been provided to allow the service to bootstrap',
                              cm.exception.get('mesg'))

                    provurl = await aha.addAhaSvcProv('01.cell', provinfo={'mirror': 'cell'})
                    conf = self.getCellConf({'aha:provision': provurl})
                    async with self.getTestCell(conf=conf, dirn=cdr1) as cell01:
                        await cell01.sync()
                    os.unlink(s_common.genpath(cdr1, 'cell.guid'))

                    conf = self.getCellConf({'aha:provision': provurl})
                    with self.raises(s_exc.FatalErr) as cm:
                        async with self.getTestCell(conf=conf, dirn=cdr1) as cell01:
                            self.fail('Cell01 should never boot')
                    self.isin('The aha:provision URL guid matches the service prov.done guid',
                              cm.exception.get('mesg'))

    async def test_backup_restore_aha(self):
        # do a mirror provisioning of a Cell
        # promote the mirror to being a leader
        # ensure the mirror has a
        # backup the mirror
        # restore the backup
        async with self.getTestAha() as aha:  # type: s_aha.AhaCell

            with self.getTestDir() as dirn:
                cdr0 = s_common.genpath(dirn, 'core00')
                cdr1 = s_common.genpath(dirn, 'core01')
                adr0 = s_common.genpath(dirn, 'axon00')
                bdr0 = s_common.genpath(dirn, 'back00')
                bdr1 = s_common.genpath(dirn, 'back01')

                async with self.addSvcToAha(aha, '00.axon', s_axon.Axon, conf={'auth:passwd': 'root'},
                                            dirn=adr0) as axon00:
                    addr, port = await axon00.addHttpsPort(0)
                    url = f'https+insecure://root:root@localhost:{port}/api/v1/axon/files/by/sha256/'

                    async with self.addSvcToAha(aha, '00.core', s_cortex.Cortex, dirn=cdr0) as core00:
                        async with self.addSvcToAha(aha, '01.core', s_cortex.Cortex, dirn=cdr1,
                                                    provinfo={'mirror': 'core'}) as core01:
                            self.len(1, await core00.nodes('[inet:asn=0]'))
                            await core01.sync()
                            self.len(1, await core01.nodes('inet:asn=0'))

                            self.true(core00.isactive)
                            self.false(core01.isactive)

                            await core01.promote(graceful=True)

                            self.true(core01.isactive)
                            self.false(core00.isactive)

                            modinfo = s_common.yamlload(core00.dirn, 'cell.mods.yaml')
                            self.isin('01.core', modinfo.get('mirror', ''))
                            modinfo = s_common.yamlload(core01.dirn, 'cell.mods.yaml')
                            self.none(modinfo.get('mirror'))

                            async with await axon00.upload() as upfd:
                                async with core00.getLocalProxy() as prox:
                                    async for chunk in prox.iterNewBackupArchive():
                                        await upfd.write(chunk)

                                    size, sha256 = await upfd.save()
                                    await asyncio.sleep(0)

                    furl = f'{url}{s_common.ehex(sha256)}'
                    purl = await aha.addAhaSvcProv('00.mynewcortex')

                    with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl,
                                           SYN_CORTEX_AHA_PROVISION=purl):
                        # Restore works
                        with self.getAsyncLoggerStream('synapse.lib.cell',
                                                       'Restoring cortex from SYN_RESTORE_HTTPS_URL') as stream:
                            argv = [bdr0, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                            async with await s_cortex.Cortex.initFromArgv(argv) as bcree00:
                                self.true(await stream.wait(6))
                                self.len(1, await bcree00.nodes('inet:asn=0'))
                                self.len(1, await bcree00.nodes('[inet:asn=1234]'))

                                rpath = s_common.genpath(bdr0, 'restore.done')
                                with s_common.genfile(rpath) as fd:
                                    doneiden = fd.read().decode().strip()
                                    self.true(s_common.isguid(doneiden))

                                # Restore the backup as a mirror of the mynewcortex
                                purl = await aha.addAhaSvcProv('01.mynewcortex',
                                                               provinfo={'mirror': 'mynewcortex'})
                                stream.clear()
                                with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl,
                                                       SYN_CORTEX_AHA_PROVISION=purl):
                                    argv = [bdr1, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                                    async with await s_cortex.Cortex.initFromArgv(argv) as bcree01:
                                        self.true(await stream.wait(6))
                                        self.true(bcree00.isactive)
                                        self.false(bcree01.isactive)

                                        await bcree01.sync()
                                        self.len(1, await bcree01.nodes('[inet:asn=8675]'))
                                        self.len(1, await bcree00.nodes('inet:asn=8675'))

    async def test_backup_restore_double_promote_aha(self):
        # do a mirror provisioning of a Cell
        # promote the mirror to being a leader
        # ensure the mirror has a
        # backup the mirror
        # restore the backup
        async with self.getTestAha() as aha:  # type: s_aha.AhaCell

            with self.getTestDir() as dirn:
                cdr0 = s_common.genpath(dirn, 'core00')
                cdr1 = s_common.genpath(dirn, 'core01')
                adr0 = s_common.genpath(dirn, 'axon00')
                bdr0 = s_common.genpath(dirn, 'back00')
                bdr1 = s_common.genpath(dirn, 'back01')

                async with self.addSvcToAha(aha, '00.axon', s_axon.Axon, conf={'auth:passwd': 'root'},
                                            dirn=adr0) as axon00:
                    addr, port = await axon00.addHttpsPort(0)
                    url = f'https+insecure://root:root@localhost:{port}/api/v1/axon/files/by/sha256/'

                    async with self.addSvcToAha(aha, '00.core', s_cortex.Cortex, dirn=cdr0) as core00:
                        async with self.addSvcToAha(aha, '01.core', s_cortex.Cortex, dirn=cdr1,
                                                    provinfo={'mirror': 'core'}) as core01:
                            self.len(1, await core00.nodes('[inet:asn=0]'))
                            await core01.sync()
                            self.len(1, await core01.nodes('inet:asn=0'))

                            self.true(core00.isactive)
                            self.false(core01.isactive)

                            await core01.promote(graceful=True)

                            self.true(core01.isactive)
                            self.false(core00.isactive)

                            modinfo = s_common.yamlload(core00.dirn, 'cell.mods.yaml')
                            self.isin('01.core', modinfo.get('mirror', ''))
                            modinfo = s_common.yamlload(core01.dirn, 'cell.mods.yaml')
                            self.none(modinfo.get('mirror'))

                            # Promote core00 back to being the leader
                            await core00.promote(graceful=True)
                            self.true(core00.isactive)
                            self.false(core01.isactive)

                            modinfo = s_common.yamlload(core00.dirn, 'cell.mods.yaml')
                            self.none(modinfo.get('mirror'))
                            modinfo = s_common.yamlload(core01.dirn, 'cell.mods.yaml')
                            self.isin('00.core', modinfo.get('mirror', ''))

                            # Backup the mirror (core01) which points to the core00
                            async with await axon00.upload() as upfd:
                                async with core01.getLocalProxy() as prox:
                                    tot_chunks = 0
                                    async for chunk in prox.iterNewBackupArchive():
                                        await upfd.write(chunk)
                                        tot_chunks += len(chunk)

                                    size, sha256 = await upfd.save()
                                    self.eq(size, tot_chunks)

                    furl = f'{url}{s_common.ehex(sha256)}'
                    purl = await aha.addAhaSvcProv('00.mynewcortex')

                    with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl,
                                           SYN_CORTEX_AHA_PROVISION=purl):
                        # Restore works
                        with self.getAsyncLoggerStream('synapse.lib.cell',
                                                       'Restoring cortex from SYN_RESTORE_HTTPS_URL') as stream:
                            argv = [bdr0, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                            async with await s_cortex.Cortex.initFromArgv(argv) as bcree00:
                                self.true(await stream.wait(6))
                                self.len(1, await bcree00.nodes('inet:asn=0'))
                                self.len(1, await bcree00.nodes('[inet:asn=1234]'))

                                rpath = s_common.genpath(bdr0, 'restore.done')
                                with s_common.genfile(rpath) as fd:
                                    doneiden = fd.read().decode().strip()
                                    self.true(s_common.isguid(doneiden))

                                # Restore the backup as a mirror of the mynewcortex
                                purl = await aha.addAhaSvcProv('01.mynewcortex',
                                                               provinfo={'mirror': 'mynewcortex'})
                                stream.clear()
                                with self.setTstEnvars(SYN_RESTORE_HTTPS_URL=furl,
                                                       SYN_CORTEX_AHA_PROVISION=purl):
                                    argv = [bdr1, '--https', '0', '--telepath', 'tcp://127.0.0.1:0']
                                    async with await s_cortex.Cortex.initFromArgv(argv) as bcree01:
                                        self.true(await stream.wait(6))
                                        self.true(bcree00.isactive)
                                        self.false(bcree01.isactive)

                                        await bcree01.sync()
                                        self.len(1, await bcree01.nodes('[inet:asn=8675]'))
                                        self.len(1, await bcree00.nodes('inet:asn=8675'))

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

        # Password policies do not prevent live migration of an existing password
        with self.getRegrDir('cells', 'passwd-2.109.0') as dirn:
            policy = {'complexity': {'length': 5}}
            conf = {'auth:passwd:policy': policy}
            async with self.getTestCell(s_cell.Cell, conf=conf, dirn=dirn) as cell:  # type: s_cell.Cell
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

    async def test_cell_minspace(self):

        with self.raises(s_exc.LowSpace):
            conf = {'limit:disk:free': 100}
            async with self.getTestCore(conf=conf) as core:
                pass

        _ntuple_diskusage = collections.namedtuple('usage', 'total used free')

        def full_disk(dirn):
            return _ntuple_diskusage(100, 96, 4)

        revt = asyncio.Event()
        addWriteHold = s_nexus.NexsRoot.addWriteHold
        delWriteHold = s_nexus.NexsRoot.delWriteHold
        async def wrapAddWriteHold(root, reason):
            retn = await addWriteHold(root, reason)
            revt.set()
            return retn

        async def wrapDelWriteHold(root, reason):
            retn = await delWriteHold(root, reason)
            revt.set()
            return retn

        errmsg = 'Insufficient free space on disk.'

        with mock.patch.object(s_cell.Cell, 'FREE_SPACE_CHECK_FREQ', 0.1), \
             mock.patch.object(s_nexus.NexsRoot, 'addWriteHold', wrapAddWriteHold), \
             mock.patch.object(s_nexus.NexsRoot, 'delWriteHold', wrapDelWriteHold):

            async with self.getTestCore() as core:

                # This tmp_reason assertion seems counter-intuitive at first; but it's really
                # asserting that the message which was incorrectly being logged is no longer logged.
                log_enable_writes = f'Free space on {core.dirn} above minimum threshold'
                with self.getAsyncLoggerStream('synapse.lib.cell', log_enable_writes) as stream:
                    await core.nexsroot.addWriteHold(tmp_reason := 'something else')
                    self.false(await stream.wait(1))
                stream.seek(0)
                self.eq(stream.read(), '')

                await core.nexsroot.delWriteHold(tmp_reason)
                revt.clear()

                self.len(1, await core.nodes('[inet:fqdn=vertex.link]'))

                with mock.patch('shutil.disk_usage', full_disk):
                    self.true(await asyncio.wait_for(revt.wait(), 1))

                    msgs = await core.stormlist('[inet:fqdn=newp.fail]')
                    self.stormIsInErr(errmsg, msgs)

                revt.clear()
                self.true(await asyncio.wait_for(revt.wait(), 1))

                self.len(1, await core.nodes('[inet:fqdn=foo.com]'))

            with self.getTestDir() as dirn:

                path00 = s_common.gendir(dirn, 'core00')
                path01 = s_common.gendir(dirn, 'core01')

                conf = {'limit:disk:free': 0}
                async with self.getTestCore(dirn=path00, conf=conf) as core00:
                    await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

                s_tools_backup.backup(path00, path01)

                async with self.getTestCore(dirn=path00, conf=conf) as core00:

                    core01conf = {'mirror': core00.getLocalUrl()}

                    async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                        await core01.sync()

                        revt.clear()
                        with mock.patch('shutil.disk_usage', full_disk):
                            self.true(await asyncio.wait_for(revt.wait(), 1))

                            msgs = await core01.stormlist('[inet:fqdn=newp.fail]')
                            self.stormIsInErr(errmsg, msgs)
                            msgs = await core01.stormlist('[inet:fqdn=newp.fail]')
                            self.stormIsInErr(errmsg, msgs)
                            self.len(1, await core00.nodes('[ inet:ipv4=2.3.4.5 ]'))

                            offs = await core00.getNexsIndx()
                            self.false(await core01.waitNexsOffs(offs, 1))

                            self.len(1, await core01.nodes('inet:ipv4=1.2.3.4'))
                            self.len(0, await core01.nodes('inet:ipv4=2.3.4.5'))
                            revt.clear()

                        revt.clear()
                        self.true(await asyncio.wait_for(revt.wait(), 1))
                        await core01.sync()

                        self.len(1, await core01.nodes('inet:ipv4=1.2.3.4'))
                        self.len(1, await core01.nodes('inet:ipv4=2.3.4.5'))

        with mock.patch.object(s_cell.Cell, 'FREE_SPACE_CHECK_FREQ', 600):

            async with self.getTestCore() as core:

                with mock.patch.object(s_lmdbslab.Slab, 'DEFAULT_MAPSIZE', 100000):
                    layr = await core.addLayer()
                    layriden = layr.get('iden')
                    view = await core.addView({'layers': (layriden,)})
                    viewiden = view.get('iden')

                    with mock.patch('shutil.disk_usage', full_disk):
                        opts = {'view': viewiden}
                        msgs = await core.stormlist('for $x in $lib.range(20000) {[inet:ipv4=$x]}', opts=opts)
                        self.stormIsInErr(errmsg, msgs)
                        nodes = await core.nodes('inet:ipv4', opts=opts)
                        self.gt(len(nodes), 0)
                        self.lt(len(nodes), 20000)

            async with self.getTestCore() as core:

                def spaceexc(self):
                    raise Exception('foo')

                with mock.patch.object(s_lmdbslab.Slab, 'DEFAULT_MAPSIZE', 100000), \
                     mock.patch.object(s_cell.Cell, 'checkFreeSpace', spaceexc):
                    layr = await core.addLayer()
                    layriden = layr.get('iden')
                    view = await core.addView({'layers': (layriden,)})
                    viewiden = view.get('iden')

                    opts = {'view': viewiden}
                    with self.getLoggerStream('synapse.lib.lmdbslab',
                                              'Error during slab resize callback - foo') as stream:
                        nodes = await core.stormlist('for $x in $lib.range(200) {[inet:ipv4=$x]}', opts=opts)
                        self.true(stream.wait(1))

        async with self.getTestCore() as core:

            await core.nexsroot.addWriteHold('LOLWRITE TESTING')

            msgs = await core.stormlist('[inet:fqdn=newp.fail]')

            self.stormIsInErr('LOLWRITE TESTING', msgs)

            await core.nexsroot.delWriteHold('LOLWRITE TESTING')

            core.nexsroot.readonly = True
            with self.raises(s_exc.IsReadOnly):
                core.nexsroot.reqNotReadOnly()

    async def test_cell_onboot_optimize(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                layriden = await core.callStorm('return($lib.layer.get().iden)')

                # to test run the tmp cleanup on boot logic
                with s_common.genfile(dirn, 'tmp', 'junk.text') as fd:
                    fd.write(b'asdf\n')

                tmpd = s_common.gendir(dirn, 'tmp', 'hehe')
                with s_common.genfile(tmpd, 'haha.text') as fd:
                    fd.write(b'lolz\n')

            lmdbfile = s_common.genpath(dirn, 'layers', layriden, 'layer_v2.lmdb', 'data.mdb')
            stat00 = os.stat(lmdbfile)

            with self.getAsyncLoggerStream('synapse.lib.cell') as stream:

                conf = {'onboot:optimize': True}
                async with self.getTestCore(dirn=dirn, conf=conf) as core:
                    pass

            stream.seek(0)
            self.isin('onboot optimization complete!', stream.read())

            stat01 = os.stat(lmdbfile)
            self.ne(stat00.st_ino, stat01.st_ino)

            _ntuple_stat = collections.namedtuple('stat', 'st_dev st_mode st_blocks st_size')
            realstat = os.stat
            def diffdev(path):
                real = realstat(path)
                if path.endswith('mdb'):
                    return _ntuple_stat(1, real.st_mode, real.st_blocks, real.st_size)
                elif path.endswith('tmp'):
                    return _ntuple_stat(2, real.st_mode, real.st_blocks, real.st_size)
                return real

            with mock.patch('os.stat', diffdev):
                with self.getAsyncLoggerStream('synapse.lib.cell') as stream:

                    conf = {'onboot:optimize': True}
                    async with self.getTestCore(dirn=dirn, conf=conf) as core:
                        pass

                stream.seek(0)
                buf = stream.read()
                self.notin('onboot optimization complete!', buf)
                self.isin('not on the same volume', buf)

            # Local backup files are skipped
            async with self.getTestCore(dirn=dirn) as core:
                await core.runBackup()

            with self.getAsyncLoggerStream('synapse.lib.cell') as stream:

                conf = {'onboot:optimize': True}
                async with self.getTestCore(dirn=dirn, conf=conf) as core:
                    pass

            stream.seek(0)
            buf = stream.read()
            self.isin('Skipping backup file', buf)
            self.isin('onboot optimization complete!', buf)

    async def test_cell_gc(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy() as proxy:
                self.nn(await proxy.runGcCollect())
                info = await proxy.getGcInfo()
                self.nn(info['stats'])
                self.nn(info['threshold'])

    async def test_cell_reload_api(self):
        async with self.getTestCell(s_t_utils.ReloadCell) as cell:  # type: s_t_utils.ReloadCell
            async with cell.getLocalProxy() as prox:

                # No registered reload functions yet
                names = await prox.getReloadableSystems()
                self.len(0, names)
                # No functions to run yet
                self.eq({}, await prox.reload())

                # Add reload func and get its name
                await cell.addTestReload()
                names = await prox.getReloadableSystems()
                self.len(1, names)
                name = names[0]

                # Reload by name
                self.false(cell._reloaded)
                self.eq({name: (True, True)}, await cell.reload(name))
                self.true(cell._reloaded)

                # Add a second function
                await cell.addTestBadReload()

                # Reload all registered functions
                cell._reloaded = False
                ret = await cell.reload()
                self.eq(ret.get('testreload'), (True, True))
                fail = ret.get('badreload')
                self.false(fail[0])
                self.eq('ZeroDivisionError', fail[1][0])
                self.eq('division by zero', fail[1][1].get('mesg'))
                self.true(cell._reloaded)

                # Attempting to call a value by name that doesn't exist fails
                with self.raises(s_exc.NoSuchName) as cm:
                    await cell.reload(subsystem='newp')
                self.eq('newp', cm.exception.get('name'))
                self.isin('newp', cm.exception.get('mesg'))

    async def test_cell_reload_sighup(self):

        with self.getTestDir() as dirn:

            ctx = multiprocessing.get_context('spawn')

            evt1 = ctx.Event()
            evt2 = ctx.Event()

            proc = ctx.Process(target=reload_target, args=(dirn, evt1, evt2))
            proc.start()

            self.true(evt1.wait(timeout=30))

            async with await s_telepath.openurl(f'cell://{dirn}') as prox:
                cnfo = await prox.getCellInfo()
                self.false(cnfo.get('cell', {}).get('reloaded'))

                os.kill(proc.pid, signal.SIGHUP)
                evt2.wait(timeout=10)

                cnfo = await prox.getCellInfo()
                self.true(cnfo.get('cell', {}).get('reloaded'))

            os.kill(proc.pid, signal.SIGTERM)
            proc.join(timeout=10)
            self.eq(proc.exitcode, 137)

    async def test_cell_reload_https(self):
        async with self.getTestCell(s_t_utils.ReloadCell) as cell:  # type: s_t_utils.ReloadCell
            async with cell.getLocalProxy() as prox:

                await cell.auth.rootuser.setPasswd('root')
                hhost, hport = await cell.addHttpsPort(0, host='127.0.0.1')

                names = await prox.getReloadableSystems()
                self.ge(len(names), 1)

                bitems = []
                bstrt = asyncio.Event()
                bdone = asyncio.Event()

                def get_pem_cert():
                    # Only run this in a executor thread
                    ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    conn = socket.create_connection((hhost, hport))
                    sock = ctx.wrap_socket(conn)
                    sock.settimeout(60)
                    der_cert = sock.getpeercert(binary_form=True)
                    sock.close()
                    conn.close()
                    return ssl.DER_cert_to_PEM_cert(der_cert)

                original_cert = await s_coro.executor(get_pem_cert)
                ocert = c_x509.load_pem_x509_certificate(original_cert.encode())
                cname = ocert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
                self.eq(cname, 'reloadcell')

                # Start a beholder session that runs over TLS

                async with self.getHttpSess(auth=('root', 'root'), port=hport) as bsess:

                    async with bsess.ws_connect(f'wss://localhost:{hport}/api/v1/behold') as sock:

                        async def beholdConsumer():
                            await sock.send_json({'type': 'call:init'})
                            bstrt.set()
                            while not cell.isfini:
                                mesg = await sock.receive_json()
                                data = mesg.get('data')
                                if data.get('event') == 'user:add':
                                    bitems.append(data)
                                if len(bitems) == 2:
                                    bdone.set()
                                    break

                        fut = cell.schedCoro(beholdConsumer())
                        self.true(await asyncio.wait_for(bstrt.wait(), timeout=12))

                        async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                            resp = await sess.get(f'https://localhost:{hport}/api/v1/healthcheck')
                            answ = await resp.json()
                            self.eq('ok', answ['status'])

                        await cell.addUser('alice')

                        # Generate and save new SSL material....
                        pkeypath = os.path.join(cell.dirn, 'sslkey.pem')
                        certpath = os.path.join(cell.dirn, 'sslcert.pem')

                        tdir = s_common.gendir(cell.dirn, 'tmp')
                        with s_common.getTempDir(dirn=tdir) as dirn:
                            cdir = s_certdir.CertDir(path=(dirn,))
                            pkey, cert = cdir.genHostCert('SomeTestCertificate')
                            cdir.savePkeyPem(pkey, pkeypath)
                            cdir.saveCertPem(cert, certpath)

                        # reload listeners
                        await cell.reload()

                        reloaded_cert = await s_coro.executor(get_pem_cert)
                        rcert = c_x509.load_pem_x509_certificate(reloaded_cert.encode())
                        rname = rcert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)[0].value
                        self.eq(rname, 'SomeTestCertificate')

                        async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                            resp = await sess.get(f'https://localhost:{hport}/api/v1/healthcheck')
                            answ = await resp.json()
                            self.eq('ok', answ['status'])

                        await cell.addUser('bob')

                        self.true(await asyncio.wait_for(bdone.wait(), timeout=12))
                        await fut

                        users = {m.get('info', {}).get('name') for m in bitems}
                        self.eq(users, {'alice', 'bob'})

    async def test_cell_user_api_key(self):
        async with self.getTestCell(s_cell.Cell) as cell:

            await cell.auth.rootuser.setPasswd('root')
            root = cell.auth.rootuser.iden

            lowuser = await cell.addUser('lowuser')
            lowuser = lowuser.get('iden')

            hhost, hport = await cell.addHttpsPort(0, host='127.0.0.1')

            rtk0, rtdf0 = await cell.addUserApiKey(root, name='Test Token')
            bkk0, bkdf0 = await cell.addUserApiKey(root, name='Backup Token')

            self.notin('exipres', rtdf0)

            async with cell.getLocalProxy() as prox:
                isok, valu = await prox.checkUserApiKey(rtk0)
            self.true(isok)
            self.eq(valu.get('kdef'), rtdf0)
            udef = valu.get('udef')
            self.eq(udef.get('iden'), root)
            self.eq(udef.get('name'), 'root')

            isok, valu = await cell.checkUserApiKey(rtk0 + 'newp')
            self.false(isok)
            self.eq(valu, {'mesg': 'API key is malformed.'})

            badkey = base64.b64encode(s_common.uhex(rtdf0.get('iden')) + b'X' * 16, altchars=b'-_').decode('utf-8')
            isok, valu = await cell.checkUserApiKey(badkey)
            self.false(isok)
            self.eq(valu, {'mesg': f'API key shadow mismatch: {rtdf0.get("iden")}',
                           'user': root, 'name': 'root'})

            allkeys = []
            async for kdef in cell.getApiKeys():
                allkeys.append(kdef)
            self.len(2, allkeys)
            _kdefs = [rtdf0, bkdf0]
            for kdef in allkeys:
                self.eq(kdef.get('user'), root)
                self.isin(kdef, _kdefs)
                _kdefs.remove(kdef)
            self.len(0, _kdefs)

            rootkeys = await cell.listUserApiKeys(root)
            self.eq(allkeys, rootkeys)

            lowkeys = await cell.listUserApiKeys(lowuser)
            self.len(0, lowkeys)

            async with self.getHttpSess(port=hport) as sess:

                headers0 = {'X-API-KEY': rtk0}

                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', headers=headers0,
                                       json={'user': lowuser})
                answ = await resp.json()
                self.eq('ok', answ['status'])

                resp = await sess.get(f'https://localhost:{hport}/api/v1/auth/roles', headers=headers0)
                answ = await resp.json()
                self.eq('ok', answ['status'])

            # Change the token name
            rtdf0_new = await cell.modUserApiKey(rtdf0.get('iden'), 'name', 'Haha Key')
            self.eq(rtdf0_new.get('name'), 'Haha Key')

            # Verify duration arg for expiration is applied
            with self.raises(s_exc.BadArg):
                await cell.addUserApiKey(root, 'newp', duration=0)
            rtk1, rtdf1 = await cell.addUserApiKey(root, 'Expiring Token', duration=200)
            self.eq(rtdf1.get('expires'), rtdf1.get('updated') + 200)

            isok, info = await cell.checkUserApiKey(rtk1)
            self.true(isok)

            await asyncio.sleep(0.4)

            isok, info = await cell.checkUserApiKey(rtk1)
            self.false(isok)
            self.isin('API key is expired', info.get('mesg'))

            # Expired tokens fail...
            async with self.getHttpSess(port=hport) as sess:

                # Expired token fails
                headers2 = {'X-API-KEY': rtk1}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', headers=headers2,
                                       json={'user': lowuser})
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                answ = await resp.json()
                self.eq('err', answ['status'])

            await cell.delUserApiKey(rtdf1.get('iden'))

            rtk3, rtdf3 = await cell.addUserApiKey(root, name='Test Token 3')

            async with self.getHttpSess(port=hport) as sess:

                # New token works
                headers2 = {'X-API-KEY': rtk3}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', headers=headers2,
                                       json={'user': lowuser})
                answ = await resp.json()
                self.eq('ok', answ['status'])

                # Delete the token - it no longer works
                await cell.delUserApiKey(rtdf3.get('iden'))

                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', headers=headers2,
                                       json={'user': lowuser})
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                answ = await resp.json()
                self.eq('err', answ['status'])

                # Backup token works
                headers2 = {'X-API-KEY': bkk0}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/onepass/issue', headers=headers2,
                                       json={'user': lowuser})
                answ = await resp.json()
                self.eq('ok', answ['status'])

            # Generate an API key for lowuser and delete the user. The token should be deleted as well.
            ltk0, ltdf0 = await cell.addUserApiKey(lowuser, name='Visi Token')
            self.eq(lowuser, ltdf0.get('user'))

            async with self.getHttpSess(port=hport) as sess:

                # New token works
                headers2 = {'X-API-KEY': ltk0}
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/password/{lowuser}', headers=headers2,
                                       json={'passwd': 'secret'})
                answ = await resp.json()
                self.eq('ok', answ['status'])

                # Make some additional keys that will be deleted
                ktup0 = await cell.addUserApiKey(lowuser, name='1', duration=1)
                ktup1 = await cell.addUserApiKey(lowuser, name='2', duration=1)
                ktup2 = await cell.addUserApiKey(lowuser, name='3', duration=1)
                ktup3 = await cell.addUserApiKey(lowuser, name='4', duration=1)

                # We have bunch of API keys we can list
                allkeys = []
                async for kdef in cell.getApiKeys():
                    allkeys.append(kdef)
                self.len(5 + 2, allkeys)  # Root has two, lowuser has 5

                # Lock users cannot use their API keys
                await cell.setUserLocked(lowuser, True)
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/password/{lowuser}', headers=headers2,
                                       json={'passwd': 'secret'})
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                answ = await resp.json()
                self.eq('err', answ['status'])

                await cell.delUser(lowuser)
                resp = await sess.post(f'https://localhost:{hport}/api/v1/auth/password/{lowuser}', headers=headers2,
                                       json={'passwd': 'secret'})
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                answ = await resp.json()
                self.eq('err', answ['status'])

            with self.raises(s_exc.NoSuchUser):  # user was deleted...
                await cell.listUserApiKeys(lowuser)
            rootkeys = await cell.listUserApiKeys(root)
            self.len(2, rootkeys)  # Root has two

            # Ensure User meta was cleaned up from the user deletion, as well as
            # the api key db. Only two root keys should be left
            vals = set()
            # for key, vals in cell.slab.scanByPref(lowuse)
            i = 0
            for lkey, val in cell.slab.scanByFull(cell.usermetadb):
                i = i + 1
                suffix = lkey[16:]
                if suffix.startswith(b'apikey'):
                    kdef = s_msgpack.un(val)
                    vals.add(kdef.get('iden'))
            self.eq(i, 2)
            self.eq(vals, {bkdf0.get('iden'), rtdf0.get('iden')})

            i = 0
            users = set()
            for lkey, val in cell.slab.scanByFull(cell.apikeydb):
                i = i + 1
                users.add(s_common.ehex(val))
            self.eq(i, 2)
            self.eq(users, {root, })

            # Sad path coverage
            with self.raises(s_exc.BadArg):
                await cell.modUserApiKey(bkdf0.get('iden'), 'shadow', {'hehe': 'haha'})

            newp = s_common.guid()

            with self.raises(s_exc.NoSuchUser):
                await cell.addUserApiKey(newp, 'newp')

            with self.raises(s_exc.NoSuchIden):
                await cell.modUserApiKey(newp, 'name', 'newp')

            with self.raises(s_exc.NoSuchIden):
                await cell.delUserApiKey(newp)

    async def test_cell_iter_slab_data(self):
        async with self.getTestCell(s_cell.Cell) as cell:
            data = await s_t_utils.alist(cell.iterSlabData('cell:info'))
            self.eq(data, (
                ('cell:version', s_version.version),
                ('nexus:version', s_cell.NEXUS_VERSION),
                ('synapse:version', s_version.version)
            ))
            with self.raises(s_exc.BadArg):
                await s_t_utils.alist(cell.iterSlabData('newp'))

            sfkv = cell.slab.getSafeKeyVal('hehe', prefix='yup')
            sfkv.set('wow', 'yes')
            data = await s_t_utils.alist(cell.iterSlabData('hehe'))
            self.eq(data, [('yupwow', 'yes')])
            data = await s_t_utils.alist(cell.iterSlabData('hehe', prefix='yup'))
            self.eq(data, [('wow', 'yes')])

    async def test_cell_nexus_compat(self):
        with mock.patch('synapse.lib.cell.NEXUS_VERSION', (0, 0)):
            async with self.getRegrCore('hive-migration') as core0:
                with mock.patch('synapse.lib.cell.NEXUS_VERSION', (2, 177)):
                    conf = {'mirror': core0.getLocalUrl()}
                    async with self.getRegrCore('hive-migration', conf=conf) as core1:
                        await core1.sync()

                        await core1.nodes('$lib.user.vars.set(foo, bar)')
                        self.eq('bar', await core0.callStorm('return($lib.user.vars.get(foo))'))

                        await core1.nodes('$lib.user.vars.pop(foo)')
                        self.none(await core0.callStorm('return($lib.user.vars.get(foo))'))

                        await core1.nodes('$lib.user.profile.set(bar, baz)')
                        self.eq('baz', await core0.callStorm('return($lib.user.profile.get(bar))'))

                        await core1.nodes('$lib.user.profile.pop(bar)')
                        self.none(await core0.callStorm('return($lib.user.profile.get(bar))'))

                        self.eq((0, 0), core1.nexsvers)
                        await core0.setNexsVers((2, 177))
                        await core1.sync()
                        self.eq((2, 177), core1.nexsvers)

                        await core1.nodes('$lib.user.vars.set(foo, bar)')
                        self.eq('bar', await core0.callStorm('return($lib.user.vars.get(foo))'))

                        await core1.nodes('$lib.user.vars.pop(foo)')
                        self.none(await core0.callStorm('return($lib.user.vars.get(foo))'))

                        await core1.nodes('$lib.user.profile.set(bar, baz)')
                        self.eq('baz', await core0.callStorm('return($lib.user.profile.get(bar))'))

                        await core1.nodes('$lib.user.profile.pop(bar)')
                        self.none(await core0.callStorm('return($lib.user.profile.get(bar))'))

    async def test_cell_hive_migration(self):

        with self.getAsyncLoggerStream('synapse.lib.cell') as stream:

            async with self.getRegrCore('hive-migration') as core:
                visi = await core.auth.getUserByName('visi')
                asvisi = {'user': visi.iden}

                valu = await core.callStorm('return($lib.user.vars.get(foovar))', opts=asvisi)
                self.eq('barvalu', valu)

                valu = await core.callStorm('return($lib.user.profile.get(fooprof))', opts=asvisi)
                self.eq('barprof', valu)

                msgs = await core.stormlist('cron.list')
                self.stormIsInPrint(' visi                      8437c35a.. ', msgs)
                self.stormIsInPrint('[tel:mob:telem=*]', msgs)

                msgs = await core.stormlist('dmon.list')
                self.stormIsInPrint('0973342044469bc40b577969028c5079:  (foodmon             ): running', msgs)

                msgs = await core.stormlist('trigger.list')
                self.stormIsInPrint('visi       27f5dc524e7c3ee8685816ddf6ca1326', msgs)
                self.stormIsInPrint('[ +#count test:str=$tag ]', msgs)

                msgs = await core.stormlist('testcmd0 foo')
                self.stormIsInPrint('foo haha', msgs)

                msgs = await core.stormlist('testcmd1')
                self.stormIsInPrint('hello', msgs)

                msgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('ou:hasalias', msgs)

                nodes = await core.nodes('_visi:int')
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.get('tick'), 1577836800000,)
                self.eq(node.get('._woot'), 5)
                self.nn(node.getTagProp('test', 'score'), 6)

                self.maxDiff = None
                roles = s_t_utils.deguidify('[{"type":"role","iden":"e1ef725990aa62ae3c4b98be8736d89f","name":"all","rules":[],"authgates":{"46cfde2c1682566602860f8df7d0cc83":{"rules":[[true,["layer","read"]]]},"4d50eb257549436414643a71e057091a":{"rules":[[true,["view","read"]]]}}}]')
                users = s_t_utils.deguidify('[{"type":"user","iden":"a357138db50780b62093a6ce0d057fd8","name":"root","rules":[],"roles":[],"admin":true,"email":null,"locked":false,"archived":false,"authgates":{"46cfde2c1682566602860f8df7d0cc83":{"admin":true},"4d50eb257549436414643a71e057091a":{"admin":true}}},{"type":"user","iden":"f77ac6744671a845c27e571071877827","name":"visi","rules":[[true,["cron","add"]],[true,["dmon","add"]],[true,["trigger","add"]]],"roles":[{"type":"role","iden":"e1ef725990aa62ae3c4b98be8736d89f","name":"all","rules":[],"authgates":{"46cfde2c1682566602860f8df7d0cc83":{"rules":[[true,["layer","read"]]]},"4d50eb257549436414643a71e057091a":{"rules":[[true,["view","read"]]]}}}],"admin":false,"email":null,"locked":false,"archived":false,"authgates":{"f21b7ae79c2dacb89484929a8409e5d8":{"admin":true},"d7d0380dd4e743e35af31a20d014ed48":{"admin":true}}}]')
                gates = s_t_utils.deguidify('[{"iden":"46cfde2c1682566602860f8df7d0cc83","type":"layer","users":[{"iden":"a357138db50780b62093a6ce0d057fd8","rules":[],"admin":true}],"roles":[{"iden":"e1ef725990aa62ae3c4b98be8736d89f","rules":[[true,["layer","read"]]],"admin":false}]},{"iden":"d7d0380dd4e743e35af31a20d014ed48","type":"trigger","users":[{"iden":"f77ac6744671a845c27e571071877827","rules":[],"admin":true}],"roles":[]},{"iden":"f21b7ae79c2dacb89484929a8409e5d8","type":"cronjob","users":[{"iden":"f77ac6744671a845c27e571071877827","rules":[],"admin":true}],"roles":[]},{"iden":"4d50eb257549436414643a71e057091a","type":"view","users":[{"iden":"a357138db50780b62093a6ce0d057fd8","rules":[],"admin":true}],"roles":[{"iden":"e1ef725990aa62ae3c4b98be8736d89f","rules":[[true,["view","read"]]],"admin":false}]},{"iden":"cortex","type":"cortex","users":[],"roles":[]}]')

                self.eq(roles, s_t_utils.deguidify(s_json.dumps(await core.callStorm('return($lib.auth.roles.list())')).decode()))
                self.eq(users, s_t_utils.deguidify(s_json.dumps(await core.callStorm('return($lib.auth.users.list())')).decode()))
                self.eq(gates, s_t_utils.deguidify(s_json.dumps(await core.callStorm('return($lib.auth.gates.list())')).decode()))

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes('[ it:dev:str=foo +#test.newp ]')

        stream.seek(0)
        data = stream.getvalue()
        newprole = s_common.guid('newprole')
        newpuser = s_common.guid('newpuser')

        self.isin(f'Unknown user {newpuser} on gate', data)
        self.isin(f'Unknown role {newprole} on gate', data)
        self.isin(f'Unknown role {newprole} on user', data)

    async def test_cell_check_sysctl(self):
        sysctls = s_linux.getSysctls()

        sysvals = s_cell.Cell.SYSCTL_VALS.copy()
        sysvals['vm.dirty_expire_centisecs'] += 1
        sysvals['vm.dirty_writeback_centisecs'] += 1

        # Detect and report incorrect values
        with self.getStructuredAsyncLoggerStream('synapse.lib.cell') as stream:
            with mock.patch.object(s_cell.Cell, 'SYSCTL_VALS', sysvals):
                async with self.getTestCore(conf={'health:sysctl:checks': True}):
                    pass

        msgs = stream.jsonlines()

        self.len(1, msgs)

        mesg = f'Sysctl values different than expected: {", ".join(sysvals)}. '
        mesg += 'See https://synapse.docs.vertex.link/en/latest/synapse/devopsguide.html#performance-tuning '
        mesg += 'for information about these sysctl parameters.'
        self.eq(msgs[0]['message'], mesg)
        self.eq(msgs[0]['sysctls'], [
            {'name': 'vm.dirty_expire_centisecs', 'expected': 21, 'actual': sysctls['vm.dirty_expire_centisecs']},
            {'name': 'vm.dirty_writeback_centisecs', 'expected': 21, 'actual': sysctls['vm.dirty_writeback_centisecs']},
        ])

        # Copy the current sysctl valus to the cell so the check passes
        sysvals = {
            'vm.dirty_expire_centisecs': sysctls['vm.dirty_expire_centisecs'],
            'vm.dirty_writeback_centisecs': sysctls['vm.dirty_writeback_centisecs'],
        }

        # Detect correct values and stop the task
        with self.getLoggerStream('synapse.lib.cell') as stream:
            with mock.patch.object(s_cell.Cell, 'SYSCTL_VALS', sysvals):
                async with self.getTestCore():
                    pass

        stream.seek(0)
        data = stream.read()
        self.len(0, data)

        # Disable the sysctl check and don't check at all
        with self.getLoggerStream('synapse.lib.cell') as stream:
            conf = {'health:sysctl:checks': False}
            async with self.getTestCore(conf=conf):
                pass

        stream.seek(0)
        data = stream.read()
        self.len(0, data, msg=data)

    async def test_cell_version_regression(self):
        oldver = (0, 1, 0)
        newver = (0, 2, 0)

        class TestCell(s_cell.Cell):
            VERSION = newver

        with self.getTestDir() as dirn:
            async with self.getTestCell(TestCell, dirn=dirn):
                pass

            with self.raises(s_exc.BadVersion) as exc:
                with mock.patch.object(TestCell, 'VERSION', oldver):
                    with self.getLoggerStream('synapse.lib.cell') as stream:
                        async with self.getTestCell(TestCell, dirn=dirn):
                            pass

            mesg = f'Cell version regression (testcell) is not allowed! Stored version: {newver}, current version: {oldver}.'
            self.eq(exc.exception.get('mesg'), mesg)
            self.eq(exc.exception.get('currver'), oldver)
            self.eq(exc.exception.get('lastver'), newver)

            stream.seek(0)
            data = stream.read()
            self.isin(mesg, data)

            async with self.getTestCell(TestCell, dirn=dirn):
                pass

        with self.getTestDir() as dirn:
            async with self.getTestCell(s_cell.Cell, dirn=dirn):
                pass

            synver = list(s_version.version)
            synver[1] -= 1
            synver = tuple(synver)

            with self.raises(s_exc.BadVersion) as exc:
                with mock.patch.object(s_version, 'version', synver):
                    with self.getLoggerStream('synapse.lib.cell') as stream:
                        async with self.getTestCell(s_cell.Cell, dirn=dirn):
                            pass

            mesg = f'Synapse version regression (cell) is not allowed! Stored version: {s_version.version}, current version: {synver}.'
            self.eq(exc.exception.get('mesg'), mesg)
            self.eq(exc.exception.get('currver'), synver)
            self.eq(exc.exception.get('lastver'), s_version.version)

            stream.seek(0)
            data = stream.read()
            self.isin(mesg, data)

            async with self.getTestCell(s_cell.Cell, dirn=dirn):
                pass

    async def test_cell_initslab_fini(self):
        class SlabCell(s_cell.Cell):
            async def initServiceStorage(self):
                self.long_lived_slab = await self._initSlabFile(os.path.join(self.dirn, 'slabs', 'long.lmdb'))
                short_slab = await self._initSlabFile(os.path.join(self.dirn, 'slabs', 'short.lmdb'), ephemeral=True)
                self.short_slab_path = short_slab.lenv.path()
                await short_slab.fini()

        async with self.getTestCell(SlabCell) as cell:
            self.true(os.path.isdir(cell.short_slab_path))
            self.isin(cell.long_lived_slab.fini, cell._fini_funcs)
            slabs = [s for s in cell.tofini if isinstance(s, s_lmdbslab.Slab) and s.lenv.path() == cell.short_slab_path]
            self.len(0, slabs)

    async def test_lib_cell_promote_schism_prevent(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    dirn00 = s_common.genpath(dirn, '00.cell')
                    dirn01 = s_common.genpath(dirn, '01.cell')
                    dirn02 = s_common.genpath(dirn, '02.cell')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00.cell', s_cell.Cell, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01.cell', s_cell.Cell, dirn=dirn01,
                                                                       provinfo={'mirror': 'cell'}))
                    cell02 = await base.enter_context(self.addSvcToAha(aha, '02.cell', s_cell.Cell, dirn=dirn02,
                                                                       provinfo={'mirror': 'cell'}))

                    self.true(cell00.isactive)
                    self.false(cell01.isactive)
                    self.false(cell02.isactive)
                    await cell02.sync()

                    with self.raises(s_exc.BadState) as cm:
                        await cell01.handoff('some://url')
                    self.isin('01.cell is not the current leader', cm.exception.get('mesg'))

                    # Note: The following behavior may change when SYN-7659 is addressed and greater
                    # control over the topology update is available during the promotion process.
                    # Promote 02.cell -> Promote 01.cell -> Promote 00.cell -> BadState exception
                    await cell02.promote(graceful=True)
                    self.false(cell00.isactive)
                    self.false(cell01.isactive)
                    self.true(cell02.isactive)
                    await cell02.sync()

                    await cell01.promote(graceful=True)
                    self.false(cell00.isactive)
                    self.true(cell01.isactive)
                    self.false(cell02.isactive)
                    await cell02.sync()

                    with self.raises(s_exc.BadState) as cm:
                        await cell00.promote(graceful=True)
                    self.isin('02.cell is not the current leader', cm.exception.get('mesg'))

    async def test_cell_get_aha_proxy(self):

        async with self.getTestCell() as cell:

            self.none(await cell.getAhaProxy())

            class MockAhaClient:
                def __init__(self, proxy=None):
                    self._proxy = proxy

                async def proxy(self, timeout=None):
                    return self._proxy

            with self.getAsyncLoggerStream('synapse.lib.cell', 'AHA client connection failed.') as stream:
                cell.ahaclient = MockAhaClient()
                self.none(await cell.getAhaProxy())
                self.true(await stream.wait(timeout=1))

            class MockProxyHasNot:
                def _hasTeleFeat(self, name, vers):
                    return False

            cell.ahaclient = MockAhaClient(proxy=MockProxyHasNot())
            self.none(await cell.getAhaProxy(feats=(('test', 1),)))

            class MockProxyHas:
                def _hasTeleFeat(self, name, vers):
                    return True

            mock_proxy = MockProxyHas()
            cell.ahaclient = MockAhaClient(proxy=mock_proxy)
            self.eq(await cell.getAhaProxy(), mock_proxy)
            self.eq(await cell.getAhaProxy(feats=(('test', 1),)), mock_proxy)

    async def test_lib_cell_sadaha(self):

        async with self.getTestCell() as cell:

            self.none(await cell.getAhaProxy())
            cell.ahaclient = await s_telepath.Client.anit('cell:///tmp/newp')

            # coverage for failure of aha client to connect
            with self.raises(TimeoutError):
                self.none(await cell.getAhaProxy(timeout=0.1))

    async def test_stream_backup_exception(self):

        with self.getTestDir() as dirn:
            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')

            conf = {'backup:dir': backdirn}
            s_common.yamlsave(conf, coredirn, 'cell.yaml')

            async with self.getTestCore(dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:

                    await proxy.runBackup(name='bkup')

                    mock_proc = mock.Mock()
                    mock_proc.join = mock.Mock()

                    async def mock_executor(func, *args, **kwargs):
                        if isinstance(func, mock.Mock) and func is mock_proc.join:
                            raise Exception('boom')
                        return mock_proc

                    with mock.patch('synapse.lib.cell.s_coro.executor', mock_executor):
                        with self.getAsyncLoggerStream('synapse.lib.cell', 'Error during backup streaming') as stream:
                            with self.raises(Exception) as cm:
                                async for _ in proxy.iterBackupArchive('bkup'):
                                    pass
                            self.true(await stream.wait(timeout=6))

    async def test_iter_new_backup_archive(self):

        with self.getTestDir() as dirn:
            backdirn = os.path.join(dirn, 'backups')
            coredirn = os.path.join(dirn, 'cortex')

            conf = {'backup:dir': backdirn}
            s_common.yamlsave(conf, coredirn, 'cell.yaml')

            async with self.getTestCore(dirn=coredirn) as core:
                async with core.getLocalProxy() as proxy:

                    async def mock_runBackup(*args, **kwargs):
                        raise Exception('backup failed')

                    with mock.patch.object(s_cell.Cell, 'runBackup', mock_runBackup):
                        with self.getAsyncLoggerStream('synapse.lib.cell', 'Removing') as stream:
                            with self.raises(s_exc.SynErr) as cm:
                                async for _ in proxy.iterNewBackupArchive('failedbackup', remove=True):
                                    pass

                            self.isin('backup failed', str(cm.exception))
                            self.true(await stream.wait(timeout=6))

                            path = os.path.join(backdirn, 'failedbackup')
                            self.false(os.path.exists(path))

                    self.false(core.backupstreaming)

                    core.backupstreaming = True
                    with self.raises(s_exc.BackupAlreadyRunning):
                        async for _ in proxy.iterNewBackupArchive('newbackup', remove=True):
                            pass

    async def test_cell_peer_noaha(self):

        todo = s_common.todo('newp')
        async with self.getTestCell() as cell:
            async for item in cell.callPeerApi(todo):
                pass
            async for item in cell.callPeerGenr(todo):
                pass

    async def test_cell_task_apis(self):
        async with self.getTestAha() as aha:

            # test some of the gather API implementations...
            purl00 = await aha.addAhaSvcProv('00.cell')
            purl01 = await aha.addAhaSvcProv('01.cell', provinfo={'mirror': 'cell'})

            cell00 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl00}))
            cell01 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl01}))

            await cell01.sync()

            async def sleep99(cell):
                await cell.boss.promote('sleep99', cell.auth.rootuser)
                await cell00.fire('sleep99')
                await asyncio.sleep(99)

            async with cell00.waiter(2, 'sleep99', timeout=6):
                task00 = cell00.schedCoro(sleep99(cell00))
                task01 = cell01.schedCoro(sleep99(cell01))

            tasks = [task async for task in cell00.getTasks(timeout=6)]

            self.len(2, tasks)
            self.eq(tasks[0]['service'], '00.cell.synapse')
            self.eq(tasks[1]['service'], '01.cell.synapse')
            self.eq(('sleep99', 'sleep99'), [task.get('name') for task in tasks])
            self.eq(('root', 'root'), [task.get('username') for task in tasks])

            self.eq(tasks[0], await cell00.getTask(tasks[0].get('iden')))
            self.eq(tasks[1], await cell00.getTask(tasks[1].get('iden')))
            self.none(await cell00.getTask(tasks[1].get('iden'), peers=False))

            self.true(await cell00.killTask(tasks[0].get('iden')))

            task01 = tasks[1].get('iden')
            self.false(await cell00.killTask(task01, peers=False))

            self.true(await cell00.killTask(task01))

            self.none(await cell00.getTask(task01))
            self.false(await cell00.killTask(task01))
