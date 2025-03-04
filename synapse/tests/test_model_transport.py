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
                    :type=cargo.tanker.oil
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
            self.eq('cargo.tanker.oil.', vessel.get('type'))
            self.eq('the vertex project', vessel.get('make'))
            self.eq('speed boat 9000', vessel.get('model'))
            self.eq('us', vessel.get('flag'))
            self.eq('imo1234567', vessel.get('imo'))
            self.eq(1577836800000, vessel.get('built'))
            self.eq(20000, vessel.get('length'))
            self.eq(10000, vessel.get('beam'))
            self.nn(vessel.get('operator'))

            self.len(1, await core.nodes('transport:sea:vessel:imo^="IMO 123"'))
            self.len(1, await core.nodes('transport:sea:vessel :name -> entity:name'))
            self.len(1, await core.nodes('transport:sea:vessel -> transport:sea:vessel:type:taxonomy'))

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
                        :type=car
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
            self.eq(nodes[0].get('type'), 'car.')
            self.eq(nodes[0].get('make'), 'lotus')
            self.eq(nodes[0].get('model'), 'elise')
            self.eq(nodes[0].get('serial'), 'V-31337')
            self.eq(nodes[0].get('built'), 1104537600000)
            self.nn(nodes[0].get('owner'))
            self.nn(nodes[0].get('registration'))
            self.len(1, await core.nodes('transport:land:vehicle -> transport:land:vehicle:type:taxonomy'))

            nodes = await core.nodes('transport:land:registration:id=zeroday -> transport:land:license')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'V-31337')
            self.eq(nodes[0].get('issued'), 1671235200000)
            self.eq(nodes[0].get('expires'), 1765929600000)
            self.eq(nodes[0].get('issuer:name'), 'virginia dmv')

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
                                :owner={[ ps:contact=* :name="road runner" ]}
                            ]}
                    ]}
                    :operator={[ ps:contact=* :name="visi" ]}
            ]''')

            self.eq(10800000, nodes[0].get('duration'))
            self.eq(10800000, nodes[0].get('scheduled:duration'))

            self.eq(1737109800000, nodes[0].get('departed'))
            self.eq('2c', nodes[0].get('departed:point'))
            self.nn(nodes[0].get('departed:place'))

            self.eq(1737109800000, nodes[0].get('scheduled:departure'))
            self.eq('2c', nodes[0].get('scheduled:departure:point'))
            self.nn(nodes[0].get('scheduled:departure:place'))

            self.eq(1737120600000, nodes[0].get('arrived'))
            self.nn(nodes[0].get('arrived:place'))
            self.eq('2c', nodes[0].get('arrived:point'))

            self.eq(1737120600000, nodes[0].get('scheduled:arrival'))
            self.nn(nodes[0].get('scheduled:arrival:place'))
            self.eq('2c', nodes[0].get('scheduled:arrival:point'))

            nodes = await core.nodes('transport:rail:consist')
            self.eq(2, nodes[0].get('max:occupants'))
            self.len(1, nodes[0].get('cars'))

            nodes = await core.nodes('transport:rail:car')
            self.eq('001', nodes[0].get('serial'))
            self.eq('engine.diesel.', nodes[0].get('type'))
            self.eq(1670803200000, nodes[0].get('built'))
            self.eq('acme', nodes[0].get('manufacturer:name'))
            self.eq('engine that could', nodes[0].get('model'))
            self.eq(2, nodes[0].get('max:occupants'))
            self.eq('1000000', nodes[0].get('max:cargo:mass'))
            self.eq(1000000, nodes[0].get('max:cargo:volume'))
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
                    :contact={[ ps:contact=({"name": "visi"}) ]}
                    :trip={ transport:rail:train }
                    :vehicle={ transport:rail:consist }
                    :seat=2c
                    :boarded=202501171020
                    :boarded:point=2c
                    :boarded:place={ geo:place:name="grand central station" }

                    :disembarked=202501171335
                    :disembarked:point=2c
                    :disembarked:place={ geo:place:name="union station" }
            ]''')
            self.nn(nodes[0].get('contact'))
            self.eq('2c', nodes[0].get('seat'))
            self.eq('passenger.', nodes[0].get('role'))
            self.eq('transport:rail:train', nodes[0].get('trip')[0])
            self.eq('transport:rail:consist', nodes[0].get('vehicle')[0])

            self.eq(1737109200000, nodes[0].get('boarded'))
            self.nn(nodes[0].get('boarded:place'))
            self.eq('2c', nodes[0].get('boarded:point'))

            self.eq(1737120900000, nodes[0].get('disembarked'))
            self.nn(nodes[0].get('disembarked:place'))
            self.eq('2c', nodes[0].get('disembarked:point'))
            self.len(1, await core.nodes('transport:occupant -> transport:occupant:role:taxonomy'))

            nodes = await core.nodes('''[
                transport:cargo=*

                    :trip={ transport:rail:train }
                    :vehicle={ transport:rail:consist }

                    :container={ transport:rail:car }
                    :object={[ transport:shipping:container=({"serial": "007"}) ]}

                    :loaded=202501171020
                    :loaded:point=2c
                    :loaded:place={ geo:place:name="grand central station" }

                    :unloaded=202501171335
                    :unloaded:point=2c
                    :unloaded:place={ geo:place:name="union station" }
            ]''')

            self.eq('transport:rail:train', nodes[0].get('trip')[0])
            self.eq('transport:rail:car', nodes[0].get('container')[0])
            self.eq('transport:rail:consist', nodes[0].get('vehicle')[0])
            self.eq('transport:shipping:container', nodes[0].get('object')[0])

            self.eq(1737109200000, nodes[0].get('loaded'))
            self.nn(nodes[0].get('loaded:place'))
            self.eq('2c', nodes[0].get('loaded:point'))

            self.eq(1737120900000, nodes[0].get('unloaded'))
            self.nn(nodes[0].get('unloaded:place'))
            self.eq('2c', nodes[0].get('unloaded:point'))
