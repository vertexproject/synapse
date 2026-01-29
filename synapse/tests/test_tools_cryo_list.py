import synapse.tests.utils as s_t_utils
import synapse.tools.cryo.list as s_cryolist

class CryoListTest(s_t_utils.SynTest):

    async def test_cryolist(self):

        async with self.getTestCryo() as cryo:

            items = [(None, {'key': i}) for i in range(20)]

            tank = await cryo.init('hehe')
            await tank.puts(items)

            cryourl = cryo.getLocalUrl()

            argv = [cryourl]
            retn, outp = await self.execToolMain(s_cryolist.main, argv)

            self.eq(0, retn)
            outp.expect(cryourl)
            outp.expect('hehe: ')
            outp.expect("'indx': 20,")
            outp.expect("'entries': 20}")
