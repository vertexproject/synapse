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

            nodes = await core.nodes('[tel:mob:mcc=611 :loc=gn]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:mcc', '611'))
            self.eq(node.get('loc'), 'gn')

            nodes = await core.nodes('[(tel:mob:carrier=(001, 02) :org=$org :loc=us :tadig=USAVX )]', opts={'vars': {'org': oguid}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:carrier', ('001', '02')))
            self.eq(node.get('mcc'), '001')
            self.eq(node.get('mnc'), '02')
            self.eq(node.get('org'), oguid)
            self.eq(node.get('loc'), 'us')
            self.eq(node.get('tadig'), 'USAVX')

            self.len(1, await core.nodes('tel:mob:carrier -> tel:mob:tadig'))

            q = '[(tel:mob:cell=((001, 02), 3, 4) :radio="Pirate " :place=$place :loc=us.ca.la :latlong=(0, 0))]'
            nodes = await core.nodes(q, opts={'vars': {'place': place}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:cell', (('001', '02'), 3, 4)))
            self.eq(node.get('carrier'), ('001', '02'))
            self.eq(node.get('carrier:mcc'), '001')
            self.eq(node.get('carrier:mnc'), '02')
            self.eq(node.get('lac'), 3)
            self.eq(node.get('cid'), 4)
            self.eq(node.get('loc'), 'us.ca.la')
            self.eq(node.get('radio'), 'pirate')
            self.eq(node.get('latlong'), (0.0, 0.0))
            self.eq(node.get('place'), place)
            self.len(1, await core.nodes('tel:mob:mcc=001'))

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
            q = '''[(tel:mob:telem=$valu :time=$p.time :latlong=$p.latlong :place=$p.place :host=$p.host
             :loc=$p.loc :accuracy=$p.accuracy :cell=$p.cell :imsi=$p.imsi :imei=$p.imei :phone=$p.phone
             :mac=$p.mac :ipv4=$p.ipv4 :ipv6=$p.ipv6 :wifi=$p.wifi :adid=$p.adid :aaid=$p.aaid :idfa=$p.idfa
             :name=$p.name :email=$p.email :acct=$p.acct :app=$p.app :data=$p.data :account=*)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:telem', guid))
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
            q = '''[(tel:call=$valu :src=$p.src :dst=$p.dst :time=$p.time :duration=$p.duration
            :connected=$p.connected :text=$p.text :file=$p.file)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:call', guid))
            self.eq(node.get('src'), '17035551212')
            self.eq(node.get('dst'), '1234567890')
            self.eq(node.get('time'), 978307200000)
            self.eq(node.get('duration'), 90)
            self.eq(node.get('connected'), True)
            self.eq(node.get('text'), 'I said some stuff')
            self.eq(node.get('file'), 'sha256:' + 64 * 'f')

    async def test_telco_txtmesg(self):
        async with self.getTestCore() as core:
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
            q = '''[(tel:txtmesg=$valu :from=$p.from :to=$p.to :recipients=$p.recipients :svctype=$p.svctype
            :time=$p.time :text=$p.text :file=$p.file)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:txtmesg', guid))
            self.eq(node.get('from'), '17035551212')
            self.eq(node.get('to'), '1234567890')
            self.eq(node.get('recipients'), ('5554443333', '5678901234'))
            self.eq(node.get('svctype'), 'sms')
            self.eq(node.get('time'), 978307200000)
            self.eq(node.get('text'), 'I wrote some stuff')
            self.eq(node.get('file'), 'sha256:' + 64 * 'b')
            # add other valid message types
            nodes = await core.nodes('[tel:txtmesg=* :svctype=mms]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('svctype'), 'mms')
            nodes = await core.nodes('[tel:txtmesg=* :svctype=" MMS"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('svctype'), 'mms')
            nodes = await core.nodes('[tel:txtmesg=* :svctype=rcs]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('svctype'), 'rcs')
            # no message type specified
            nodes = await core.nodes('[tel:txtmesg=*]')
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('svctype'))
            # add bad svc type
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:txtmesg=* :svctype=newp]')
