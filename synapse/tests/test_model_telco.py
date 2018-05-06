import synapse.exc as s_exc
import synapse.tests.common as s_test


class TelcoModelTest(s_test.SynTest):
    def test_telco_simple(self):
        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                # tel:mob:tac
                props = {'manu': 'Acme Corp',
                         'model': 'eYephone 9000',
                         'internal': 'spYphone 9000',
                         # 'org': '',  FIXME: Add when ou:org is ported
                         }
                node = xact.addNode('tel:mob:tac', 1, props)
                self.eq(node.ndef[1], 1)
                # self.eq(node.get('org'), '')  FIXME: Add when ou:org is ported
                self.eq(node.get('manu'), 'acme corp')
                self.eq(node.get('model'), 'eyephone 9000')
                self.eq(node.get('internal'), 'spyphone 9000')
                # defvals
                node = xact.addNode('tel:mob:tac', 2)
                self.eq(node.get('manu'), '??')
                self.eq(node.get('model'), '??')
                self.eq(node.get('internal'), '??')

                # tel:mob:imid
                node = xact.addNode('tel:mob:imid', (490154203237518, 310150123456789))
                self.eq(node.ndef[1], (490154203237518, 310150123456789))
                self.eq(node.get('imei'), 490154203237518)
                self.eq(node.get('imsi'), 310150123456789)

                # tel:mob:imsiphone
                node = xact.addNode('tel:mob:imsiphone', (310150123456789, '+7(495) 124-59-83'))
                self.eq(node.ndef[1], (310150123456789, '74951245983'))
                self.eq(node.get('imsi'), 310150123456789)
                self.eq(node.get('phone'), '74951245983')

    def test_telco_imei(self):
        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                # proper value
                node = xact.addNode('tel:mob:imei', '490154203237518')
                self.eq(node.ndef[1], 490154203237518)
                self.eq(node.get('serial'), 323751)
                self.eq(node.get('tac'), 49015420)
                # One without the check bit (it gets added)
                node = xact.addNode('tel:mob:imei', '39015420323751')
                self.eq(node.ndef[1], 390154203237519)
                # Invalid checksum
                self.raises(s_exc.BadTypeValu, xact.addNode, 'tel:mob:imei', 490154203237519)
                self.raises(s_exc.BadTypeValu, xact.addNode, 'tel:mob:imei', '20')
                self.raises(s_exc.BadTypeValu, xact.addNode, 'tel:mob:imei', 'hehe')

    def test_telco_imsi(self):
        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                node = xact.addNode('tel:mob:imsi', '310150123456789')
                self.eq(node.ndef[1], 310150123456789)
                self.eq(node.get('mcc'), 310)
                self.raises(s_exc.BadTypeValu, xact.addNode, 'tel:mob:imsi', 'hehe')
                self.raises(s_exc.BadTypeValu, xact.addNode, 'tel:mob:imsi', 1111111111111111)

    def test_telco_phone(self):
        with self.getTestCore() as core:
            t = core.model.type('tel:phone')
            norm, subs = t.norm('123 456 7890')
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'cc': 'us'}})

            norm, subs = t.norm(1234567890)
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'cc': 'us'}})

            norm, subs = t.norm('+1911')
            self.eq(norm, '1911')
            self.eq(subs, {'subs': {'cc': 'us'}})

            self.eq(t.repr('12345678901'), '+1 (234) 567-8901')
            self.eq(t.repr('9999999999'), '+9999999999')

            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.raises(s_exc.BadTypeValu, t.norm, '+()*')

            with core.xact(write=True) as xact:
                node = xact.addNode('tel:phone', '+1 (703) 555-1212')
                self.eq(node.ndef[1], '17035551212')
                self.eq(node.get('cc'), 'us')

class Fixme:

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
