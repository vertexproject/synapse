import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class CnGovTest(s_t_utils.SynTest):

    async def test_models_cngov_mucd(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[gov:cn:icp=12345678]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('gov:cn:icp', 12345678))

            nodes = await core.nodes('[gov:cn:mucd=61786]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('gov:cn:mucd', 61786))
