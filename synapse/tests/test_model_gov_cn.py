import synapse.tests.common as s_test

class CnGovTest(s_test.SynTest):

    def test_models_cngov_mucd(self):

        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                icp = xact.addNode('gov:cn:icp', 12345)
                mucd = xact.addNode('gov:cn:mucd', 61786)
