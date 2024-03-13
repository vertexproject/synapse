import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class SciModelTest(s_t_utils.SynTest):

    async def test_model_sci(self):

        async with self.getTestCore() as core:

            # TODO implement model element tests
