import synapse.lib.types as s_types

from synapse.tests.common import *

class TelcoTest(SynTest):

    def test_model_type_phone(self):
        tlib = s_types.TypeLib()
        prop = 'tel:phone'

        self.eq(tlib.getTypeNorm(prop, 1234567890)[0], 1234567890)
        self.eq(tlib.getTypeParse(prop, '123 456 7890')[0], 1234567890)

        self.eq(tlib.getTypeRepr(prop, 12345678901), '+1 (234) 567-8901')
        self.eq(tlib.getTypeRepr(prop, 9999999999), '+9999999999')

    def test_model_telco_phone(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('tel:phone', '+1 (703) 555-1212')
            self.eq(node[1].get('tel:phone'), 17035551212)
            self.eq(node[1].get('tel:phone:cc'), 'us')

    def test_model_telco_cast_loc_us(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeCast('tel:loc:us', '7035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '17035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '0017035551212'), 17035551212)
            self.eq(core.getTypeCast('tel:loc:us', '01117035551212'), 17035551212)

            self.eq(core.getTypeCast('tel:loc:us', '+865551212'), 865551212)
            self.eq(core.getTypeCast('tel:loc:us', '+17035551212'), 17035551212)

            self.eq(core.getTypeCast('tel:loc:us', '7(495) 124-59-83'), 74951245983)
            self.eq(core.getTypeCast('tel:loc:us', '+7(495) 124-59-83'), 74951245983)

    def test_model_telco_imei(self):

        with self.getRamCore() as core:

            # a perfect one...
            valu, subs = core.getTypeNorm('tel:mob:imei', '490154203237518')
            self.eq(valu, 490154203237518)

            # invalid checksum bit
            self.raises(BadTypeValu, core.getTypeNorm, 'tel:mob:imei', '490154203237519')

            # one without it's check bit ( gets check bit added )
            valu, subs = core.getTypeNorm('tel:mob:imei', '49015420323751')
            self.eq(valu, 490154203237518)

            node = core.formTufoByProp('tel:mob:imei', 49015420323751)
            self.eq(node[1].get('tel:mob:imei'), 490154203237518)
            self.eq(node[1].get('tel:mob:imei:tac'), 49015420)
            self.eq(node[1].get('tel:mob:imei:serial'), 323751)

            self.raises(BadTypeValu, core.formTufoByProp, 'tel:mob:imei', 20)
            self.raises(BadTypeValu, core.formTufoByProp, 'tel:mob:imei', 'hehe')

    def test_model_telco_imsi(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('tel:mob:imsi', 310150123456789)
            self.eq(node[1].get('tel:mob:imsi'), 310150123456789)
            self.eq(node[1].get('tel:mob:imsi:mcc'), 310)

            node = core.formTufoByProp('tel:mob:imsi', '310150123456789')
            self.eq(node[1].get('tel:mob:imsi'), 310150123456789)
            self.eq(node[1].get('tel:mob:imsi:mcc'), 310)

            # < 15 digits
            self.raises(BadTypeValu, core.formTufoByProp, 'tel:mob:imsi', 'hehe')
            self.raises(BadTypeValu, core.formTufoByProp, 'tel:mob:imsi', 1111111111111111)

    def test_model_telco_imsiphone(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('tel:mob:imsiphone', (310150123456789, '+7(495) 124-59-83'))
            self.eq(node[1].get('tel:mob:imsiphone:imsi'), 310150123456789)
            self.eq(node[1].get('tel:mob:imsiphone:phone'), 74951245983)

            self.nn(core.getTufoByProp('tel:phone', 74951245983))
            self.nn(core.getTufoByProp('tel:mob:imsi', 310150123456789))
