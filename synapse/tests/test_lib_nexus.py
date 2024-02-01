import asyncio
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.cell as s_cell
import synapse.lib.nexus as s_nexus
import synapse.lib.hiveauth as s_hiveauth

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

        orig = s_hiveauth.Auth.reqUser
        async def slowReq(self, iden):
            await asyncio.sleep(0.2)
            return await orig(self, iden)

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                with mock.patch('synapse.lib.hiveauth.Auth.reqUser', slowReq):

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

                with mock.patch('synapse.lib.hiveauth.Auth.reqUser', slowReq):
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
