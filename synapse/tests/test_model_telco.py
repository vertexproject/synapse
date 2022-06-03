import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class TelcoModelTest(s_t_utils.SynTest):
    async def test_telco_simple(self):
        async with self.getTestCore() as core:

            typ = core.model.type('tel:mob:mcc')
            self.eq(typ.norm('001')[0], '001')
            self.raises(s_exc.BadTypeValu, typ.norm, '01')
            self.raises(s_exc.BadTypeValu, typ.norm, '0001')

            typ = core.model.type('tel:mob:mnc')
            self.eq(typ.norm('01')[0], '01')
            self.eq(typ.norm('001')[0], '001')
            self.raises(s_exc.BadTypeValu, typ.norm, '0001')
            self.raises(s_exc.BadTypeValu, typ.norm, '1')

            async with await core.snap() as snap:
                # tel:mob:tac
                oguid = s_common.guid()
                place = s_common.guid()
                props = {'manu': 'Acme Corp',
                         'model': 'eYephone 9000',
                         'internal': 'spYphone 9000',
                         'org': oguid,
                         }
                node = await snap.addNode('tel:mob:tac', 1, props)
                self.eq(node.ndef[1], 1)
                self.eq(node.get('manu'), 'acme corp')
                self.eq(node.get('model'), 'eyephone 9000')
                self.eq(node.get('internal'), 'spyphone 9000')
                self.eq(node.get('org'), oguid)
                # defvals
                node = await snap.addNode('tel:mob:tac', 2)

                # tel:mob:imid
                node = await snap.addNode('tel:mob:imid', (490154203237518, 310150123456789))
                self.eq(node.ndef[1], (490154203237518, 310150123456789))
                self.eq(node.get('imei'), 490154203237518)
                self.eq(node.get('imsi'), 310150123456789)

                # tel:mob:imsiphone
                node = await snap.addNode('tel:mob:imsiphone', (310150123456789, '+7(495) 124-59-83'))
                self.eq(node.ndef[1], (310150123456789, '74951245983'))
                self.eq(node.get('imsi'), 310150123456789)
                self.eq(node.get('phone'), '74951245983')

                # tel:mob:mcc
                node = await snap.addNode('tel:mob:mcc', '611', {'loc': 'gn'})
                self.eq(node.ndef[1], '611')
                self.eq(node.get('loc'), 'gn')

                # tel:mob:carrier
                node = await snap.addNode('tel:mob:carrier', ('001', '02'), {'org': oguid, 'loc': 'us'})
                self.eq(node.ndef[1], ('001', '02'))
                self.eq(node.get('mcc'), '001')
                self.eq(node.get('mnc'), '02')
                self.eq(node.get('org'), oguid)
                self.eq(node.get('loc'), 'us')

                # tel:mob:cell
                node = await snap.addNode('tel:mob:cell', (('001', '02'), 3, 4), {'radio': 'Pirate  ',
                                                                                  'latlong': (0, 0),
                                                                                  'place': place,
                                                                                  'loc': 'us.ca.la'})
                self.eq(node.get('carrier'), ('001', '02'))
                self.eq(node.get('carrier:mcc'), '001')
                self.eq(node.get('carrier:mnc'), '02')
                self.eq(node.get('lac'), 3)
                self.eq(node.get('cid'), 4)
                self.eq(node.get('loc'), 'us.ca.la')
                self.eq(node.get('radio'), 'pirate')
                self.eq(node.get('latlong'), (0.0, 0.0))
                self.eq(node.get('place'), place)

                await self.checkNodes(core, (('tel:mob:mcc', '001'),))

                # tel:mob:telem
                guid = s_common.guid()
                host = s_common.guid()
                softguid = s_common.guid()
                props = {'time': '2001',
                         'latlong': (-1, 1),
                         'place': place,
                         'host': host,
                         'loc': 'us',
                         'accuracy': '100mm',
                         'cell': (('001', '02'), 3, 4),
                         'imsi': '310150123456789',
                         'imei': '490154203237518',
                         'phone': '123 456 7890',
                         'mac': '00:00:00:00:00:00',
                         'ipv4': '1.2.3.4',
                         'ipv6': '::1',
                         'wifi': ('The Best SSID2', '00:11:22:33:44:55'),
                         'adid': 'someadid',
                         'aaid': 'somestr',
                         'idfa': 'someotherstr',
                         'name': 'Robert Grey',
                         'email': 'clown@vertex.link',
                         'acct': ('vertex.link', 'clown'),
                         'app': softguid,
                         'data': {'some key': 'some valu',
                                  'BEEP': 1}
                         }
                node = await snap.addNode('tel:mob:telem', guid, props)
                self.eq(node.ndef[1], guid)
                self.eq(node.get('time'), 978307200000)
                self.eq(node.get('latlong'), (-1.0, 1.0))
                self.eq(node.get('place'), place)
                self.eq(node.get('host'), host)
                self.eq(node.get('loc'), 'us')
                self.eq(node.get('accuracy'), 100)
                self.eq(node.get('cell'), (('001', '02'), 3, 4))
                self.eq(node.get('cell:carrier'), ('001', '02'))
                self.eq(node.get('imsi'), 310150123456789)
                self.eq(node.get('imei'), 490154203237518)
                self.eq(node.get('phone'), '1234567890')
                self.eq(node.get('mac'), '00:00:00:00:00:00')
                self.eq(node.get('ipv4'), 0x01020304)
                self.eq(node.get('ipv6'), '::1')
                self.eq(node.get('wifi'), ('The Best SSID2', '00:11:22:33:44:55')),
                self.eq(node.get('wifi:ssid'), 'The Best SSID2')
                self.eq(node.get('wifi:bssid'), '00:11:22:33:44:55')
                self.eq(node.get('adid'), 'someadid')
                self.eq(node.get('aaid'), 'somestr')
                self.eq(node.get('idfa'), 'someotherstr')
                self.eq(node.get('name'), 'robert grey')
                self.eq(node.get('email'), 'clown@vertex.link')
                self.eq(node.get('acct'), ('vertex.link', 'clown'))
                self.eq(node.get('app'), softguid)
                self.eq(node.get('data'), {'some key': 'some valu', 'BEEP': 1})

    async def test_telco_imei(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                # proper value
                node = await snap.addNode('tel:mob:imei', '490154203237518')
                self.eq(node.ndef[1], 490154203237518)
                self.eq(node.get('serial'), 323751)
                self.eq(node.get('tac'), 49015420)
                # One without the check bit (it gets added)
                node = await snap.addNode('tel:mob:imei', '39015420323751')
                self.eq(node.ndef[1], 390154203237519)
                # Invalid checksum
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:mob:imei', 490154203237519))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:mob:imei', '20'))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:mob:imei', 'hehe'))

    async def test_telco_imsi(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('tel:mob:imsi', '310150123456789')
                self.eq(node.ndef[1], 310150123456789)
                self.eq(node.get('mcc'), '310')
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:mob:imsi', 'hehe'))
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:mob:imsi', 1111111111111111))

    async def test_telco_phone(self):
        async with self.getTestCore() as core:
            t = core.model.type('tel:phone')
            norm, subs = t.norm('123 456 7890')
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'loc': 'us'}})

            norm, subs = t.norm('123 456 \udcfe7890')
            self.eq(norm, '1234567890')

            norm, subs = t.norm(1234567890)
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'loc': 'us'}})

            norm, subs = t.norm('+1911')
            self.eq(norm, '1911')
            self.eq(subs, {'subs': {'loc': 'us'}})

            self.eq(t.repr('12345678901'), '+1 (234) 567-8901')
            self.eq(t.repr('9999999999'), '+9999999999')

            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.raises(s_exc.BadTypeValu, t.norm, '+()*')

            async with await core.snap() as snap:
                node = await snap.addNode('tel:phone', '+1 (703) 555-1212')
                self.eq(node.ndef[1], '17035551212')
                self.eq(node.get('loc'), 'us')
                node = await snap.addNode('tel:phone', '+1 (703) 555-2424')
                # Esnap search
                nodes = await snap.nodes('tel:phone=17035552424')
                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], '17035552424')
                # Prefix search
                nodes = await snap.nodes('tel:phone=1703555*')
                self.len(2, nodes)

    async def test_telco_call(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                guid = s_common.guid()
                props = {
                    'src': '+1 (703) 555-1212',
                    'dst': '123 456 7890',
                    'time': '2001',
                    'duration': 90,
                    'connected': True,
                    'text': 'I said some stuff',
                    'file': 'sha256:' + 64 * 'f',
                }
                node = await snap.addNode('tel:call', guid, props)
                self.eq(node.ndef[1], guid)
                self.eq(node.get('src'), '17035551212')
                self.eq(node.get('dst'), '1234567890')
                self.eq(node.get('time'), 978307200000)
                self.eq(node.get('duration'), 90)
                self.eq(node.get('connected'), True)
                self.eq(node.get('text'), 'I said some stuff')
                self.eq(node.get('file'), 'sha256:' + 64 * 'f')

    async def test_telco_txtmesg(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                guid = s_common.guid()
                props = {
                    'from': '+1 (703) 555-1212',
                    'to': '123 456 7890',
                    'recipients': ('567 890 1234', '555 444 3333'),
                    'svctype': 'sms',
                    'time': '2001',
                    'text': 'I wrote some stuff',
                    'file': 'sha256:' + 64 * 'b',
                }
                node = await snap.addNode('tel:txtmesg', guid, props)
                self.eq(node.ndef[1], guid)
                self.eq(node.get('from'), '17035551212')
                self.eq(node.get('to'), '1234567890')
                self.eq(node.get('recipients'), ('5554443333', '5678901234'))
                self.eq(node.get('svctype'), 'sms')
                self.eq(node.get('time'), 978307200000)
                self.eq(node.get('text'), 'I wrote some stuff')
                self.eq(node.get('file'), 'sha256:' + 64 * 'b')

                # add other valid message types
                guid = s_common.guid()
                node = await snap.addNode('tel:txtmesg', guid, {'svctype': 'mms'})
                self.eq(node.ndef[1], guid)

                guid = s_common.guid()
                node = await snap.addNode('tel:txtmesg', guid, {'svctype': ' MMS'})
                self.eq(node.ndef[1], guid)

                guid = s_common.guid()
                node = await snap.addNode('tel:txtmesg', guid, {'svctype': 'rcs'})
                self.eq(node.ndef[1], guid)

                # no message type specified
                guid = s_common.guid()
                node = await snap.addNode('tel:txtmesg', guid, {'text': 'no message type'})
                self.eq(node.ndef[1], guid)

                # add bad svc type
                guid = s_common.guid()
                await self.asyncraises(s_exc.BadTypeValu, snap.addNode('tel:txtmesg', guid, {'svctype': 'foo'}))
