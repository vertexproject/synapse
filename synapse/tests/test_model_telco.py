from synapse.tests.common import *

class TelcoTest(SynTest):

    def test_model_telco_phone(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            node = core.formTufoByProp('tel:phone', '+1 (703) 555-1212')
            self.eq(node[1].get('tel:phone'), 17035551212)
            self.eq(node[1].get('tel:phone:cc'), 'us')

    def test_model_telco_cast_loc_us(self):
        with s_cortex.openurl('ram:///') as core:
            self.eq(core.getTypeCast('tel:loc:us', '7035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '17035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '0017035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '01117035551212'), 17035551212)

            self.eq(core.getTypeCast('tel:loc:us', '+865551212'), 865551212)
            self.eq(core.getTypeCast('tel:loc:us', '+17035551212'), 17035551212)

            self.eq(core.getTypeCast('tel:loc:us', '7(495) 124-59-83'), 74951245983)
            self.eq(core.getTypeCast('tel:loc:us', '+7(495) 124-59-83'), 74951245983)
