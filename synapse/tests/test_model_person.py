
from synapse.tests.common import *

class PersonTest(SynTest):

    def test_models_person(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('ps:fullname','Kenshoto,Invisigoth')

            self.eq(node[1].get('ps:fullname:sur'),'kenshoto')
            self.eq(node[1].get('ps:fullname:given'),'invisigoth')

            self.nn( core.getTufoByProp('ps:name','kenshoto') )
            self.nn( core.getTufoByProp('ps:name','invisigoth') )

    def test_models_person_name(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('ps:name','Invisigoth')
            self.eq( node[1].get('ps:name'), 'invisigoth' )

    def test_models_person_fullname(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('ps:fullname','Kenshoto,Invisigoth')

            self.eq(node[1].get('ps:fullname:sur'),'kenshoto')
            self.eq(node[1].get('ps:fullname:given'),'invisigoth')

            self.nn( core.getTufoByProp('ps:name','kenshoto') )
            self.nn( core.getTufoByProp('ps:name','invisigoth') )

