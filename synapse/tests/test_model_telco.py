import synapse.exc as s_exc

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

            typ = core.model.type('tel:mob:tadig')
            self.eq((await typ.norm('USAWZ'))[0], 'USAWZ')
            with self.raises(s_exc.BadTypeValu):
                await typ.norm('usawz')

            with self.raises(s_exc.BadTypeValu):
                await typ.norm('US')

            # tel:mob:tac
            props = {'model': 'eYephone 9000'}
            q = '''[(tel:mob:tac=1 :model=$p.model)]'''
            nodes = await core.nodes(q, opts={'vars': {'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:tac', 1))
            self.propeq(node, 'model', 'eYephone 9000')

            nodes = await core.nodes('[tel:mob:imid=(490154203237518, 310150123456789)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imid', ('490154203237518', '310150123456789')))
            self.propeq(node, 'imei', '490154203237518')
            self.propeq(node, 'imsi', '310150123456789')

            nodes = await core.nodes('[tel:mob:imsiphone=(310150123456789, "+7(495) 124-59-83")]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imsiphone', ('310150123456789', '74951245983')))
            self.propeq(node, 'imsi', '310150123456789')
            self.propeq(node, 'phone', '74951245983')

            nodes = await core.nodes('[tel:mob:mcc=611 :place:country:code=gn]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:mcc', '611'))
            self.propeq(node, 'place:country:code', 'gn')

            nodes = await core.nodes("[ tel:mob:carrier=('001', '02') ]")
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:carrier', ('001', '02')))
            self.propeq(node, 'mcc', '001')
            self.propeq(node, 'mnc', '02')

            nodes = await core.nodes('''
                [ tel:mob:cell=*
                    :radio="Pirate "
                    :carrier=('001', '02') as tel:mob:carrier
                    :lac=3
                    :cid=4
                    :place=* as geo:place
                    :place:loc=us.ca.la
                    :place:latlong=(0, 0)
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'carrier', ('001', '02'))
            self.propeq(nodes[0], 'lac', 3)
            self.propeq(nodes[0], 'cid', 4)
            self.propeq(nodes[0], 'radio', 'pirate.')
            self.propeq(nodes[0], 'place:loc', 'us.ca.la')
            self.propeq(nodes[0], 'place:latlong', (0.0, 0.0))
            self.len(1, await core.nodes('tel:mob:cell :place -> geo:place'))
            self.len(1, await core.nodes('tel:mob:cell -> tel:mob:carrier -> tel:mob:mcc'))

    async def test_telco_imei(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[tel:mob:imei=490154203237518]')
            self.len(1, nodes)
            node = nodes[0]
            # proper value with tac/serial subs carved from the regex
            self.eq(node.ndef, ('tel:mob:imei', '490154203237518'))
            self.propeq(node, 'serial', 323751)
            self.propeq(node, 'tac', 49015420)
            # the full 15 digit IMEI is required
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=39015420323751]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=20]')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[tel:mob:imei=hehe]')

    async def test_telco_imsi(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[tel:mob:imsi=310150123456789]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('tel:mob:imsi', '310150123456789'))
            self.propeq(node, 'mcc', '310')
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
            self.propeq(node, 'loc', 'us')
            self.propeq(node, 'type', 'fax.')
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
            self.propeq(nodes[0], 'caller:phone', '17035551212')
            self.propeq(nodes[0], 'recipient:phone', '1234567890')
            self.propeq(nodes[0], 'period', (978307200000000, 978307200000001, 1))
            self.propeq(nodes[0], 'connected', True)
