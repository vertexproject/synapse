from synapse.tests.common import *

class UsGovTest(SynTest):

    def test_models_usgov_cage(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)
            node = core.formTufoByProp('gov:us:cage','7QE71', phone=17035551212)
            self.eq( node[1].get('gov:us:cage'), '7qe71' )
            self.eq( node[1].get('gov:us:cage:phone'), 17035551212 )
            self.nn( core.getTufoByProp('tel:phone',17035551212) )
