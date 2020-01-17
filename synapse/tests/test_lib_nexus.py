import synapse.lib.nexus as s_nexus
import synapse.tests.utils as s_t_utils

class SampleNexus(s_nexus.Nexus):

    async def __anit__(self, iden, parent=None):
        await s_nexus.Nexus.__anit__(self, iden=iden, parent=parent)
        self.iden = iden

    async def doathing(self, eventdict):
        return await self._fireChange('thing:doathing', (eventdict, 'foo'))

    @s_nexus.Nexus.onChng('thing:doathing')
    async def _doathinghandler(self, eventdict, anotherparm):
        eventdict['happened'] = self.iden
        return anotherparm

class SampleNexus2(SampleNexus):
    async def doathing(self, eventdict):
        return await self._fireChange('thing:doathing', (eventdict, 'bar'))

    async def _thing2handler(self):
        return self

class NexusTest(s_t_utils.SynTest):
    async def test_nexus(self):
        async with await SampleNexus.anit(1) as testparent:
            eventdict = {}
            self.eq('foo', await testparent.doathing(eventdict))
            self.eq(1, eventdict.get('happened'))
            async with await SampleNexus2.anit(2, parent=testparent) as testkid:
                parm = {}
                # Tricky inheriting handler funcs themselves
                self.eq('foo', await testparent.doathing(parm))
                self.eq('bar', await testkid.doathing(parm))
                self.eq(2, parm.get('happened'))

                testkid.onChange('thing:2', testkid._thing2handler)
                self.eq(testkid, await testparent._fireChange('thing:2', (), iden=2))
