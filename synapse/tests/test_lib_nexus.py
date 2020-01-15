import synapse.lib.nexus as s_nexus
import synapse.tests.utils as s_t_utils


class SampleNexus(s_nexus.Nexus):

    async def __anit__(self, iden, parent=None):
        self.iden = iden

        await s_nexus.Nexus.__anit__(self, iden=iden, parent=parent)

    async def doathing(self, eventdict):
        return await self._fireChange('thing:doathing', (eventdict,))

    @s_nexus.Nexus.onChng('thing:doathing')
    async def _doathinghandler(self, parms):
        eventdict, = parms
        eventdict['happened'] = self.iden
        return 42

class SampleNexus2(SampleNexus):
    async def doathing(self, eventdict):
        return await self._fireChange('thing:doathing', (eventdict,))

class NexusTest(s_t_utils.SynTest):
    async def test_nexus(self):
        async with await SampleNexus.anit(1) as testparent:
            parm = {}
            self.eq(42, await testparent.doathing(parm))
            self.eq(1, parm.get('happened'))
            async with await SampleNexus2.anit(2, parent=testparent) as testkid:
                parm = {}
                self.eq(42, await testkid.doathing(parm))
                self.eq(2, parm.get('happened'))
