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
