import synapse.tests.utils as s_t_utils

class UsGovTest(s_t_utils.SynTest):

    async def test_models_usgov_cage(self):

        async with self.getTestCore() as core:
            # gov:us:cage is a base:id and preserves case
            valu = '7QE71'
            nodes = await core.nodes('[ gov:us:cage=$valu ]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('gov:us:cage', '7QE71'))
