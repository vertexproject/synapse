import synapse.glob as s_glob

import synapse.tests.utils as s_t_utils

class GlobTest(s_t_utils.SynTest):

    def test_glob_sync(self):

        async def afoo():
            return 42

        retn = s_glob.sync(afoo())
        self.eq(retn, 42)
