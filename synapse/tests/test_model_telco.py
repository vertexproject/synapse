import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class TelcoModelTest(s_t_utils.SynTest):
    async def test_telco_simple(self):
        async with self.getTestCore() as core:

            typ = core.model.type('tel:mob:mcc')
            self.eq((await typ.norm('001'))[0], '001')
            await self.asyncraises(s_exc.BadTypeValu, typ.norm('01'))
            await self.asyncraises(s_exc.BadTypeValu, typ.norm('0001'))

            typ = core.model.type('tel:mob:mnc')
            self.eq((await typ.norm('01'))[0], '01')
            self.eq((await typ.norm('001'))[0], '001')
            await self.asyncraises(s_exc.BadTypeValu, typ.norm('0001'))
            await self.asyncraises(s_exc.BadTypeValu, typ.norm('1'))

            # tel:mob:tac
            oguid = s_common.guid()
            place = s_common.guid()
            props = {'manu': 'Acme Corp',
                     'model': 'eYephone 9000',
                     'internal': 'spYphone 9000',
                     'org': oguid,
                     }
            q = '''[(tel:mob:tac=1 :manu=$p.manu :model=$p.model :internal=$p.internal :org=$p.org)]'''
            nodes = await core.nodes(q, opts={'vars': {'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:tac', 1))
            self.eq(node.get('manu'), 'acme corp')
            self.eq(node.get('model'), 'eyephone 9000')
            self.eq(node.get('internal'), 'spyphone 9000')
            self.eq(node.get('org'), oguid)

            nodes = await core.nodes('[tel:mob:imid=(490154203237518, 310150123456789)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imid', (490154203237518, 310150123456789)))
            self.eq(node.get('imei'), 490154203237518)
            self.eq(node.get('imsi'), 310150123456789)

            nodes = await core.nodes('[tel:mob:imsiphone=(310150123456789, "+7(495) 124-59-83")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imsiphone', (310150123456789, '74951245983')))
            self.eq(node.get('imsi'), 310150123456789)
            self.eq(node.get('phone'), '74951245983')

            nodes = await core.nodes('[tel:mob:mcc=611 :place:country:code=gn]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:mcc', '611'))
            self.eq(node.get('place:country:code'), 'gn')

            nodes = await core.nodes('[ tel:mob:carrier=(001, 02) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:carrier', ('001', '02')))
            self.eq(node.get('mcc'), '001')
            self.eq(node.get('mnc'), '02')

            nodes = await core.nodes('''
                [ tel:mob:cell=*
                    :radio="Pirate "
                    :carrier=(001, 02)
                    :lac=3
                    :cid=4
                    :place=*
                    :place:loc=us.ca.la
                    :place:latlong=(0, 0)
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('carrier'), ('001', '02'))
            self.eq(nodes[0].get('lac'), 3)
            self.eq(nodes[0].get('cid'), 4)
            self.eq(nodes[0].get('radio'), 'pirate.')
            self.eq(nodes[0].get('place:loc'), 'us.ca.la')
            self.eq(nodes[0].get('place:latlong'), (0.0, 0.0))
            self.len(1, await core.nodes('tel:mob:cell :place -> geo:place'))
            self.len(1, await core.nodes('tel:mob:cell -> tel:mob:carrier -> tel:mob:mcc'))

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
                     'imsi': '310150123456789',
                     'imei': '490154203237518',
                     'phone': '123 456 7890',
                     'mac': '00:00:00:00:00:00',
                     'ip': '1.2.3.4',
                     'adid': 'someadid',
                     'name': 'Robert Grey',
                     'email': 'clown@vertex.link',
                     'app': softguid,
                     'data': {'some key': 'some valu',
                              'BEEP': 1}
                     }
            q = '''[(tel:mob:telem=$valu :time=$p.time :place:latlong=$p.latlong :place=$p.place :host=$p.host
             :place:loc=$p.loc :place:latlong:accuracy=$p.accuracy
             :cell=* :imsi=$p.imsi :imei=$p.imei :phone=$p.phone
             :mac=$p.mac :ip=$p.ip :wifi:ap=* :adid=$p.adid
             :name=$p.name :email=$p.email :app=$p.app :data=$p.data :account=*)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:telem', guid))
            self.eq(node.get('time'), 978307200000000)
            self.eq(node.get('place:latlong'), (-1.0, 1.0))
            self.eq(node.get('place'), place)
            self.eq(node.get('host'), host)
            self.eq(node.get('place:loc'), 'us')
            self.eq(node.get('place:latlong:accuracy'), 100)
            self.eq(node.get('imsi'), 310150123456789)
            self.eq(node.get('imei'), 490154203237518)
            self.eq(node.get('phone'), '1234567890')
            self.eq(node.get('mac'), '00:00:00:00:00:00')
            self.eq(node.get('ip'), (4, 0x01020304))
            self.eq(node.get('adid'), 'someadid')
            self.eq(node.get('name'), 'robert grey')
            self.eq(node.get('email'), 'clown@vertex.link')
            self.eq(node.get('app'), softguid)
            self.eq(node.get('data'), {'some key': 'some valu', 'BEEP': 1})
            self.len(1, await core.nodes('tel:mob:telem :cell -> tel:mob:cell'))
            self.len(1, await core.nodes('tel:mob:telem :wifi:ap -> inet:wifi:ap'))
            self.len(1, await core.nodes('tel:mob:telem :account -> inet:service:account'))

    async def test_telco_imei(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[tel:mob:imei=490154203237518]')
            self.len(1, nodes)
            node = nodes[0]
            # proper value
            self.eq(node.ndef, ('tel:mob:imei', 490154203237518))
            self.eq(node.get('serial'), 323751)
            self.eq(node.get('tac'), 49015420)
            # One without the check bit (it gets added)
            nodes = await core.nodes('[tel:mob:imei=39015420323751]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imei', 390154203237519))
            # Invalid checksum
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=(490154203237519)]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=20]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=hehe]')

    async def test_telco_imsi(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[tel:mob:imsi=310150123456789]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imsi', 310150123456789))
            self.eq(node.get('mcc'), '310')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imsi=hehe]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imsi=1111111111111111]')

    async def test_telco_phone(self):
        async with self.getTestCore() as core:
            t = core.model.type('tel:phone')
            norm, subs = await t.norm('123 456 7890')
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'loc': (t.loctype.typehash, 'us', {})}})

            norm, subs = await t.norm('123 456 \udcfe7890')
            self.eq(norm, '1234567890')

            norm, subs = await t.norm(1234567890)
            self.eq(norm, '1234567890')
            self.eq(subs, {'subs': {'loc': (t.loctype.typehash, 'us', {})}})

            norm, subs = await t.norm('+1911')
            self.eq(norm, '1911')
            self.eq(subs, {'subs': {'loc': (t.loctype.typehash, 'us', {})}})

            self.eq(t.repr('12345678901'), '+1 (234) 567-8901')
            self.eq(t.repr('9999999999'), '+9999999999')

            await self.asyncraises(s_exc.BadTypeValu, t.norm(-1))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('+()*'))

            nodes = await core.nodes('[tel:phone="+1 (703) 555-1212" :type=fax ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:phone', '17035551212'))
            self.eq(node.get('loc'), 'us')
            self.eq(node.get('type'), 'fax.')
            self.len(1, await core.nodes('tel:phone:type=fax -> tel:phone:type:taxonomy'))
            # Phone # folding..
            self.len(1, await core.nodes('[tel:phone="+1 (703) 555-2424"]'))
            self.len(1, await core.nodes('tel:phone=17035552424'))
            # Prefix searching
            self.len(2, await core.nodes('tel:phone=1703555*'))

    async def test_telco_call(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ tel:call=*
                    :caller:phone="+1 (703) 555-1212"
                    :recipient:phone="123 456 7890"
                    :period=2001
                    :connected=(true)
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('caller:phone'), '17035551212')
            self.eq(nodes[0].get('recipient:phone'), '1234567890')
            self.eq(nodes[0].get('period'), (978307200000000, 978307200000001, 1))
            self.eq(nodes[0].get('connected'), True)
