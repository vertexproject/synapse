
from synapse.tests.common import SynTest

class CnGovTest(SynTest):

    def test_models_cngov_mucd(self):

        with self.getTestCore() as core:
            formname = 'gov:cn:mucd'

            with core.snap(write=True) as snap:

                n0 = snap.addNode('gov:cn:mucd', 61786)
                n1 = snap.addNode('gov:cn:icp', 12345678)

            self.eq(n0.ndef, ('gov:cn:mucd', 61786))
            self.eq(n1.ndef, ('gov:cn:icp', 12345678))

            # FIXME 010 - after orgs add test to make sure the pla org was created

            # FIXME 010 - after orgs add tests for gov:cn:orgicp
