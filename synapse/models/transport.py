import synapse.lib.module as s_module

class TransportModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (

                ('transport:direction', ('hugenum', {'modulo': 360}), {
                    'doc': 'A direction measured in degrees with 0.0 being true North.'}),

                ('transport:land:vehicle:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy', {}),
                    'doc': 'A type taxonomy for land vehicles.'}),

                ('transport:land:vehicle', ('guid', {}), {
                    'doc': 'An individual vehicle.'}),

                ('transport:land:registration', ('guid', {}), {
                    'doc': 'Registration issued to a contact for a land vehicle.'}),

                ('transport:land:license', ('guid', {}), {
                    'doc': 'A license to operate a land vehicle issued to a contact.'}),

                ('transport:air:craft', ('guid', {}), {
                    'doc': 'An individual aircraft.'}),

                ('transport:air:tailnum', ('str', {'lower': True, 'strip': True, 'regex': '^[a-z0-9-]{2,}$'}), {
                    'doc': 'An aircraft registration number or military aircraft serial number.',
                    'ex': 'ff023'}),

                ('transport:air:flightnum', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^[a-z0-9]{3,6}$'}), {
                    'doc': 'A commercial flight designator including airline and serial.',
                    'ex': 'ua2437'}),

                ('transport:air:telem', ('guid', {}), {
                    'doc': 'A telemetry sample from an aircraft in transit.'}),

                ('transport:air:flight', ('guid', {}), {
                    'doc': 'An individual instance of a flight.'}),

                ('transport:air:occupant', ('guid', {}), {
                    'doc': 'An occupant of a specific flight.'}),

                ('transport:air:port', ('str', {'lower': True}), {
                    'doc': 'An IATA assigned airport code.'}),

                ('transport:sea:vessel', ('guid', {}), {
                    'doc': 'An individual sea vessel.'}),

                ('transport:sea:mmsi', ('str', {'regex': '[0-9]{9}'}), {
                    'doc': 'A Maritime Mobile Service Identifier'}),

                ('transport:sea:imo', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^imo[0-9]{7}$'}), {
                    'doc': 'An International Maritime Organization registration number.'}),

                ('transport:sea:telem', ('guid', {}), {
                    'doc': 'A telemetry sample from a vessel in transit.'}),

                ('transport:rail:train', ('guid', {}), {
                    'interfaces': ('transport:conveyance',),
                    'templates': {'phys:item': 'train'},
                    'doc': 'An individual instance of a train running a route.'}),

                ('transport:rail:car', ('guid', {}), {
                    'interfaces': ('transport:container',),
                    'templates': {'phys:item': 'train car'},
                    'doc': 'An individual train car.'}),

                ('transport:rail:train:stop', ('guid', {}), {
                    'doc': 'An instance of a train stopping at a station.'}),

                ('transport:rail:route', ('guid', {}), {
                    'doc': 'A recurring route taken by trains from station to station.'}),

                ('transport:rail:station', ('guid', {}), {
                    'doc': 'A train station.'}),

                ('transport:shipping:container', ('guid', {}), {
                    'interfaces': ('transport:container',),
                    'templates': {'phys:item': 'shipping container'},
                    'doc': 'An individual shipping container.'}),

                # TODO a few more items to plumb eventually
                # ('transport:sea:hin',
                # ('transport:sea:port',
            ),
            'interfaces': (

                # ('transport:hub'
                ('transport:container', {
                    'interfaces': ('mat:physical',),
                    'doc': 'Properties common to a container used to transport cargo or people.',
                    'props': (
                        ('manufacturer', ('ou:org', {}), {
                            'doc': 'The organization which manufactured the {phys:item}.'}),

                        ('manufacturer:name', ('ou:name', {}), {
                            'doc': 'The name of the organization which manufactured the {phys:item}.'}),

                        ('model', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The model of the {phys:item}.'}),

                        ('serial', ('str', {'strip': True}), {
                            'doc': 'The manufacturer assigned serial number of the {phys:item}.'}),

                        ('occupants', ('int', {'min': 0}), {
                            'doc': 'The maximum number of occupants the {phys:item} can hold.'}),

                        ('cargo:mass', ('mass', {}), {
                            'doc': 'The maximum mass the {phys:item} can carry as cargo.'}),

                        ('cargo:volume', ('geo:dist', {}), {
                            'doc': 'The maxiumum volume the {phys:item} can carry as cargo.'}),

                        # TODO ownership interface
                        ('owner', ('ps:contact', {}), {
                            'doc': 'The contact information of the owner of the {phys:item}.'}),
                    ),
                }),
                ('transport:conveyance', {
                    # train, flight, launch...
                    'doc': 'Properties common to conveyances.',
                    'interfaces': ('transport:container',),
                    'template': {'phys:item': 'vehicle'},
                    'props': (
                        ('operator', ('ps:contact', {}), {
                            'doc': 'The contact information of the operator.'}),
                    ),
                }),
            ),
            'forms': (
                ('transport:land:license', {}, (
                    ('id', ('str', {'strip': True}), {
                        'doc': 'The license ID.'}),
                    # TODO type ( drivers license, commercial trucking, etc? )
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact info of the registrant.'}),
                    ('issued', ('time', {}), {
                        'doc': 'The time the license was issued.'}),
                    ('expires', ('time', {}), {
                        'doc': 'The time the license expires.'}),
                    ('issuer', ('ou:org', {}), {
                        'doc': 'The org which issued the license.'}),
                    ('issuer:name', ('ou:name', {}), {
                        'doc': 'The name of the org which issued the license.'}),
                )),
                ('transport:land:registration', {}, (
                    ('id', ('str', {'strip': True}), {
                        'doc': 'The vehicle registration ID or license plate.'}),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact info of the registrant.'}),
                    ('license', ('transport:land:license', {}), {
                        'doc': 'The license used to register the vehicle.'}),
                    ('issued', ('time', {}), {
                        'doc': 'The time the vehicle registration was issued.'}),
                    ('expires', ('time', {}), {
                        'doc': 'The time the vehicle registration expires.'}),
                    ('vehicle', ('transport:land:vehicle', {}), {
                        'doc': 'The vehicle being registered.'}),
                    ('issuer', ('ou:org', {}), {
                        'doc': 'The org which issued the registration.'}),
                    ('issuer:name', ('ou:name', {}), {
                        'doc': 'The name of the org which issued the registration.'}),
                )),

                ('transport:land:vehicle:type:taxonomy', {}, ()),

                ('transport:land:vehicle', {}, (

                    ('type', ('transport:land:vehicle:type:taxonomy', {}), {
                        'doc': 'A type taxonomy for land vehicles.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A description of the vehicle.'}),

                    ('serial', ('str', {'strip': True}), {
                        'doc': 'The serial number or VIN of the vehicle.'}),

                    ('built', ('time', {}), {
                        'doc': 'The date the vehicle was constructed.'}),

                    ('make', ('ou:name', {}), {
                        'doc': 'The make of the vehicle.'}),

                    ('model', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The model of the vehicle.'}),

                    ('registration', ('transport:land:registration', {}), {
                        'doc': 'The current vehicle registration information.'}),

                    ('owner', ('ps:contact', {}), {
                        'doc': 'The contact info of the owner of the vehicle.'}),
                )),
                ('transport:air:craft', {}, (
                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The aircraft tail number.'}),
                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The type of aircraft.'}),
                    ('built', ('time', {}), {
                        'doc': 'The date the aircraft was constructed.'}),
                    ('make', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The make of the aircraft.'}),
                    ('model', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The model of the aircraft.'}),
                    ('serial', ('str', {'strip': True}), {
                        'doc': 'The serial number of the aircraft.'}),
                    ('operator', ('ps:contact', {}), {
                        'doc': 'Contact info representing the person or org that operates the aircraft.'}),
                )),
                ('transport:air:port', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the airport'}),
                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the IATA airport code is assigned.'}),
                )),
                ('transport:air:tailnum', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'The geopolitical location that the tailnumber is allocated to.'}),
                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A type which may be specific to the country prefix.'}),
                )),
                ('transport:air:flightnum', {}, (
                    ('carrier', ('ou:org', {}), {
                        'doc': 'The org which operates the given flight number.'}),
                    ('to:port', ('transport:air:port', {}), {
                        'doc': 'The most recently registered destination for the flight number.'}),
                    ('from:port', ('transport:air:port', {}), {
                        'doc': 'The most recently registered origin for the flight number.'}),
                    ('stops', ('array', {'type': 'transport:air:port'}), {
                        'doc': 'An ordered list of aiport codes for the flight segments.'}),
                )),
                ('transport:air:flight', {}, (
                    ('num', ('transport:air:flightnum', {}), {
                        'doc': 'The flight number of this flight.'}),
                    ('scheduled:departure', ('time', {}), {
                        'doc': 'The time this flight was originally scheduled to depart'}),
                    ('scheduled:arrival', ('time', {}), {
                        'doc': 'The time this flight was originally scheduled to arrive'}),
                    ('departed', ('time', {}), {
                        'doc': 'The time this flight departed'}),
                    ('arrived', ('time', {}), {
                        'doc': 'The time this flight arrived'}),
                    ('carrier', ('ou:org', {}), {
                        'doc': 'The org which operates the given flight number.'}),
                    ('craft', ('transport:air:craft', {}), {
                        'doc': 'The aircraft that flew this flight.'}),
                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The tail/registration number at the time the aircraft flew this flight.'}),
                    ('to:port', ('transport:air:port', {}), {
                        'doc': 'The destination airport of this flight.'}),
                    ('from:port', ('transport:air:port', {}), {
                        'doc': 'The origin airport of this flight.'}),
                    ('stops', ('array', {'type': 'transport:air:port'}), {
                        'doc': 'An ordered list of airport codes for stops which occurred during this flight.'}),
                    ('cancelled', ('bool', {}), {
                        'doc': 'Set to true for cancelled flights.'}),
                )),
                ('transport:air:telem', {}, (
                    ('flight', ('transport:air:flight', {}), {
                        'doc': 'The flight being measured.'}),
                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The lat/lon of the aircraft at the time.'}),
                    ('loc', ('loc', {}), {
                        'doc': 'The location of the aircraft at the time.'}),
                    ('place', ('geo:place', {}), {
                        'doc': 'The place that the lat/lon geocodes to.'}),
                    ('accuracy', ('geo:dist', {}), {
                        'doc': 'The horizontal accuracy of the latlong sample.'}),
                    ('course', ('transport:direction', {}), {
                        'doc': 'The direction, in degrees from true North, that the aircraft is traveling.'}),
                    ('heading', ('transport:direction', {}), {
                        'doc': 'The direction, in degrees from true North, that the nose of the aircraft is pointed.'}),
                    ('speed', ('velocity', {}), {
                        'doc': 'The ground speed of the aircraft at the time.'}),
                    ('airspeed', ('velocity', {}), {
                        'doc': 'The air speed of the aircraft at the time.'}),
                    ('verticalspeed', ('velocity', {'relative': True}), {
                        'doc': 'The relative vertical speed of the aircraft at the time.'}),
                    ('altitude', ('geo:altitude', {}), {
                        'doc': 'The altitude of the aircraft at the time.'}),
                    ('altitude:accuracy', ('geo:dist', {}), {
                        'doc': 'The vertical accuracy of the altitude measurement.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the telemetry sample was taken.'})
                )),
                ('transport:air:occupant', {}, (
                    ('type', ('str', {'lower': True}), {
                        'doc': 'The type of occupant such as pilot, crew or passenger.'}),
                    ('flight', ('transport:air:flight', {}), {
                        'doc': 'The flight that the occupant was aboard.'}),
                    ('seat', ('str', {'lower': True}), {
                        'doc': 'The seat assigned to the occupant'}),
                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact information of the occupant.'}),
                )),
                # TODO ais numbers
                ('transport:sea:vessel', {}, (
                    ('imo', ('transport:sea:imo', {}), {
                        'doc': 'The International Maritime Organization number for the vessel.'}),
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the vessel'}),
                    ('length', ('geo:dist', {}), {
                        'doc': 'The official overall vessel length'}),
                    ('beam', ('geo:dist', {}), {
                        'doc': 'The official overall vessel beam'}),
                    ('flag', ('iso:3166:cc', {}), {
                        'doc': 'The country the vessel is flagged to.'}),
                    ('mmsi', ('transport:sea:mmsi', {}), {
                        'doc': 'The Maritime Mobile Service Identifier assigned to the vessel.'}),
                    ('built', ('time', {}), {
                        'doc': 'The year the vessel was constructed.'}),
                    ('make', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The make of the vessel.'}),
                    ('model', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The model of the vessel.'}),
                    ('operator', ('ps:contact', {}), {
                        'doc': 'The contact information of the operator.'}),
                    # TODO tonnage / gross tonnage?
                )),
                ('transport:sea:telem', {}, (
                    ('vessel', ('transport:sea:vessel', {}), {
                        'doc': 'The vessel being measured.'}),
                    ('time', ('time', {}), {
                        'doc': 'The time the telemetry was sampled.'}),
                    ('latlong', ('geo:latlong', {}), {
                        'doc': 'The lat/lon of the vessel at the time.'}),
                    ('loc', ('loc', {}), {
                        'doc': 'The location of the vessel at the time.'}),
                    ('place', ('geo:place', {}), {
                        'doc': 'The place that the lat/lon geocodes to.'}),
                    ('accuracy', ('geo:dist', {}), {
                        'doc': 'The horizontal accuracy of the latlong sample.'}),
                    ('course', ('transport:direction', {}), {
                        'doc': 'The direction, in degrees from true North, that the vessel is traveling.'}),
                    ('heading', ('transport:direction', {}), {
                        'doc': 'The direction, in degrees from true North, that the bow of the vessel is pointed.'}),
                    ('speed', ('velocity', {}), {
                        'doc': 'The speed of the vessel at the time.'}),
                    ('draft', ('geo:dist', {}), {
                        'doc': 'The keel depth at the time.'}),
                    ('airdraft', ('geo:dist', {}), {
                        'doc': 'The maximum height of the ship from the waterline.'}),
                    ('destination', ('geo:place', {}), {
                        'doc': 'The fully resolved destination that the vessel has declared.'}),
                    ('destination:name', ('geo:name', {}), {
                        'doc': 'The name of the destination that the vessel has declared.'}),
                    ('destination:eta', ('time', {}), {
                        'doc': 'The estimated time of arrival that the vessel has declared.'}),
                )),

                ('transport:rail:train', {}, (

                    ('id', ('str', {'strip': True}), {
                        'doc': 'The ID assigned to the train.'}),

                    ('route', ('transport:rail:route', {}), {
                        'doc': 'The route the train travels along.'}),

                    ('stops', ('array', {'type': 'transport:rail:train:stop'}), {
                        'doc': 'The stops the train made along the route.'}),

                    ('cars', ('array', {'type': 'transport:rail:car', 'uniq': True}), {
                        'doc': 'The cars which are attached to form the train.'}),

                    ('operator', ('ps:contact', {}), {
                        'doc': 'The organization which operates the train.'}),

                    ('operator:name', ('ou:name', {}), {
                        'doc': 'The name of the organization which operates the train.'}),
                )),

                ('transport:rail:car', {}, ()),

                ('transport:rail:occupant', {}, (

                    ('contact', ('ps:contact', {}), {
                        'doc': 'Contact information of the occupant.'}),

                    ('train', ('transport:rail:train', {}), {
                        'doc': 'The train the occupant boarded.'}),

                    ('car', ('int', {'min': 1}), {
                        'doc': 'The car number containing the occupants seat.'}),

                    ('seat', ('str', {'strip': True}), {
                        'doc': 'The seat which the occupant sat in.'}),

                    ('boarded', ('time', {}), {
                        'doc': 'The time when the occupant boarded the train.'}),

                    ('boarded:stop', ('transport:rail:train:stop', {}), {
                        'doc': 'The stop where the occupant boarded the train.'}),

                    ('disembarked', ('time', {}), {
                        'doc': 'The time when the occupant detrained.'}),

                    ('disembarked:stop', ('transport:rail:train:stop', {}), {
                        'doc': 'The stop where the occupant detrained.'}),
                )),

                ('transport:travel:path', {}, (
                )),

                ('transport:travel:path:link', {}, (

                    ('arrived', ('time', {}), {
                        'doc': 'The time the vehicle arrived at the stop.'}),

                    ('departed', ('time', {}), {
                        'doc': 'The time the vehicle departed from the stop.'}),

                    ('arrival:time', ('time', {}), {
                        'doc': 'The time the vehicle was scheduled to arrive.'}),

                    ('arrival:point', ('str', {'strip': True}), {
                        'doc': 'The gate, platform, or dock where the vehicle arrived.'}),

                    ('arrival:place', ('geo:place', {}), {
                        'doc': 'The place that the vehicle arrives at.'}),

                    ('departure:time', ('time', {}), {
                        'doc': 'The time the vehicle was scheduled to depart.'}),

                    ('departure:point', ('str', {'strip': True}), {
                        'doc': 'The gate, platform, or dock that the vehicle departed from.'}),

                    ('departure:place', ('geo:place', {}), {
                        'doc': 'The place that the vehicle departs from.'}),
                )),

                ('transport:rail:route', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the train route.'}),

                    ('stations', ('array', {'type': 'transport:rail:station'}), {
                        'doc': 'The stations along the route.'}),
                )),

                ('transport:rail:station', {}, (

                    ('id', ('str', {'strip': True}), {
                        'doc': 'The assigned ID of the rail station.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The geographic place of the station.'}),

                    ('place:name', ('geo:name', {}), {
                        'doc': 'The name of the rail station.'}),
                )),

                # ('transport:shipping:parcel',
                ('transport:shipping:container', {}, ()),
            ),
        }
        return (('transport', modl), )
