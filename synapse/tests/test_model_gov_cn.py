from synapse.tests.common import *

class CnGovTest(SynTest):

    def test_models_cngov_mucd(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('gov:cn:mucd', 61786)

            self.nn(node)
            self.nn(core.getTufoByProp('ou:org:name', 'chinese pla unit 61786'))
