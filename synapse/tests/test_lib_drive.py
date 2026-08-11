import os
import asyncio

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

async def migrate_indx(info, versinfo, data, curv):
    data['type'] = 'migrated'
    return data

def wootIndxer(item):
    # a string index and an order preserving numeric one, so that the range and reverse
    # scans have something meaningful to order by
    indx = [b'type\x00' + item.get('type').encode()]

    stuff = item.get('stuff')
    if stuff is not None:
        indx.append(b'stuff\x00' + s_common.int64en(stuff))

    return indx

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

        async def tst_drive_basics(dirn):
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

                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('stuff',), {'valu': 1234}),))
                data = await cell.getDriveData(iden)
                self.eq(data[1]['stuff'], 1234)

                # Drive schema callbacks must be valid reqDynCoro items
                with self.raises(s_exc.NoSuchDyn):
                    await cell.drive.setTypeSchema('woot', testDataSchema_v1,
                                                   callback='synapse.tests.test_lib_drive.newp')

                with self.raises(s_exc.NoSuchDyn):
                    await cell.drive.setTypeSchema('woot', testDataSchema_v1,
                                                   callback='synapse.tests.test_lib_drive.migrate_not_coro')

                # This will be done by the cell in a cell storage version migration...
                callback = 'synapse.tests.test_lib_drive.migrate_v1'
                await cell.drive.setTypeSchema('woot', testDataSchema_v1, callback=callback)

                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, 'woot', {'valu': 'woot'}),))

                versinfo['version'] = (1, 1, 1)
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, 'stuff', {'valu': 3829}),))
                data = await cell.getDriveData(iden)
                self.eq(data[0]['version'], (1, 1, 1))
                self.eq(data[1]['stuff'], 3829)

                with self.raises(s_exc.NoSuchIden):
                    edit = (s_drive.DRIVE_EDIT_SET, ('lolnope',), {'valu': 'not real'})
                    await cell.editDriveItem(s_common.guid(), versinfo, (edit,))

                with self.raises(s_exc.BadArg):
                    edit = (s_drive.DRIVE_EDIT_SET, ('blorp', 0, 'neato'), {'valu': 'my special string'})
                    await cell.editDriveItem(iden, versinfo, (edit,))
                data[1]['blorp'] = {
                    'bleep': [{'neato': 'thing'}]
                }
                info, versinfo = await cell.setDriveData(iden, versinfo, data[1])
                now = s_common.now()
                versinfo['updated'] = now
                edit = (s_drive.DRIVE_EDIT_SET, ('blorp', 'bleep', 0, 'neato'), {'valu': 'my special string'})
                await cell.editDriveItem(iden, versinfo, (edit,))
                data = await cell.getDriveData(iden)
                self.eq(now, data[0]['updated'])
                self.eq('my special string', data[1]['blorp']['bleep'][0]['neato'])

                versinfo['version'] = (1, 2, 1)
                edit = (s_drive.DRIVE_EDIT_DEL, ('blorp', 'bleep', 0, 'neato'), {})
                await cell.editDriveItem(iden, versinfo, (edit,))
                vers, data = await cell.getDriveData(iden)
                self.eq((1, 2, 1), vers['version'])
                self.nn(data['blorp']['bleep'][0])
                self.notin('neato', data['blorp']['bleep'][0])

                with self.raises(s_exc.NoSuchIden):
                    await cell.editDriveItem(s_common.guid(), versinfo, ((s_drive.DRIVE_EDIT_DEL, 'blorp', {}),))

                # a del whose intermediate path is missing is a caller error, not a no-op
                with self.raises(s_exc.BadArg):
                    edit = (s_drive.DRIVE_EDIT_DEL, ('lolnope', 'nopath'), {})
                    await cell.editDriveItem(iden, versinfo, (edit,))

                # the path and index rules the editors enforce
                with self.raises(s_exc.NoSuchIden):
                    await cell.editDriveItem(s_common.guid(), versinfo,
                                             ((s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -1), {}),))

                # the last element of the path must be a list index
                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep'), {}),))

                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, 'blorp', {}),))

                # bool is an int subclass but is not a valid list index
                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', True), {}),))

                # the path must resolve to a list
                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('blorp', 0), {}),))

                # only -1 may be used to insert relative to the end of the list
                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -2), {}),))

                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', 99), {}),))

                with self.raises(s_exc.BadArg):
                    await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_INS, ('lolnope', 'bleep', 0), {}),))

                # stepping into a list with a string is an invalid path
                with self.raises(s_exc.BadArg):
                    edit = (s_drive.DRIVE_EDIT_SET, ('blorp', 'bleep', 'newp'), {'valu': 'newp'})
                    await cell.editDriveItem(iden, versinfo, (edit,))

                # ... while a del tolerates it, since the value is absent either way
                edit = (s_drive.DRIVE_EDIT_DEL, ('blorp', 'bleep', 'newp'), {})
                self.true(await cell.editDriveItem(iden, versinfo, (edit,)))

                # the whole item is re-validated, so an invalid insert is rejected
                with self.raises(s_exc.SchemaViolation):
                    await cell.editDriveItem(iden, versinfo, (
                        (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -1), {'valu': 'newp'}),))

                # removing a list element shifts the rest of the list, which is safe to
                # replicate because the nexs guard refuses a replay of the same edit
                await cell.editDriveItem(iden, versinfo, (
                    (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -1), {'valu': {'neato': 'doomed'}}),))
                vers, data = await cell.getDriveData(iden)
                self.len(2, data['blorp']['bleep'])

                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_DEL, ('blorp', 'bleep', 1), {}),))
                vers, data = await cell.getDriveData(iden)
                self.len(1, data['blorp']['bleep'])

                # an out of range index is not an error
                edit = (s_drive.DRIVE_EDIT_DEL, ('blorp', 'bleep', 99), {})
                self.true(await cell.editDriveItem(iden, versinfo, (edit,)))

                versinfo, data = await cell.getDriveData(iden, vers=(1, 0, 0))
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

        with self.getTestDir() as dirn:
            await tst_drive_basics(dirn)

    async def test_drive_item_edits(self):

        async with self.getTestCell() as cell:

            await cell.drive.setTypeSchema('woot', testDataSchema_v1)

            rootuser = cell.auth.rootuser.iden
            tick = s_common.now()

            info = {'name': 'edits', 'iden': s_common.guid(), 'type': 'woot'}
            pathinfo = await cell.addDriveItem(info)
            iden = pathinfo[-1].get('iden')

            versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
            data = {'type': 'hehe', 'size': 0, 'woot': 'woot', 'stuff': 12,
                    'blorp': {'bleep': [{'neato': 'one'}, {'neato': 'two'}]}}
            await cell.setDriveData(iden, versinfo, data)

            # several edits land as one write
            ok, editvers, editdata = await cell.editDriveItem(iden, versinfo, (
                (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'haha'}),
                (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -1), {'valu': {'neato': 'three'}}),
                (s_drive.DRIVE_EDIT_MOV, ('blorp', 'bleep', 0), {'path': ('blorp', 'bleep', -1)}),
                (s_drive.DRIVE_EDIT_DEL, ('stuff',), {}),
            ))
            self.true(ok)

            # the version info and the data which come back are the ones now current
            self.eq('haha', editdata['type'])
            self.eq(['two', 'three', 'one'], [x['neato'] for x in editdata['blorp']['bleep']])
            self.nn(editvers.get('nexs'))

            versinfo, data = await cell.getDriveData(iden)
            self.eq('haha', data['type'])
            self.eq(['two', 'three', 'one'], [x['neato'] for x in data['blorp']['bleep']])
            # stuff declares a default, so removing it puts the default back
            self.none(data['stuff'])

            # the edit records the nexus offset it was applied at, and it is merged into
            # the item info for the current version
            nexs = versinfo.get('nexs')
            self.nn(nexs)
            self.eq(nexs, (await cell.getDriveInfo(iden)).get('nexs'))

            # edits computed against the version which is there are applied
            ok, editvers, editdata = await cell.editDriveItem(iden, versinfo, (
                (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'hoho'}),), nexs=nexs)
            self.true(ok)
            self.eq('hoho', editdata['type'])

            versinfo, data = await cell.getDriveData(iden)
            self.eq('hoho', data['type'])
            self.lt(nexs, versinfo.get('nexs'))

            # ... and edits computed against a version which someone else has written over
            # are refused rather than applied on top of theirs
            ok, curvers, curdata = await cell.editDriveItem(iden, versinfo, (
                (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'newp'}),), nexs=nexs)
            self.false(ok)

            versinfo, data = await cell.getDriveData(iden)
            self.eq('hoho', data['type'])

            # the refusal hands back the version which is current, so the edits can be
            # rebased onto it and retried without a second read which could race
            self.eq('hoho', curdata['type'])
            self.eq(versinfo.get('nexs'), curvers.get('nexs'))

            # ... and the data is copied with lists on that path too, so a caller may edit
            # it in place whether the edits were applied or refused
            self.true(isinstance(curdata['blorp']['bleep'], list))

            ok, _, retrydata = await cell.editDriveItem(iden, curvers, (
                (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'rebased'}),), nexs=curvers.get('nexs'))
            self.true(ok)
            self.eq('rebased', retrydata['type'])

            versinfo, data = await cell.getDriveData(iden)
            self.eq('rebased', data['type'])

            # applying the same event a second time is a replay of it, which the offset
            # the event stamped onto the data identifies. This is what makes the handler
            # idempotent, since re-applying an ins or a mov would not be.
            versinfo, data = await cell.getDriveData(iden)
            ok, _, replaydata = await cell._editDriveItem(iden, dict(versinfo), (
                (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', -1), {'valu': {'neato': 'dupe'}}),),
                None, nexsitem=(versinfo['nexs'], None))
            self.true(ok)

            # ... and a replay hands back what is current rather than the edits it skipped
            self.notin('dupe', [x.get('neato') for x in replaydata['blorp']['bleep']])

            versinfo, data = await cell.getDriveData(iden)
            self.notin('dupe', [x.get('neato') for x in data['blorp']['bleep']])

            # every drive data write records an offset, not just the batched edits
            await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'byprop'}),))
            versinfo, data = await cell.getDriveData(iden)
            self.lt(nexs, versinfo.get('nexs'))

            await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_DEL, ('blorp', 'bleep', 0), {}),))
            versinfo, data = await cell.getDriveData(iden)
            self.lt(nexs, versinfo.get('nexs'))

            # removing something which is not there is not an error
            self.true((await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_DEL, ('nopey',), {}),)))[0])

            # the edit type indexes the editors, so one which is out of range or is not
            # an index at all is refused
            with self.raises(s_exc.BadArg) as cm:
                await cell.editDriveItem(iden, versinfo, ((99, ('type',), {}),))

            self.isin('Invalid item edit type', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await cell.editDriveItem(iden, versinfo, (('set', ('type',), {}),))

            self.isin('Invalid item edit type', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, 'type'),))

            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, (), {'valu': 1}),))

            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_MOV, ('type',), {}),))

            with self.raises(s_exc.NoSuchIden):
                await cell.editDriveItem(s_common.guid(), versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 1}),))

            # the drive method is reachable on its own, and requires the item too
            with self.raises(s_exc.NoSuchIden):
                await cell.drive.editItemData(s_common.guid(), versinfo,
                                              ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 1}),))

            # a bare string is a single element path, for the source and the destination
            self.true((await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, 'type', {'valu': 'bystr'}),)))[0])
            versinfo, data = await cell.getDriveData(iden)
            self.eq('bystr', data['type'])

            self.true((await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('stuff',), {'valu': 99}),)))[0])
            self.true((await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_MOV, 'stuff', {'path': 'size'}),)))[0])
            versinfo, data = await cell.getDriveData(iden)
            self.eq(99, data['size'])
            self.none(data['stuff'])

            # a path which steps into a list with a string is an invalid path
            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('blorp', 'bleep', 'newp'), {'valu': 1}),))

            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, (
                    (s_drive.DRIVE_EDIT_MOV, ('blorp', 'bleep', 'newp'), {'path': ('woot',)}),))

            # ... and so is a destination which does
            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, (
                    (s_drive.DRIVE_EDIT_MOV, ('woot',), {'path': ('blorp', 'bleep', 'newp')}),))

            # nothing is written when any edit in the batch is malformed
            versinfo, data = await cell.getDriveData(iden)
            self.eq('bystr', data['type'])

            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, (
                    (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'nope'}),
                    (s_drive.DRIVE_EDIT_SET, ('blorp', 'bleep', 'newp'), {'valu': 1}),
                ))

            versinfo, data = await cell.getDriveData(iden)
            self.eq('bystr', data['type'])

            # an insert at an index puts the value there and shifts the rest right
            versinfo, data = await cell.getDriveData(iden)
            count = len(data['blorp']['bleep'])

            self.true((await cell.editDriveItem(iden, versinfo, (
                (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', 0), {'valu': {'neato': 'zero'}}),)))[0])

            versinfo, data = await cell.getDriveData(iden)
            self.len(count + 1, data['blorp']['bleep'])
            self.eq('zero', data['blorp']['bleep'][0]['neato'])

            # ... and an index equal to the length of the list appends, as -1 does
            self.true((await cell.editDriveItem(iden, versinfo, (
                (s_drive.DRIVE_EDIT_INS, ('blorp', 'bleep', count + 1), {'valu': {'neato': 'last'}}),)))[0])

            versinfo, data = await cell.getDriveData(iden)
            self.eq('last', data['blorp']['bleep'][-1]['neato'])

            # a udef gates the whole batch before any of it is applied
            udef = {'iden': s_common.guid(), 'roles': ()}
            with self.raises(s_exc.AuthDeny):
                await cell.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'nope'}),), udef=udef)

            versinfo, data = await cell.getDriveData(iden)
            self.eq('bystr', data['type'])

            await cell.setDriveInfoPerm(iden, {'users': {udef['iden']: s_cell.PERM_EDIT},
                                               'roles': {}})
            edit = (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'byuser'})
            self.true((await cell.editDriveItem(iden, versinfo, (edit,), udef=udef))[0])
            versinfo, data = await cell.getDriveData(iden)
            self.eq('byuser', data['type'])

    async def test_drive_item_edits_telepath(self):

        async with self.getTestCell() as cell:

            await cell.drive.setTypeSchema('woot', testDataSchema_v1)

            rootuser = cell.auth.rootuser.iden

            info = {'name': 'edits', 'iden': s_common.guid(), 'type': 'woot'}
            pathinfo = await cell.addDriveItem(info)
            iden = pathinfo[-1].get('iden')

            versinfo = {'version': (1, 0, 0), 'updated': s_common.now(), 'updater': rootuser}
            await cell.setDriveData(iden, versinfo, {'type': 'hehe', 'size': 0, 'woot': 'woot'})

            await cell.auth.addUser('lowly', passwd='secret')
            await cell.auth.addUser('other', passwd='secret')
            other = await cell.auth.getUserByName('other')

            async with cell.getLocalProxy() as prox:

                await prox.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'byroot'}),))
                versinfo, data = await cell.getDriveData(iden)
                self.eq('byroot', data['type'])

                # an admin may name the user to check as, and it is honoured: other has no
                # permission on the item yet, so the edit is refused
                udef = await cell.getUserDef(other.iden)
                with self.raises(s_exc.AuthDeny):
                    await prox.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'nope'}),),
                                             udef=udef)

            async with cell.getLocalProxy(user='lowly') as prox:

                # a non admin is checked as themselves
                with self.raises(s_exc.AuthDeny):
                    await prox.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'nope'}),))

                # ... and passing someone else's udef does not change that
                udef = await cell.getUserDef(other.iden)
                await cell.setDriveInfoPerm(iden, {'users': {other.iden: s_cell.PERM_EDIT},
                                                   'roles': {}})

                with self.raises(s_exc.AuthDeny):
                    await prox.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'nope'}),),
                                             udef=udef)

                versinfo, data = await cell.getDriveData(iden)
                self.eq('byroot', data['type'])

                # once they are granted edit on the item themselves, it goes through
                lowly = await cell.auth.getUserByName('lowly')
                await cell.setDriveInfoPerm(iden, {'users': {lowly.iden: s_cell.PERM_EDIT},
                                                   'roles': {}})

                await prox.editDriveItem(iden, versinfo, ((s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'bylowly'}),))
                versinfo, data = await cell.getDriveData(iden)
                self.eq('bylowly', data['type'])

    def test_drive_haseasypermudef(self):

        item = {'permissions': {'users': {'a' * 32: s_cell.PERM_EDIT},
                                'roles': {'r' * 32: s_cell.PERM_READ},
                                'default': s_cell.PERM_DENY}}

        func = s_cell.Cell._hasEasyPermUdef

        # an unauthenticated caller has no permissions at all
        self.false(func(None, item, {}, s_cell.PERM_READ))

        with self.raises(s_exc.BadArg):
            func(None, item, {'iden': 'a' * 32}, 99)

        # a cell admin is allowed everything
        self.true(func(None, item, {'iden': 'b' * 32, 'admin': True}, s_cell.PERM_ADMIN))

        # a user grant is checked ahead of any role
        udef = {'iden': 'a' * 32, 'roles': ({'iden': 'r' * 32},)}
        self.true(func(None, item, udef, s_cell.PERM_EDIT))
        self.false(func(None, item, udef, s_cell.PERM_ADMIN))

        # ... and a role grant when the user has none of their own
        udef = {'iden': 'c' * 32, 'roles': ({'iden': 'r' * 32},)}
        self.true(func(None, item, udef, s_cell.PERM_READ))
        self.false(func(None, item, udef, s_cell.PERM_EDIT))

        # a user grant which is present but insufficient falls through to the roles rather
        # than deciding, so a role granting more than the user's own level is honoured
        fall = {'permissions': {'users': {'a' * 32: s_cell.PERM_READ},
                                'roles': {'r' * 32: s_cell.PERM_EDIT},
                                'default': s_cell.PERM_DENY}}

        udef = {'iden': 'a' * 32, 'roles': ({'iden': 'r' * 32},)}
        self.true(func(None, fall, udef, s_cell.PERM_EDIT))
        self.false(func(None, fall, udef, s_cell.PERM_ADMIN))

        # ... and an insufficient role falls through to the roles after it
        fall = {'permissions': {'users': {},
                                'roles': {'r' * 32: s_cell.PERM_READ, 's' * 32: s_cell.PERM_ADMIN},
                                'default': s_cell.PERM_DENY}}

        udef = {'iden': 'a' * 32, 'roles': ({'iden': 'r' * 32}, {'iden': 's' * 32})}
        self.true(func(None, fall, udef, s_cell.PERM_ADMIN))

        # ... and finally to the default
        fall = {'permissions': {'users': {'a' * 32: s_cell.PERM_READ}, 'roles': {},
                                'default': s_cell.PERM_EDIT}}
        self.true(func(None, fall, {'iden': 'a' * 32}, s_cell.PERM_EDIT))

        # an explicit role deny stops the check, even where the default would allow
        fall = {'permissions': {'users': {}, 'roles': {'r' * 32: s_cell.PERM_DENY},
                                'default': s_cell.PERM_EDIT}}

        udef = {'iden': 'a' * 32, 'roles': ({'iden': 'r' * 32},)}
        self.false(func(None, fall, udef, s_cell.PERM_READ))

        # a role with no grant at all is skipped rather than deciding
        fall = {'permissions': {'users': {}, 'roles': {'s' * 32: s_cell.PERM_EDIT},
                                'default': s_cell.PERM_DENY}}

        udef = {'iden': 'a' * 32, 'roles': ({'iden': 'r' * 32}, {'iden': 's' * 32})}
        self.true(func(None, fall, udef, s_cell.PERM_EDIT))

        # an explicit deny beats the default
        denied = {'permissions': {'users': {'a' * 32: s_cell.PERM_DENY}, 'roles': {},
                                  'default': s_cell.PERM_READ}}
        self.false(func(None, denied, {'iden': 'a' * 32}, s_cell.PERM_READ))

        # otherwise the default decides
        self.true(func(None, denied, {'iden': 'z' * 32}, s_cell.PERM_READ))
        self.false(func(None, denied, {'iden': 'z' * 32}, s_cell.PERM_EDIT))

    async def test_drive_type_validator(self):

        async with self.getTestCell() as cell:

            drive = cell.drive

            await drive.setTypeSchema('woot', testDataSchema_v1)
            await drive.setTypeSchema('nope', testDataSchema_v1)

            with self.raises(s_exc.BadName):
                drive.setTypeValidator('A' * 512, lambda versinfo, item: None)

            with self.raises(s_exc.BadArg):
                drive.setTypeValidator('woot', 'newp')

            with self.raises(s_exc.BadArg):
                drive.setTypeValidator('woot', None)

            rootuser = cell.auth.rootuser.iden
            tick = s_common.now()

            info = {'name': 'vtor', 'iden': s_common.guid(), 'type': 'woot'}
            iden = (await cell.addDriveItem(info))[-1].get('iden')

            data = {'type': 'hehe', 'size': 0, 'woot': 'woot'}

            # with no validator registered the data is stored
            versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(iden, versinfo, dict(data))

            # the validators copy what they are handed, since by contract they may not
            # retain or modify the objects which are about to be stored. The counts are
            # compared as deltas rather than absolutes, since a nexus replay run applies
            # each event, and so calls the validator, twice.
            calls = []

            def syncvtor(versinfo, item):
                calls.append((dict(versinfo), dict(item)))

            drive.setTypeValidator('woot', syncvtor)

            # a plain def is called with the schema defaulted item and the normalized
            # version info
            versinfo = {'version': (1, 1, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(iden, versinfo, dict(data))

            self.gt(len(calls), 0)
            self.eq((1, 1, 0), calls[0][0].get('version'))
            self.nn(calls[0][0].get('size'))
            # stuff declares a schema default, which the validator sees filled in
            self.none(calls[0][1].get('stuff'))

            # adding an item info does not call it, since there is no data to validate
            count = len(calls)
            await cell.addDriveItem({'name': 'novtor', 'iden': s_common.guid(), 'type': 'woot'})
            self.len(count, calls)

            # ... and neither does a write of an item with another type
            other = {'name': 'other', 'iden': s_common.guid(), 'type': 'nope'}
            oden = (await cell.addDriveItem(other))[-1].get('iden')
            versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(oden, versinfo, dict(data))
            self.len(count, calls)

            # an async def is awaited
            async def asyncvtor(versinfo, item):
                calls.append((dict(versinfo), dict(item)))

            drive.setTypeValidator('woot', asyncvtor)

            versinfo = {'version': (1, 2, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(iden, versinfo, dict(data))
            self.gt(len(calls), count)

            # a validator which raises refuses the write
            def badvtor(versinfo, item):
                raise s_exc.BadArg(mesg='the validator said no')

            drive.setTypeValidator('woot', badvtor)

            versinfo = {'version': (1, 3, 0), 'updated': tick, 'updater': rootuser}
            with self.raises(s_exc.BadArg):
                await cell.setDriveData(iden, versinfo, {'type': 'newp', 'size': 0, 'woot': 'woot'})

            # ... on the edit path as well
            versinfo = {'version': (1, 2, 0), 'updated': tick, 'updater': rootuser}
            with self.raises(s_exc.BadArg):
                await cell.editDriveItem(iden, versinfo, (
                    (s_drive.DRIVE_EDIT_SET, ('type',), {'valu': 'newp'}),))

            # neither refused write landed
            versinfo, item = await cell.getDriveData(iden)
            self.eq((1, 2, 0), versinfo.get('version'))
            self.eq('hehe', item.get('type'))
            self.none(await cell.getDriveData(iden, vers=(1, 3, 0)))

    async def test_drive_type_indexer(self):

        async with self.getTestCell() as cell:

            drive = cell.drive

            await drive.setTypeSchema('woot', testDataSchema_v1)
            await drive.setTypeSchema('nope', testDataSchema_v1)

            drive.setTypeIndxer('woot', wootIndxer)
            drive.setTypeIndxer('nope', wootIndxer)

            rootuser = cell.auth.rootuser.iden
            tick = s_common.now()

            async def addItem(name, typename, valu, stuff):
                info = {'name': name, 'iden': s_common.guid(), 'type': typename}
                iden = (await cell.addDriveItem(info))[-1].get('iden')

                versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
                data = {'type': valu, 'size': 0, 'woot': 'woot', 'stuff': stuff}
                await cell.setDriveData(iden, versinfo, data)

                return iden

            async def lift(*args, **kwargs):
                return [item async for _, item in drive.iterItemsByRange(*args, **kwargs)]

            async def liftpref(*args, **kwargs):
                return [item async for _, item in drive.iterItemsByPrefix(*args, **kwargs)]

            idenA = await addItem('itemA', 'woot', 'hehe', 10)
            idenB = await addItem('itemB', 'woot', 'hehe', 20)
            await addItem('itemC', 'woot', 'haha', 30)

            # a second type, whose abrv sorts after the first, so a scan which leaks past
            # the type boundary picks it up
            await addItem('itemD', 'nope', 'zoinks', 40)
            self.lt(drive._getTypeAbrv('woot'), drive._getTypeAbrv('nope'))

            def stuffkey(valu):
                return b'stuff\x00' + s_common.int64en(valu)

            # an exact lookup, and two items which share one index value
            self.eq('hehe', (await liftpref('woot', b'type\x00hehe'))[0].get('type'))
            self.len(2, await liftpref('woot', b'type\x00hehe'))

            # a bound shorter than the stored values is a prefix
            self.len(3, await liftpref('woot', b'type\x00'))

            # an explicit range, in ascending order
            self.eq([10, 20], [i.get('stuff') for i in await lift('woot', stuffkey(10), maxv=stuffkey(20))])

            # maxv of None runs to the end of the type's index, past the byts prefix and
            # into the later values, but never out of the type. The stuff rows sort ahead of
            # the type rows, whose order among themselves is iden order and so is not
            # asserted here.
            rows = await lift('woot', b'')
            self.len(6, rows)
            self.eq([10, 20, 30], [i.get('stuff') for i in rows[:3]])
            self.len(6, await lift('woot', b'stuff\x00'))
            self.len(2, await lift('nope', b''))

            # reverse with explicit bounds
            self.eq([20, 10], [i.get('stuff') for i in
                               await lift('woot', stuffkey(10), maxv=stuffkey(20), reverse=True)])

            # reverse over a prefix, which a naive seek walks straight past
            self.eq([30, 20, 10], [i.get('stuff') for i in
                                   await liftpref('woot', b'stuff\x00', reverse=True)])

            # ... and reverse with no upper bound at all
            rows = await lift('woot', b'', reverse=True)
            self.len(6, rows)
            self.eq([30, 20, 10], [i.get('stuff') for i in rows[3:]])

            bidnA = s_common.uhex(idenA)

            def countRows(bidn):
                return len(list(drive.slab.scanKeysByPref(s_drive.LKEY_IREV + bidn, db=drive.dbname)))

            # a rewrite drops the values which are gone and adds the ones which are new
            versinfo = {'version': (1, 1, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(idenA, versinfo, {'type': 'hoho', 'size': 0, 'woot': 'woot', 'stuff': 11})

            self.len(0, await liftpref('woot', stuffkey(10)))
            self.len(0, await liftpref('woot', b'type\x00hehe\x00'))
            self.len(1, await liftpref('woot', stuffkey(11)))
            self.eq('hoho', (await liftpref('woot', b'type\x00hoho'))[0].get('type'))

            # the reverse rows prove the old ones were removed rather than shadowed
            self.eq(2, countRows(bidnA))
            self.len(1, await liftpref('woot', b'type\x00hehe'))

            # ... while the unbounded default runs on past the prefix into the new value
            self.len(2, await lift('woot', b'type\x00hehe'))

            # a write below the current version changes no index rows
            versinfo = {'version': (0, 5, 0), 'updated': tick, 'updater': rootuser}
            await cell.setDriveData(idenA, versinfo, {'type': 'newp', 'size': 0, 'woot': 'woot', 'stuff': 99})

            self.len(0, await liftpref('woot', stuffkey(99)))
            self.len(1, await liftpref('woot', stuffkey(11)))
            self.eq(2, countRows(bidnA))

            # deleting the current version rolls the index back to whatever becomes current,
            # which is the greatest version left rather than the one written most recently
            await cell.delDriveData(idenA, vers=(1, 1, 0))

            self.len(0, await liftpref('woot', stuffkey(11)))
            self.eq(10, (await liftpref('woot', stuffkey(10)))[0].get('stuff'))

            # ... deleting a version which is not current leaves the index alone
            await cell.delDriveData(idenA, vers=(0, 5, 0))
            self.eq(10, (await liftpref('woot', stuffkey(10)))[0].get('stuff'))
            self.eq(2, countRows(bidnA))

            # ... and deleting the last version clears every row
            await cell.delDriveData(idenA, vers=(1, 0, 0))
            self.eq(0, countRows(bidnA))
            self.len(0, await liftpref('woot', stuffkey(10)))

            # a teardown leaves no index row and no by-type row behind
            bidnB = s_common.uhex(idenB)
            await cell.delDriveInfo(idenB)

            self.eq(0, countRows(bidnB))
            self.len(0, [k for k in drive.slab.scanKeysByPref(s_drive.LKEY_INDX, db=drive.dbname)
                         if k.endswith(bidnB)])
            self.false(drive.slab.has(s_drive.LKEY_INFO_BYTYPE + b'woot\x00' + bidnB, db=drive.dbname))
            self.len(1, await liftpref('woot', b'type\x00'))

            # an index row whose item is no longer fetchable is skipped rather than raising.
            # Every teardown path removes the rows with the data, so the row is orphaned here
            # by removing the version row underneath it.
            idenE = await addItem('itemE', 'woot', 'zonk', 50)
            self.len(1, await liftpref('woot', stuffkey(50)))

            bidnE = s_common.uhex(idenE)
            versindx = s_drive.getVersIndx((1, 0, 0))
            self.true(drive.slab.delete(s_drive.LKEY_VERS + bidnE + versindx, db=drive.dbname))

            self.eq(2, countRows(bidnE))
            self.len(0, await liftpref('woot', stuffkey(50)))

    async def test_drive_type_indexer_errs(self):

        with self.getTestDir() as dirn:

            async with self.getTestCell(dirn=dirn) as cell:

                drive = cell.drive

                async def liftpref(*args, **kwargs):
                    return [item async for _, item in drive.iterItemsByPrefix(*args, **kwargs)]

                await drive.setTypeSchema('woot', testDataSchema_v1)

                with self.raises(s_exc.BadName):
                    drive.setTypeIndxer('A' * 512, wootIndxer)

                with self.raises(s_exc.BadArg):
                    drive.setTypeIndxer('woot', 'newp')

                with self.raises(s_exc.BadArg):
                    drive.setTypeIndxer('woot', None)

                # an indexer must be synchronous, so that index maintenance stays await free
                # and therefore atomic with the data write
                with self.raises(s_exc.BadArg):
                    drive.setTypeIndxer('woot', asyncio.sleep)

                # a type with no indexer registered has no index
                rootuser = cell.auth.rootuser.iden
                tick = s_common.now()

                info = {'name': 'errs', 'iden': s_common.guid(), 'type': 'woot'}
                iden = (await cell.addDriveItem(info))[-1].get('iden')

                data = {'type': 'hehe', 'size': 0, 'woot': 'woot'}
                versinfo = {'version': (1, 0, 0), 'updated': tick, 'updater': rootuser}
                await cell.setDriveData(iden, versinfo, dict(data))

                self.len(0, await liftpref('woot', b''))

                # an indexer which returns something which is not bytes, or a value which is
                # too long, refuses the write rather than half applying it
                drive.setTypeIndxer('woot', lambda item: ['newp'])

                versinfo = {'version': (1, 1, 0), 'updated': tick, 'updater': rootuser}
                with self.raises(s_exc.BadArg):
                    await cell.setDriveData(iden, versinfo, dict(data))

                drive.setTypeIndxer('woot', lambda item: [b'A' * (s_drive.MAX_INDX_LEN + 1)])

                with self.raises(s_exc.BadArg):
                    await cell.setDriveData(iden, versinfo, dict(data))

                self.eq((1, 0, 0), (await cell.getDriveData(iden))[0].get('version'))
                self.none(await cell.getDriveData(iden, vers=(1, 1, 0)))

                # a value which the indexer repeats is stored once
                drive.setTypeIndxer('woot', lambda item: [b'dup', b'dup'])
                await cell.setDriveData(iden, versinfo, dict(data))

                self.len(1, [k for k in drive.slab.scanKeysByPref(s_drive.LKEY_IREV +
                                                                  s_common.uhex(iden), db=drive.dbname)])
                self.len(1, await liftpref('woot', b'dup'))

                # a bound which is not bytes, or is too long
                with self.raises(s_exc.BadArg):
                    await liftpref('woot', 'newp')

                with self.raises(s_exc.BadArg):
                    await liftpref('woot', b'A' * (s_drive.MAX_INDX_LEN + 1))

                with self.raises(s_exc.BadArg):
                    self.len(0, [x async for x in drive.iterItemsByRange('woot', b'',
                                                                         maxv=b'A' * (s_drive.MAX_INDX_LEN + 1))])

                # a type which has never been indexed has no abrv, and so no rows
                self.len(0, await liftpref('nope', b''))

                # a migration is what indexes the items which are already stored, and only
                # for a type whose indexer is registered by the time it runs
                await drive.setTypeSchema('haha', testDataSchema_v1, vers=0)

                info = {'name': 'migr', 'iden': s_common.guid(), 'type': 'haha'}
                mgriden = (await cell.addDriveItem(info))[-1].get('iden')
                await cell.setDriveData(mgriden, versinfo, dict(data))

                # ... an item with info but no data at all, which the walk skips
                info = {'name': 'nodata', 'iden': s_common.guid(), 'type': 'haha'}
                await cell.addDriveItem(info)

                self.true(await drive.setTypeSchema('haha', testDataSchema_v1, vers=1,
                                                    callback='synapse.tests.test_lib_drive.migrate_indx'))
                self.len(0, await liftpref('haha', b'type\x00migrated'))

                drive.setTypeIndxer('haha', wootIndxer)

                self.true(await drive.setTypeSchema('haha', testDataSchema_v1, vers=2,
                                                    callback='synapse.tests.test_lib_drive.migrate_indx'))
                self.len(1, await liftpref('haha', b'type\x00migrated'))

                abrv = drive._getTypeAbrv('woot')

            # the abrvs are recovered on the way back up, so an existing type keeps its own
            # and a new one is given the next
            async with self.getTestCell(dirn=dirn) as cell:

                drive = cell.drive
                drive.setTypeIndxer('woot', wootIndxer)

                self.eq(abrv, drive._getTypeAbrv('woot'))
                self.len(1, await liftpref('woot', b'dup'))

                self.eq(2, s_common.int64un(drive._getTypeAbrv('newp', init=True)))

            # ... and a readonly cell may still read the index
            async with await s_cell.Cell.anit(dirn, readonly=True) as cell:
                drive = cell.drive
                self.len(1, await liftpref('woot', b'dup'))

    async def test_drive_backup_sync(self):

        async def tst_drive_sync(dirn):
            celldirn = os.path.join(dirn, 'cell')

            async with self.getTestCell(s_cell.Cell, dirn=celldirn) as cell:

                await cell.addDriveItem({'name': 'testitem'})

                bdir = os.path.join(dirn, 'backups', 'drivetest')
                await s_t_utils.pullBackup(cell, bdir)

            drivepath = os.path.join(bdir, 'slabs', 'drive.lmdb', 'data.mdb')
            self.true(os.path.isfile(drivepath))

        with self.getTestDir() as dirn:
            await tst_drive_sync(dirn)
