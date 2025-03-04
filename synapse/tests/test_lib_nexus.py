import asyncio
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.auth as s_auth
import synapse.lib.cell as s_cell
import synapse.lib.nexus as s_nexus

import synapse.tests.utils as s_t_utils

class SampleNexus(s_cell.Cell):

    async def doathing(self, eventdict):
        return await self._push('thing:doathing', eventdict, 'foo')

    @s_nexus.Pusher.onPush('thing:doathing')
    async def _doathinghandler(self, eventdict, anotherparm):
        eventdict['happened'] = self.iden
        return anotherparm

    async def _push(self, event, *args, **kwargs):
        eventdict = args[0]
        eventdict['specialpush'] += 1
        return await s_nexus.Pusher._push(self, event, *args, **kwargs)

    async def doathing2(self, eventdict):
        return await self._push('thing:doathing2', eventdict, 'foo')

    @s_nexus.Pusher.onPush('thing:doathing2', passitem=True)
    async def _doathing2handler(self, eventdict, anotherparm, nexsitem=None):
        nexsoff, nexsmesg = nexsitem
        eventdict['gotindex'] = nexsoff
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto2')
    async def doathingauto(self, eventdict, anotherparm):
        eventdict['autohappened'] = self.iden
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto1')
    async def doathingauto2(self, eventdict, anotherparm):
        '''doc'''
        eventdict['autohappened2'] = self.iden
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto3')
    async def doathingauto3(self, eventdict):
        raise s_exc.SynErr(mesg='Test error')

class SampleMixin(metaclass=s_nexus.RegMethType):
    @s_nexus.Pusher.onPushAuto('mixinthing')
    async def mixinthing(self, eventdict):
        eventdict['autohappened3'] = self.iden
        return 42

class SampleNexus2(SampleNexus, SampleMixin):
    async def doathing(self, eventdict):
        return await self._push('thing:doathing', eventdict, 'bar')

class NexusTest(s_t_utils.SynTest):

    async def test_nexus(self):

        with self.getTestDir() as dirn:
            dir1 = s_common.genpath(dirn, 'nexus1')
            dir2 = s_common.genpath(dirn, 'nexus2')
            guid1 = s_common.guid('nexus1')
            guid2 = s_common.guid('nexus2')

            conf1 = {'cell:guid': guid1, 'nexslog:en': True}
            async with await SampleNexus.anit(conf=conf1, dirn=dir1) as nexus1:
                nexsroot = nexus1.nexsroot

                eventdict = {'specialpush': 0}
                self.eq('foo', await nexus1.doathing(eventdict))
                self.eq(guid1, eventdict.get('happened'))

                self.eq('foo', await nexus1.doathingauto(eventdict, 'foo'))
                self.eq(guid1, eventdict.get('autohappened'))

                self.eq('foo', await nexus1.doathingauto2(eventdict, 'foo'))
                self.eq(guid1, eventdict.get('autohappened2'))

                self.eq('doc', nexus1.doathingauto2.__doc__)

                self.eq(3, await nexsroot.index())

                conf2 = {'cell:guid': guid2, 'nexslog:en': True}
                async with await SampleNexus2.anit(conf=conf2, dirn=dir2, parent=nexus1) as nexus2:

                    eventdict = {'specialpush': 0}
                    # Tricky inheriting handler funcs themselves
                    self.eq('foo', await nexus1.doathing(eventdict))
                    self.eq('bar', await nexus2.doathing(eventdict))
                    self.eq(guid2, eventdict.get('happened'))

                    # Check offset passing
                    self.eq('foo', await nexus2.doathing2(eventdict))
                    self.eq(5, eventdict.get('gotindex'))

                    # Check raising an exception
                    with self.raises(s_exc.SynErr) as cm:
                        await nexus2.doathingauto3(eventdict)
                    self.eq(cm.exception.get('mesg'), 'Test error')

                    with self.getLoggerStream('synapse.lib.nexus') as stream:
                        await nexsroot.recover()

                    stream.seek(0)
                    self.isin('while replaying log', stream.read())

    async def test_nexus_modroot(self):

        async with self.getTestCell() as cell:
            await cell.sync()
            async with cell.nexslock:
                await cell.modNexsRoot(cell._ctorNexsRoot)
            await cell.sync()

    async def test_nexus_mixin(self):
        with self.getTestDir() as dirn:
            dir1 = s_common.genpath(dirn, 'nexus1')
            dir2 = s_common.genpath(dirn, 'nexus2')
            guid1 = s_common.guid('nexus1')
            guid2 = s_common.guid('nexus2')

            conf1 = {'cell:guid': guid1, 'nexslog:en': True}
            async with await SampleNexus.anit(conf=conf1, dirn=dir1) as nexus1:
                conf1 = {'cell:guid': guid2, 'nexslog:en': True}
                async with await SampleNexus2.anit(conf=conf1, dirn=dir2, parent=nexus1) as nexus2:
                    eventdict = {'specialpush': 0}
                    self.eq('bar', await nexus2.doathing(eventdict))
                    self.eq(42, await nexus2.mixinthing(eventdict))

    async def test_nexus_no_logging(self):
        '''
        Pushers/NexsRoot works with donexslog=False
        '''
        with self.getTestDir() as dirn:
            dir1 = s_common.genpath(dirn, 'nexus1')
            dir2 = s_common.genpath(dirn, 'nexus2')
            guid1 = s_common.guid('nexus1')
            guid2 = s_common.guid('nexus2')

            conf1 = {'cell:guid': guid1, 'nexslog:en': False}
            async with await SampleNexus.anit(conf=conf1, dirn=dirn) as nexus1:
                nexsroot = nexus1.nexsroot

                eventdict = {'specialpush': 0}
                self.eq('foo', await nexus1.doathing(eventdict))
                self.eq('foo', await nexus1.doathing2(eventdict))
                self.eq(guid1, eventdict.get('happened'))
                self.eq(1, eventdict.get('gotindex'))

                self.eq(2, await nexsroot.index())

                conf2 = {'cell:guid': guid2, 'nexslog:en': False}
                async with await SampleNexus2.anit(conf=conf2, dirn=dir2, parent=nexus1) as nexus2:
                    eventdict = {'specialpush': 0}
                    self.eq('bar', await nexus2.doathing(eventdict))
                    self.eq('foo', await nexus2.doathing2(eventdict))
                    self.eq(guid2, eventdict.get('happened'))
                    self.eq(3, eventdict.get('gotindex'))

    async def test_nexus_migration(self):
        with self.getRegrDir('cortexes', 'reindex-byarray3') as regrdirn:
            slabsize00 = s_common.getDirSize(regrdirn)
            async with self.getTestCore(dirn=regrdirn) as core00:
                slabsize01 = s_common.getDirSize(regrdirn)
                # Ensure that realsize hasn't grown wildly. That would be indicative
                # of a sparse file copy and not a directory move.
                self.lt(slabsize01[0], 3 * slabsize00[0])

                nexsindx = await core00.getNexsIndx()
                layrindx = max([await layr.getEditIndx() for layr in core00.layers.values()])
                self.gt(nexsindx, layrindx)

                retn = await core00.nexsroot.nexslog.get(0)
                self.nn(retn)
                self.eq([0], core00.nexsroot.nexslog._ranges)
                items = await s_t_utils.alist(core00.nexsroot.nexslog.iter(0))
                self.ge(len(items), 62)

    async def test_nexus_setindex(self):

        async with self.getRegrCore('migrated-nexuslog') as core00:

            nexsindx = await core00.getNexsIndx()
            layrindx = max([await layr.getEditIndx() for layr in core00.layers.values()])
            self.ge(nexsindx, layrindx)

            # Make sure a mirror gets updated to the correct index
            url = core00.getLocalUrl()
            core01conf = {'mirror': url}

            async with self.getRegrCore('migrated-nexuslog', conf=core01conf) as core01:

                await core01.sync()

                layrindx = max([await layr.getEditIndx() for layr in core01.layers.values()])
                self.ge(nexsindx, layrindx)

            # Can only move index forward
            self.false(await core00.setNexsIndx(0))

        # Test with nexuslog disabled
        nologconf = {'nexslog:en': False}
        async with self.getRegrCore('migrated-nexuslog', conf=nologconf) as core:

            nexsindx = await core.getNexsIndx()
            layrindx = max([await layr.getEditIndx() for layr in core.layers.values()])
            self.ge(nexsindx, layrindx)

    async def test_nexus_safety(self):

        orig = s_auth.Auth.reqUser
        async def slowReq(self, iden):
            await asyncio.sleep(0.2)
            return await orig(self, iden)

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                with mock.patch('synapse.lib.auth.Auth.reqUser', slowReq):

                    vcnt = len(core.views)
                    deflayr = (await core.getLayerDef()).get('iden')

                    strt = await core.nexsroot.index()

                    vdef = {'layers': (deflayr,), 'name': 'nextview'}
                    core.schedCoro(core.addView(vdef))

                    for x in range(10):
                        vdef = {'layers': (deflayr,), 'name': f'someview{x}'}
                        core.schedCoro(core.addView(vdef))

                    await asyncio.sleep(0.1)

            async with self.getTestCore(dirn=dirn) as core:

                viewadds = 0
                async for item in core.nexsroot.nexslog.iter(strt):
                    if item[1][1] == 'view:add':
                        viewadds += 1

                self.eq(1, viewadds)
                self.len(vcnt + viewadds, core.views)
                self.len(1, [v for v in core.views.values() if (await v.pack())['name'] == 'nextview'])

                vcnt = len(core.views)
                strt = await core.nexsroot.index()

                with mock.patch('synapse.lib.auth.Auth.reqUser', slowReq):
                    for x in range(3):
                        vdef = {'layers': (deflayr,), 'name': f'someview{x}'}
                        with self.raises(TimeoutError):
                            await s_common.wait_for(core.addView(vdef), 0.1)

                await core.nexsroot.waitOffs(strt + 3, timeout=2)

                viewadds = 0
                async for item in core.nexsroot.nexslog.iter(strt):
                    if item[1][1] == 'view:add':
                        viewadds += 1

                self.eq(3, viewadds)
                self.len(vcnt + viewadds, core.views)

            async with self.getTestCore(dirn=dirn) as core:
                self.len(vcnt + viewadds, core.views)

    async def test_mirror_version(self):

        with self.getTestDir() as dirn:

            s_common.yamlsave({'nexslog:en': True}, dirn, 'cell.yaml')
            async with await s_cell.Cell.anit(dirn=dirn) as cell00:

                getCellInfo = cell00.getCellInfo
                async def getCrazyVersion():
                    info = await getCellInfo()
                    info['cell']['version'] = (9999, 0, 0)
                    return info

                await cell00.runBackup(name='cell01')

                path = s_common.genpath(dirn, 'backups', 'cell01')

                conf = s_common.yamlload(path, 'cell.yaml')
                conf['mirror'] = f'cell://{dirn}'
                s_common.yamlsave(conf, path, 'cell.yaml')

                evnt = asyncio.Event()
                cell00.getCellInfo = getCrazyVersion

                async with await s_cell.Cell.anit(dirn=path) as cell01:
                    addWriteHold = cell01.nexsroot.addWriteHold
                    def wrapAddWriteHold(reason):
                        retn = addWriteHold(reason)
                        evnt.set()
                        return retn

                    cell01.nexsroot.addWriteHold = wrapAddWriteHold
                    await asyncio.wait_for(evnt.wait(), timeout=3)

                    with self.raises(s_exc.IsReadOnly):
                        await cell01.sync()
                    self.isin(s_nexus.leaderversion, cell01.nexsroot.writeholds)

                cell00.getCellInfo = getCellInfo

                # test case where a mirror which is updated first may push events
                # the leader does not yet have handlers for
                async with await s_cell.Cell.anit(dirn=path) as cell01:
                    cell01.nexsiden = 'newp'
                    with self.raises(s_exc.NoSuchIden) as cm:
                        await cell01.sync()
                    self.eq(cm.exception.get('mesg'), "No Nexus Pusher with iden newp event='sync' args=() kwargs={}")

                    self.none(await cell00.nexsroot.nexslog.last())
                    self.none(await cell01.nexsroot.nexslog.last())

                    cell01.nexsiden = cell00.nexsiden
                    await cell01.sync()

                    self.eq(0, (await cell00.nexsroot.nexslog.last())[0])
                    self.eq(0, (await cell01.nexsroot.nexslog.last())[0])

                    with self.raises(s_exc.NoSuchName) as cm:
                        await cell01._push('newp')
                    self.eq(cm.exception.get('mesg'), 'No event handler for event newp args=() kwargs={}')

                    self.eq(0, (await cell00.nexsroot.nexslog.last())[0])
                    self.eq(0, (await cell01.nexsroot.nexslog.last())[0])

    async def test_mirror_nexus_loop_failure(self):
        with self.getTestDir() as dirn:

            s_common.yamlsave({'nexslog:en': True}, dirn, 'cell.yaml')
            async with await s_cell.Cell.anit(dirn=dirn) as cell00:

                await cell00.runBackup(name='cell01')

                path = s_common.genpath(dirn, 'backups', 'cell01')

                conf = s_common.yamlload(path, 'cell.yaml')
                conf['mirror'] = f'cell://{dirn}'
                s_common.yamlsave(conf, path, 'cell.yaml')

                seen = False
                restarted = False
                orig = s_nexus.NexsRoot.delWriteHold

                # Patch NexsRoot.delWriteHold so we can cause an exception in
                # the setup part of the nexus loop (NexsRoot.runMirrorLoop). The
                # exception should only happen one time so we can check that the
                # proxy and the nexus loop were both restarted
                async def delWriteHold(self, reason):
                    nonlocal seen
                    nonlocal restarted
                    if not seen:
                        seen = True
                        raise Exception('Knock over the nexus setup.')

                    restarted = True
                    return await orig(self, reason)

                with mock.patch('synapse.lib.nexus.NexsRoot.delWriteHold', delWriteHold):
                    with self.getLoggerStream('synapse.lib.nexus') as stream:
                        async with await s_cell.Cell.anit(dirn=path) as cell01:
                            await cell01.sync()

                    stream.seek(0)
                    data = stream.read()
                    mesg = 'Unknown error during mirror loop startup: Knock over the nexus setup.'
                    self.isin(mesg, data)

                self.true(restarted)

    async def test_pusher_race(self):

        evnt = asyncio.Event()

        async with self.getTestCore() as core:
            orig = core._nexshands['view:delwithlayer'][0]

            async def holdlock(self, viewiden, layriden, nexsitem, newparent=None):
                evnt.set()
                await asyncio.sleep(1)
                await orig(self, viewiden, layriden, nexsitem, newparent=newparent)

            core._nexshands['view:delwithlayer'] = (holdlock, True)

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')

            core.schedCoro(core.delViewWithLayer(forkiden))
            await asyncio.wait_for(evnt.wait(), timeout=10)

            with self.raises(s_exc.NoSuchIden):
                await core.nodes('[ it:dev:str=foo ]', opts={'view': forkiden})
