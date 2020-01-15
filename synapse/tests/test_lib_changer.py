import synapse.lib.changer as s_changer
import synapse.tests.utils as s_t_utils


class SampleChanger(s_changer.Changer):

    async def __anit__(self, iden, parent=None):
        self.iden = iden

        await s_changer.Changer.__anit__(self, iden=iden, parent=parent)

    async def doathing(self, eventdict):
        return await self._fireChange(('thing:doathing', (eventdict,)))

    @s_changer.Changer.onChng('thing:doathing')
    async def _doathinghandler(self, mesg):
        eventdict, = mesg[1]
        eventdict['happened'] = self.iden
        return 42

class SampleChanger2(SampleChanger):
    async def doathing(self, eventdict):
        return await self._fireChange((('thing:doathing', self.iden), (eventdict,)))

class ChangerTest(s_t_utils.SynTest):
    async def test_changer(self):
        async with await SampleChanger.anit(1) as testparent:
            parm = {}
            self.eq(42, await testparent.doathing(parm))
            self.eq(1, parm.get('happened'))
            async with await SampleChanger2.anit(2, parent=testparent) as testkid:
                parm = {}
                self.eq(42, await testkid.doathing(parm))
                self.eq(2, parm.get('happened'))
