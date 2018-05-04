import synapse.tests.common as s_test

import unittest
raise unittest.SkipTest('US GOV MODEL')

class UsGovTest(s_test.SynTest):

    def test_models_usgov_cage(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('gov:us:cage', '7QE71', phone0=17035551212)
            self.eq(node[1].get('gov:us:cage'), '7qe71')
            self.eq(node[1].get('gov:us:cage:phone0'), 17035551212)
            self.nn(core.getTufoByProp('tel:phone', 17035551212))
