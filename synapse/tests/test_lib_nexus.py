import synapse.lib.nexus as s_nexus
import synapse.tests.utils as s_t_utils

class SampleNexus(s_nexus.Pusher):

    async def __anit__(self, iden, nexsroot=None):
        await s_nexus.Pusher.__anit__(self, iden=iden, nexsroot=nexsroot)
        self.iden = iden

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

class SampleNexus2(SampleNexus):
    async def doathing(self, eventdict):
        return await self._push('thing:doathing', eventdict, 'bar')

    async def _thing2handler(self):
        return self

class NexusTest(s_t_utils.SynTest):
    async def test_nexus(self):
        async with await SampleNexus.anit(1) as nexus1, await s_nexus.NexsRoot.anit() as nexsroot:
            eventdict = {'specialpush': 0}
            self.eq('foo', await nexus1.doathing(eventdict))
            self.eq(1, eventdict.get('happened'))
            async with await SampleNexus2.anit(2, nexsroot=nexsroot) as testkid:
                eventdict = {'specialpush': 0}
                # Tricky inheriting handler funcs themselves
                self.eq('foo', await nexus1.doathing(eventdict))
                self.eq('bar', await testkid.doathing(eventdict))
                self.eq(2, eventdict.get('happened'))
