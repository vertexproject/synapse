import synapse.tests.utils as s_test

class TransportTest(s_test.SynTest):

    async def test_model_transport(self):

        async with self.getTestCore() as core:

            craft = (await core.nodes('''[
                transport:air:craft=*
                    :tailnum=FF023
                    :type=helicopter
                    :built=202002
                    :model=747
                    :serial=1234
                    :operator={[ entity:contact=* ]}
            ]'''))[0]
            self.propeq(craft, 'type', 'helicopter.')
            self.propeq(craft, 'built', 1580515200000000)
            self.propeq(craft, 'model', '747')
            self.propeq(craft, 'serial', '1234')
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
                ]'''))[0]

            self.propeq(flight, 'num', 'ua2437')
            self.propeq(flight, 'scheduled:departure', 1580601600000000)
            self.propeq(flight, 'scheduled:arrival', 1580688000000000)
            self.propeq(flight, 'departed', 1580608800000000)
            self.propeq(flight, 'arrived', 1580612520000000)

            telem = (await core.nodes('''
                [ transport:air:telem=*
                    :flight=*
                    :place:latlong=(20.22, 80.1111)
                    :place:latlong:accuracy=10m
                    :place:loc=us
                    :place=*
                    :course=-280.9
                    :heading=99.02
                    :speed=374km/h
                    :airspeed=24ft/sec
                    :verticalspeed=-20feet/sec
                    :place:altitude=9144m
                    :place:altitude:accuracy=10m
                    :time=20200202
                ]'''))[0]
            self.nn(telem.get('flight'))
            self.nn(telem.get('place'))
            self.eq((20.22, 80.1111), telem.get('place:latlong'))
            self.propeq(telem, 'place:loc', 'us')
            self.propeq(telem, 'place:latlong:accuracy', 10000)
            self.propeq(telem, 'speed', 103888)
            self.propeq(telem, 'airspeed', 7315)
            self.propeq(telem, 'verticalspeed', -6096)
            self.propeq(telem, 'place:altitude', 6380152800)
            self.propeq(telem, 'place:altitude:accuracy', 10000)
            self.propeq(telem, 'time', 1580601600000000)
            self.propeq(telem, 'course', '79.1')
            self.propeq(telem, 'heading', '99.02')

            vessel = (await core.nodes('''[
                transport:sea:vessel=*
                    :mmsi=123456789
                    :callsign=V123
                    :name="Slice of Life"
                    :flag=us
                    :type=cargo.tanker.oil
                    :imo="IMO 1234567"
                    :built=2020
                    :model="Speed Boat 9000"
                    :operator={[ entity:contact=* ]}
                ]'''))[0]
            self.propeq(vessel, 'mmsi', '123456789')
            self.propeq(vessel, 'name', 'slice of life')
            self.propeq(vessel, 'callsign', 'V123')
            self.propeq(vessel, 'type', 'cargo.tanker.oil.')
            self.propeq(vessel, 'model', 'speed boat 9000')
            self.propeq(vessel, 'flag', 'us')
            self.propeq(vessel, 'imo', 'imo1234567')
            self.propeq(vessel, 'built', 1577836800000000)
            self.nn(vessel.get('operator'))

            self.len(1, await core.nodes('transport:sea:vessel:imo^="IMO 123"'))
            self.len(1, await core.nodes('transport:sea:vessel :name -> meta:name'))
            self.len(1, await core.nodes('transport:sea:vessel -> transport:sea:vessel:type:taxonomy'))

            seatelem = (await core.nodes('''[
                 transport:sea:telem=*
                    :time=20200202
                    :vessel=*
                    :place:loc=us
                    :place:latlong=(20.22, 80.1111)
                    :place:latlong:accuracy=10m
                    :place=*
                    :course=-280.9
                    :heading=99.02
                    :speed=c
                    :draft=20m
                    :airdraft=30m
                    :destination=*
                    :destination:name=woot
                    :destination:eta=20200203
            ]'''))[0]

            self.nn(seatelem.get('place'))
            self.eq((20.22, 80.1111), seatelem.get('place:latlong'))
            self.propeq(seatelem, 'place:loc', 'us')
            self.propeq(seatelem, 'place:latlong:accuracy', 10000)
            self.propeq(seatelem, 'time', 1580601600000000)
            self.propeq(seatelem, 'draft', 20000)
            self.propeq(seatelem, 'airdraft', 30000)
            self.propeq(seatelem, 'speed', 299792458000)
            self.propeq(seatelem, 'course', '79.1')
            self.propeq(seatelem, 'heading', '99.02')

            self.nn(seatelem.get('destination'))
            self.propeq(seatelem, 'destination:name', 'woot')
            self.propeq(seatelem, 'destination:eta', 1580688000000000)

            airport = (await core.nodes('transport:air:port=VISI [:name="Visi Airport" :place=*]'))[0]
            self.eq('visi', airport.ndef[1])
            self.propeq(airport, 'name', 'visi airport')
            self.nn(airport.get('place'))

            nodes = await core.nodes('''
                $regid = $lib.guid()

                $contact = {[
                    entity:contact=({
                        "type": "us.va.dmv",
                        "email": "visi@vertex.link",
                    })
                ]}

                [ transport:land:registration=$regid

                    :id=zeroday
                    :issued=20150202
                    :expires=20230202
                    :issuer={gen.ou.org "virginia dmv"}
                    :issuer:name="virginia dmv"

                    :contact=$contact

                    :vehicle={[ transport:land:vehicle=*
                        :serial=V-31337
                        :built=2005
                        :model=elise
                        :registration=$regid
                        :type=car
                        :owner=$contact
                    ]}

                    :license={[ transport:land:license=*
                        :id=V-31337
                        :contact=$contact
                        :issued=20221217
                        :expires=20251217
                        :issuer={[ ou:org=({"name": "virginia dmv"}) ]}
                        :issuer:name="virginia dmv"
                    ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'zeroday')
            self.propeq(nodes[0], 'issuer:name', 'virginia dmv')
            self.propeq(nodes[0], 'issued', 1422835200000000)
            self.propeq(nodes[0], 'expires', 1675296000000000)

            self.nn(nodes[0].get('issuer'))
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('license'))
            self.nn(nodes[0].get('vehicle'))

            nodes = await core.nodes('transport:land:registration:id=zeroday :vehicle -> transport:land:vehicle')
            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'car.')
            self.propeq(nodes[0], 'model', 'elise')
            self.propeq(nodes[0], 'serial', 'V-31337')
            self.propeq(nodes[0], 'built', 1104537600000000)
            self.nn(nodes[0].get('owner'))
            self.nn(nodes[0].get('registration'))
            self.len(1, await core.nodes('transport:land:vehicle -> transport:land:vehicle:type:taxonomy'))

            nodes = await core.nodes('transport:land:registration:id=zeroday -> transport:land:license')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'V-31337')
            self.propeq(nodes[0], 'issued', 1671235200000000)
            self.propeq(nodes[0], 'expires', 1765929600000000)
            self.propeq(nodes[0], 'issuer:name', 'virginia dmv')

            self.nn(nodes[0].get('issuer'))
            self.nn(nodes[0].get('contact'))

            nodes = await core.nodes('''[
                transport:land:drive=*
                    :vehicle={transport:land:vehicle}
            ]''')

            self.eq('transport:land:vehicle', nodes[0].get('vehicle')[0])

    async def test_model_transport_rail(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                transport:rail:train=*

                    :status=completed
                    :occupants=1
                    :cargo:mass=10kg
                    :cargo:volume=10m

                    :duration=03:00:00
                    :scheduled:duration=03:00:00

                    :departed=202501171030
                    :departed:point=2C
                    :departed:place={[ geo:place=* :name="grand central station" ]}

                    :scheduled:departure=202501171030
                    :scheduled:departure:point=2C
                    :scheduled:departure:place={ geo:place:name="grand central station" }

                    :arrived=202501171330
                    :arrived:place={[ geo:place=* :name="union station" ]}
                    :arrived:point=2C

                    :scheduled:arrival=202501171330
                    :scheduled:arrival:place={ geo:place:name="union station" }
                    :scheduled:arrival:point=2C

                    :vehicle={[
                        transport:rail:consist=*
                            :max:occupants=2
                            :cars={[
                                transport:rail:car=*
                                :serial=001
                                :type=engine.diesel
                                :built=20221212
                                :manufacturer:name=acme
                                :manufacturer={[ ou:org=({"name": "acme"}) ]}
                                :model="Engine That Could"
                                :max:occupants=2
                                :max:cargo:mass=1000kg
                                :max:cargo:volume=1000m
                                :owner={[ entity:contact=* :name="road runner" ]}
                            ]}
                    ]}
                    :operator={[ entity:contact=* :name="visi" ]}
            ]''')

            self.propeq(nodes[0], 'duration', 10800000000)
            self.propeq(nodes[0], 'scheduled:duration', 10800000000)

            self.propeq(nodes[0], 'departed', 1737109800000000)
            self.propeq(nodes[0], 'departed:point', '2c')
            self.nn(nodes[0].get('departed:place'))

            self.propeq(nodes[0], 'scheduled:departure', 1737109800000000)
            self.propeq(nodes[0], 'scheduled:departure:point', '2c')
            self.nn(nodes[0].get('scheduled:departure:place'))

            self.propeq(nodes[0], 'arrived', 1737120600000000)
            self.nn(nodes[0].get('arrived:place'))
            self.propeq(nodes[0], 'arrived:point', '2c')

            self.propeq(nodes[0], 'scheduled:arrival', 1737120600000000)
            self.nn(nodes[0].get('scheduled:arrival:place'))
            self.propeq(nodes[0], 'scheduled:arrival:point', '2c')

            nodes = await core.nodes('transport:rail:consist')
            self.propeq(nodes[0], 'max:occupants', 2)
            self.len(1, nodes[0].get('cars'))

            nodes = await core.nodes('transport:rail:car')
            self.propeq(nodes[0], 'serial', '001')
            self.propeq(nodes[0], 'type', 'engine.diesel.')
            self.propeq(nodes[0], 'built', 1670803200000000)
            self.propeq(nodes[0], 'manufacturer:name', 'acme')
            self.propeq(nodes[0], 'model', 'engine that could')
            self.propeq(nodes[0], 'max:occupants', 2)
            self.propeq(nodes[0], 'max:cargo:mass', '1000000')
            self.propeq(nodes[0], 'max:cargo:volume', 1000000)
            self.len(1, await core.nodes('transport:rail:car -> transport:rail:car:type:taxonomy'))

            self.nn(nodes[0].get('owner'))

            nodes = await core.nodes('''[
                transport:stop=*
                    :arrived:place={[ geo:place=* :name="BWI Rail Station" ]}
                    :trip={ transport:rail:train }
            ]''')
            self.nn(nodes[0].get('arrived:place'))
            self.eq('transport:rail:train', nodes[0].get('trip')[0])

            nodes = await core.nodes('''[
                transport:occupant=*
                    :role=passenger
                    :contact={[ entity:contact=({"name": "visi"}) ]}
                    :trip={ transport:rail:train }
                    :vehicle={ transport:rail:consist }
                    :seat=2c
                    :period=(202501171020, 202501171335)
                    :boarded:point=2c
                    :boarded:place={ geo:place:name="grand central station" }
                    :disembarked:point=2c
                    :disembarked:place={ geo:place:name="union station" }
            ]''')
            self.nn(nodes[0].get('contact'))
            self.propeq(nodes[0], 'seat', '2c')
            self.propeq(nodes[0], 'role', 'passenger.')
            self.eq('transport:rail:train', nodes[0].get('trip')[0])
            self.eq('transport:rail:consist', nodes[0].get('vehicle')[0])

            self.propeq(nodes[0], 'period', (1737109200000000, 1737120900000000, 11700000000))

            self.nn(nodes[0].get('boarded:place'))
            self.propeq(nodes[0], 'boarded:point', '2c')

            self.nn(nodes[0].get('disembarked:place'))
            self.propeq(nodes[0], 'disembarked:point', '2c')
            self.len(1, await core.nodes('transport:occupant -> transport:occupant:role:taxonomy'))

            nodes = await core.nodes('''[
                transport:cargo=*

                    :trip={ transport:rail:train }
                    :vehicle={ transport:rail:consist }

                    :container={ transport:rail:car }
                    :object={[ transport:shipping:container=({"serial": "007"}) ]}

                    :period=(202501171020, 202501171335)

                    :loaded:point=2c
                    :loaded:place={ geo:place:name="grand central station" }

                    :unloaded:point=2c
                    :unloaded:place={ geo:place:name="union station" }
            ]''')

            self.eq('transport:rail:train', nodes[0].get('trip')[0])
            self.eq('transport:rail:car', nodes[0].get('container')[0])
            self.eq('transport:rail:consist', nodes[0].get('vehicle')[0])
            self.eq('transport:shipping:container', nodes[0].get('object')[0])

            self.nn(nodes[0].get('loaded:place'))
            self.propeq(nodes[0], 'period', (1737109200000000, 1737120900000000, 11700000000))

            self.propeq(nodes[0], 'loaded:point', '2c')

            self.nn(nodes[0].get('unloaded:place'))
            self.propeq(nodes[0], 'unloaded:point', '2c')
