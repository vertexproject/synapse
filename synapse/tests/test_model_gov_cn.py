import synapse.common as s_common
import synapse.tests.common as s_test

class CnGovTest(s_test.SynTest):

    def test_models_cngov_mucd(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                org0 = s_common.guid()
                props = {
                    'org': org0
                }
                node = await snap.addNode('gov:cn:icp', 12345678, props)
                self.eq(node.ndef[1], 12345678)
                self.eq(node.get('org'), org0)

                node = await snap.addNode('gov:cn:mucd', 61786)
                self.eq(node.ndef[1], 61786)
