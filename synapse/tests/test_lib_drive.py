import os

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.drive as s_drive
import synapse.lib.config as s_config

import synapse.tests.utils as s_t_utils

async def migrate_v1(info, versinfo, data, curv):
    assert curv == 1
    data['woot'] = 'woot'
    return data

def migrate_not_coro(*args):
    pass

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
        'blorp': {
            'type': 'object',
            'properties': {
                'bleep': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'neato': {'type': 'string'}
                        }
                    }
                }
            }
        }
    },
    'required': ['type', 'size', 'woot'],
    'additionalProperties': False,
}

class DriveTest(s_t_utils.SynTest):

    async def test_drive_base(self):

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

                info = {'name': 'win32k.sys', 'type': 'woot', 'perm': {'users': {}}}
                info = await cell.addDriveItem(info, reldir=rootdir)
                self.notin('perm', info)
                self.eq(info[0]['permissions'], {
                    'users': {},
                    'roles': {}
                })

                iden = info[-1].get('iden')

                tick = s_common.now()
                rootuser = cell.auth.rootuser.iden
                fooser = await cell.auth.addUser('foo')
                neatrole = await cell.auth.addRole('neatrole')
                await fooser.grant(neatrole.iden)

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

                await cell.setDriveItemProp(iden, versinfo, ('stuff',), 1234)
                data = await cell.getDriveData(iden)
                self.eq(data[1]['stuff'], 1234)

                # Drive schema callbacks must be valid dynLocal items + coro
                with self.raises(s_exc.BadArg):
                    await cell.drive.setTypeSchema('woot', testDataSchema_v1,
                                                   callback='synapse.tests.test_lib_drive.newp')

                with self.raises(s_exc.BadArg):
                    await cell.drive.setTypeSchema('woot', testDataSchema_v1,
                                                   callback='synapse.tests.test_lib_drive.migrate_not_coro')

                # This will be done by the cell in a cell storage version migration...
                callback = 'synapse.tests.test_lib_drive.migrate_v1'
                await cell.drive.setTypeSchema('woot', testDataSchema_v1, callback=callback)

                await cell.setDriveItemProp(iden, versinfo, 'woot', 'woot')

                versinfo['version'] = (1, 1, 1)
                await cell.setDriveItemProp(iden, versinfo, 'stuff', 3829)
                data = await cell.getDriveData(iden)
                self.eq(data[0]['version'], (1, 1, 1))
                self.eq(data[1]['stuff'], 3829)

                await self.asyncraises(s_exc.NoSuchIden, cell.setDriveItemProp(s_common.guid(), versinfo, ('lolnope',), 'not real'))

                await self.asyncraises(s_exc.BadArg, cell.setDriveItemProp(iden, versinfo, ('blorp', 0, 'neato'), 'my special string'))
                data[1]['blorp'] = {
                    'bleep': [{'neato': 'thing'}]
                }
                info, versinfo = await cell.setDriveData(iden, versinfo, data[1])
                now = s_common.now()
                versinfo['updated'] = now
                await cell.setDriveItemProp(iden, versinfo, ('blorp', 'bleep', 0, 'neato'), 'my special string')
                data = await cell.getDriveData(iden)
                self.eq(now, data[0]['updated'])
                self.eq('my special string', data[1]['blorp']['bleep'][0]['neato'])

                versinfo['version'] = (1, 2, 1)
                await cell.delDriveItemProp(iden, versinfo, ('blorp', 'bleep', 0, 'neato'))
                vers, data = await cell.getDriveData(iden)
                self.eq((1, 2, 1), vers['version'])
                self.nn(data['blorp']['bleep'][0])
                self.notin('neato', data['blorp']['bleep'][0])

                await self.asyncraises(s_exc.NoSuchIden, cell.delDriveItemProp(s_common.guid(), versinfo, 'blorp'))

                self.none(await cell.delDriveItemProp(iden, versinfo, ('lolnope', 'nopath')))

                versinfo, data = await cell.getDriveData(iden, vers=(1, 0, 0))
                print(versinfo)
                print(data)
                self.eq('woot', data.get('woot'))

                versinfo, data = await cell.getDriveData(iden, vers=(1, 1, 0))
                self.eq('woot', data.get('woot'))

                with self.raises(s_exc.NoSuchIden):
                    await cell.reqDriveInfo('d7d6107b200e2c039540fc627bc5537d')

                with self.raises(s_exc.TypeMismatch):
                    await cell.getDriveInfo(iden, typename='newp')

                self.nn(await cell.getDriveInfo(iden))
                self.len(4, [vers async for vers in cell.getDriveDataVersions(iden)])

                await cell.delDriveData(iden)
                self.len(3, [vers async for vers in cell.getDriveDataVersions(iden)])

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

                info = await cell.setDriveInfoPerm(baziden, {'users': {rootuser: s_cell.PERM_ADMIN}, 'roles': {}})
                # make sure drive perms work with easy perms
                self.true(cell._hasEasyPerm(info, cell.auth.rootuser, s_cell.PERM_ADMIN))
                # defaults to READ
                self.true(cell._hasEasyPerm(info, fooser, s_cell.PERM_READ))
                self.false(cell._hasEasyPerm(info, fooser, s_cell.PERM_EDIT))

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
                    await cell.drive.reqFreeStep(iden, name)

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

                self.none(await cell.drive.getTypeSchema('newp'))

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
                await cell.drive.reqValidData('woot', data)

    async def test_drive_perm_migration(self):
        async with self.getRegrCore('drive-perm-migr') as core:
            item = await core.getDrivePath('driveitemdefaultperms')
            self.len(1, item)
            self.notin('perm', item)
            self.eq(item[0]['permissions'], {'users': {}, 'roles': {}})

            ldog = await core.auth.getRoleByName('littledog')
            bdog = await core.auth.getRoleByName('bigdog')

            louis = await core.auth.getUserByName('lewis')
            tim = await core.auth.getUserByName('tim')
            mj = await core.auth.getUserByName('mj')

            item = await core.getDrivePath('permfolder/driveitemwithperms')
            self.len(2, item)
            self.notin('perm', item[0])
            self.notin('perm', item[1])
            self.eq(item[0]['permissions'], {'users': {tim.iden: s_cell.PERM_ADMIN}, 'roles': {}})
            self.eq(item[1]['permissions'], {
                'users': {
                    mj.iden: s_cell.PERM_ADMIN
                },
                'roles': {
                    ldog.iden: s_cell.PERM_READ,
                    bdog.iden: s_cell.PERM_EDIT,
                },
                'default': s_cell.PERM_DENY
            })

            # make sure it's all good with easy perms
            self.true(core._hasEasyPerm(item[0], tim, s_cell.PERM_ADMIN))
            self.false(core._hasEasyPerm(item[0], mj, s_cell.PERM_EDIT))

            self.true(core._hasEasyPerm(item[1], mj, s_cell.PERM_ADMIN))
            self.true(core._hasEasyPerm(item[1], tim, s_cell.PERM_READ))
            self.true(core._hasEasyPerm(item[1], louis, s_cell.PERM_EDIT))

    async def test_drive_backup_sync(self):
        with self.getTestDir() as dirn:
            backdirn = os.path.join(dirn, 'backups')
            celldirn = os.path.join(dirn, 'cell')

            s_common.yamlsave({'backup:dir': backdirn}, celldirn, 'cell.yaml')

            async with self.getTestCell(s_cell.Cell, dirn=celldirn) as cell:

                await cell.addDriveItem({'name': 'testitem'})

                name = await cell.runBackup('drivetest')

            drivepath = os.path.join(backdirn, name, 'slabs', 'drive.lmdb', 'data.mdb')
            self.true(os.path.isfile(drivepath))
