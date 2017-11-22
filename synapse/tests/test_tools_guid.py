from synapse.tests.common import *
import synapse.tools.guid as s_guid

class TestGuid(SynTest):

    def test_tools_guid(self):
        argv = []
        outp = self.getTestOutp()
        s_guid.main(argv, outp=outp)
        self.true(isguid(str(outp)))
