import synapse.common as s_common

import synapse.tests.utils as s_t_utils
import synapse.tools.guid as s_guid

class TestGuid(s_t_utils.SynTest):

    def test_tools_guid(self):
        argv = []
        outp = self.getTestOutp()
        s_guid.main(argv, outp=outp)
        self.true(s_common.isguid(str(outp)))
