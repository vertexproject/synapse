import synapse.tests.utils as s_test

class TransportTest(s_test.SynTest):

    async def test_model_transport(self):

        async with self.getTestCore() as core:

            craft = (await core.nodes('[ transport:air:craft=* :tailnum=FF023 :type=helicopter :built=202002 :make=boeing :model=747 :serial=1234 :operator=*]'))[0]
            self.eq('helicopter', craft.get('type'))
            self.eq(1580515200000, craft.get('built'))
            self.eq('boeing', craft.get('make'))
            self.eq('747', craft.get('model'))
            self.eq('1234', craft.get('serial'))
            self.nn(craft.get('operator'))

            tailnum = (await core.nodes('transport:air:tailnum=FF023 [ :type=fighter ]'))[0]
            flightnum = (await core.nodes('[ transport:air:flightnum="ua 2437" :carrier=* :from:port=IAD :to:port=LAS :stops=(IAD,VISI,LAS) ]'))[0]

            flight = (await core.nodes('''
                [ transport:air:flight=*
                    :num=UA2437
                    :scheduled:departure=20200202
                    :scheduled:arrival=20200203
                    :departed=2020020202
                    :arrived=202002020302
                    :carrier=*
                    :craft=*
                    :from:port=IAD
                    :to:port=LAS
                    :stops=(iad, visi, las)
                    :cancelled=true
                ]'''))[0]

            self.len(1, await core.nodes('transport:air:flight -> transport:air:craft'))

            self.eq('ua2437', flight.get('num'))
            self.eq(1580601600000, flight.get('scheduled:departure'))
            self.eq(1580688000000, flight.get('scheduled:arrival'))
            self.eq(1580608800000, flight.get('departed'))
            self.eq(1580612520000, flight.get('arrived'))
            self.true(flight.get('cancelled'))

            self.nn(flight.get('carrier'))

            self.eq('las', flight.get('to:port'))
            self.eq('iad', flight.get('from:port'))

            flightiden = flight.ndef[1]
            occup = (await core.nodes(f'[ transport:air:occupant=* :flight={flightiden} :seat=1A :contact=* ]'))[0]

            self.eq('1a', occup.get('seat'))
            self.len(1, await core.nodes('transport:air:occupant -> ps:contact'))
            self.len(1, await core.nodes('transport:air:occupant -> transport:air:flight'))

            telem = (await core.nodes('''
                [ transport:air:telem=*
                    :flight=*
                    :latlong=(20.22, 80.1111)
                    :loc=us
                    :place=*
                    :course=-280.9
                    :heading=99.02
                    :speed=374km/h
                    :airspeed=24ft/sec
                    :verticalspeed=-20feet/sec
                    :accuracy=10m
                    :altitude=9144m
                    :altitude:accuracy=10m
                    :time=20200202
                ]'''))[0]
            self.nn(telem.get('flight'))
            self.nn(telem.get('place'))
            self.eq((20.22, 80.1111), telem.get('latlong'))
            self.eq('us', telem.get('loc'))
            self.eq(10000, telem.get('accuracy'))
            self.eq(103888, telem.get('speed'))
            self.eq(7315, telem.get('airspeed'))
            self.eq(-6096, telem.get('verticalspeed'))
            self.eq(6380152800, telem.get('altitude'))
            self.eq(10000, telem.get('altitude:accuracy'))
            self.eq(1580601600000, telem.get('time'))
            self.eq('79.1', telem.get('course'))
            self.eq('99.02', telem.get('heading'))

            vessel = (await core.nodes('''[
                transport:sea:vessel=*
                    :mmsi=123456789
                    :name="Slice of Life"
                    :flag=us
                    :imo="IMO 1234567"
                    :built=2020
                    :make="The Vertex Project"
                    :model="Speed Boat 9000"
                    :length=20m
                    :beam=10m
                    :operator=*
                ]'''))[0]
            self.eq('123456789', vessel.get('mmsi'))
            self.eq('slice of life', vessel.get('name'))
            self.eq('the vertex project', vessel.get('make'))
            self.eq('speed boat 9000', vessel.get('model'))
            self.eq('us', vessel.get('flag'))
            self.eq('imo1234567', vessel.get('imo'))
            self.eq(1577836800000, vessel.get('built'))
            self.eq(20000, vessel.get('length'))
            self.eq(10000, vessel.get('beam'))
            self.nn(vessel.get('operator'))

            self.len(1, await core.nodes('transport:sea:vessel:imo^="IMO 123"'))

            seatelem = (await core.nodes('''[
                 transport:sea:telem=*
                    :time=20200202
                    :vessel=*
                    :latlong=(20.22, 80.1111)
                    :loc=us
                    :place=*
                    :course=-280.9
                    :heading=99.02
                    :speed=c
                    :accuracy=10m
                    :draft=20m
                    :airdraft=30m
                    :destination=*
                    :destination:name=woot
                    :destination:eta=20200203
            ]'''))[0]

            self.nn(seatelem.get('place'))
            self.eq((20.22, 80.1111), seatelem.get('latlong'))
            self.eq('us', seatelem.get('loc'))
            self.eq(10000, seatelem.get('accuracy'))
            self.eq(1580601600000, seatelem.get('time'))
            self.eq(20000, seatelem.get('draft'))
            self.eq(30000, seatelem.get('airdraft'))
            self.eq(299792458000, seatelem.get('speed'))
            self.eq('79.1', seatelem.get('course'))
            self.eq('99.02', seatelem.get('heading'))

            self.nn(seatelem.get('destination'))
            self.eq('woot', seatelem.get('destination:name'))
            self.eq(1580688000000, seatelem.get('destination:eta'))

            airport = (await core.nodes('transport:air:port=VISI [:name="Visi Airport" :place=*]'))[0]
            self.eq('visi', airport.ndef[1])
            self.eq('visi airport', airport.get('name'))
            self.nn(airport.get('place'))

            nodes = await core.nodes('''
                $regid = $lib.guid()

                [ transport:land:registration=$regid

                    :id=zeroday
                    :issued=20150202
                    :expires=20230202
                    :issuer={gen.ou.org "virginia dmv"}
                    :issuer:name="virginia dmv"

                    :contact={gen.ps.contact.email us.va.dmv visi@vertex.link}

                    :vehicle={[ transport:land:vehicle=*
                        :serial=V-31337
                        :built=2005
                        :make=lotus
                        :model=elise
                        :registration=$regid
                        :owner={gen.ps.contact.email us.va.dmv visi@vertex.link}
                    ]}

                    :license={[ transport:land:license=*
                        :id=V-31337
                        :contact={gen.ps.contact.email us.va.dmv visi@vertex.link}
                        :issued=20221217
                        :expires=20251217
                        :issuer={gen.ou.org "virginia dmv"}
                        :issuer:name="virginia dmv"
                    ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'zeroday')
            self.eq(nodes[0].get('issuer:name'), 'virginia dmv')
            self.eq(nodes[0].get('issued'), 1422835200000)
            self.eq(nodes[0].get('expires'), 1675296000000)

            self.nn(nodes[0].get('issuer'))
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('license'))
            self.nn(nodes[0].get('vehicle'))

            nodes = await core.nodes('transport:land:registration:id=zeroday :vehicle -> transport:land:vehicle')
            self.len(1, nodes)
            self.eq(nodes[0].get('make'), 'lotus')
            self.eq(nodes[0].get('model'), 'elise')
            self.eq(nodes[0].get('serial'), 'V-31337')
            self.eq(nodes[0].get('built'), 1104537600000)
            self.nn(nodes[0].get('owner'))
            self.nn(nodes[0].get('registration'))

            nodes = await core.nodes('transport:land:registration:id=zeroday -> transport:land:license')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'V-31337')
            self.eq(nodes[0].get('issued'), 1671235200000)
            self.eq(nodes[0].get('expires'), 1765929600000)
            self.eq(nodes[0].get('issuer:name'), 'virginia dmv')

            self.nn(nodes[0].get('issuer'))
            self.nn(nodes[0].get('contact'))
