import synapse.lib.nexus as s_nexus
import synapse.tests.utils as s_t_utils

class SampleNexus(s_nexus.Nexus):

    async def __anit__(self, iden, parent=None):
        await s_nexus.Nexus.__anit__(self, iden=iden, parent=parent)
        self.iden = iden

    async def doathing(self, eventdict):
        return await self._push('thing:doathing', (eventdict, 'foo'))

    @s_nexus.Nexus.onPush('thing:doathing')
    async def _doathinghandler(self, eventdict, anotherparm):
        eventdict['happened'] = self.iden
        return anotherparm

    async def _push(self, event, parms, iden=None):
        eventdict = parms[0]
        eventdict['specialpush'] += 1
        return await s_nexus.Nexus._push(self, event, parms, iden)

class SampleNexus2(SampleNexus):
    async def doathing(self, eventdict):
        return await self._push('thing:doathing', (eventdict, 'bar'))

    async def _thing2handler(self):
        return self

class NexusTest(s_t_utils.SynTest):
    async def test_nexus(self):
        async with await SampleNexus.anit(1) as testparent:
            eventdict = {'specialpush': 0}
            self.eq('foo', await testparent.doathing(eventdict))
            self.eq(1, eventdict.get('happened'))
            async with await SampleNexus2.anit(2, parent=testparent) as testkid:
                eventdict = {'specialpush': 0}
                # Tricky inheriting handler funcs themselves
                self.eq('foo', await testparent.doathing(eventdict))
                self.eq('bar', await testkid.doathing(eventdict))
                self.eq(2, eventdict.get('happened'))
