modeldefs = (
    ('transport', {
        'types': (

            # TODO is transport:journey a thing?

            ('transport:cargo', ('guid', {}), {
                'doc': 'Cargo being carried by a vehicle on a trip.'}),

            ('transport:point', ('str', {'lower': True, 'onespace': True}), {
                'doc': 'A departure/arrival point such as an airport gate or train platform.'}),

            ('transport:trip', ('ndef', {'interface': 'transport:trip'}), {
                'doc': 'A trip such as a flight or train ride.'}),

            ('transport:stop', ('guid', {}), {
                'interfaces': (
                    ('transport:schedule', {}),
                ),
                'doc': 'A stop made by a vehicle on a trip.'}),

            ('transport:container', ('ndef', {'interface': 'transport:container'}), {
                'doc': 'A container capable of transporting cargo or personnel.'}),

            ('transport:vehicle', ('ndef', {'interface': 'transport:vehicle'}), {
                'doc': 'A vehicle such as an aircraft or sea vessel.'}),

            ('transport:occupant', ('guid', {}), {
                'doc': 'An occupant of a vehicle on a trip.'}),

            ('transport:occupant:role:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of transportation occupant roles.'}),

            ('transport:direction', ('hugenum', {'modulo': 360}), {
                'doc': 'A direction measured in degrees with 0.0 being true North.'}),

            ('transport:land:vehicle:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A type taxonomy for land vehicles.'}),

            ('transport:land:vehicle', ('guid', {}), {
                'interfaces': (
                    ('transport:vehicle', {
                        'template': {'phys:object': 'vehicle'}}),
                ),
                'doc': 'An individual land based vehicle.'}),

            ('transport:land:registration', ('guid', {}), {
                'doc': 'Registration issued to a contact for a land vehicle.'}),

            ('transport:land:license', ('guid', {}), {
                'doc': 'A license to operate a land vehicle issued to a contact.'}),

            ('transport:air:craft:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of aircraft types.'}),

            ('transport:land:drive', ('guid', {}), {
                'interfaces': (
                    ('transport:trip', {
                        'template': {
                            'trip': 'drive',
                            'gate': 'docking bay',
                            'place': 'place',
                            'vehicle': 'vehicle'}}),
                ),
                'doc': 'A drive taken by a land vehicle.'}),

            ('transport:air:craft', ('guid', {}), {
                'interfaces': (
                    ('transport:vehicle', {
                        'template': {'phys:object': 'aircraft'}}),
                ),
                'doc': 'An individual aircraft.'}),

            ('transport:air:tailnum:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of aircraft registration number types.'}),

            ('transport:air:tailnum', ('str', {'lower': True, 'strip': True, 'regex': '^[a-z0-9-]{2,}$'}), {
                'doc': 'An aircraft registration number or military aircraft serial number.',
                'ex': 'ff023'}),

            ('transport:air:flightnum', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^[a-z0-9]{3,6}$'}), {
                'doc': 'A commercial flight designator including airline and serial.',
                'ex': 'ua2437'}),

            ('transport:air:telem', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'locatable': 'telemetry sample'}}),
                ),
                'doc': 'A telemetry sample from an aircraft in transit.'}),

            ('transport:air:flight', ('guid', {}), {
                'interfaces': (
                    ('transport:trip', {
                        'template': {
                            'trip': 'flight',
                            'point': 'gate',
                            'place': 'airport',
                            'vehicle': 'aircraft'}}),
                ),
                'doc': 'An individual instance of a flight.'}),

            ('transport:air:port', ('str', {'lower': True}), {
                'doc': 'An IATA assigned airport code.'}),

            ('transport:sea:vessel:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of sea vessel types.'}),

            ('transport:sea:vessel', ('guid', {}), {
                'interfaces': (
                    ('transport:vehicle', {
                        'template': {'phys:object': 'vessel'}}),
                ),
                'doc': 'An individual sea vessel.'}),

            ('transport:sea:mmsi', ('str', {'regex': '[0-9]{9}'}), {
                'doc': 'A Maritime Mobile Service Identifier.'}),

            ('transport:sea:imo', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^imo[0-9]{7}$'}), {
                'doc': 'An International Maritime Organization registration number.'}),

            ('transport:sea:telem', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'locatable': 'telemetry sample'}}),
                ),
                'doc': 'A telemetry sample from a vessel in transit.'}),

            ('transport:rail:train', ('guid', {}), {
                'interfaces': (
                    ('transport:trip', {
                        'template': {
                            'point': 'gate',
                            'place': 'station',
                            'trip': 'train trip',
                            'vehicle': 'train'}}),
                ),
                'doc': 'An individual instance of a consist of train cars running a route.'}),

            ('transport:rail:car:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'ex': 'engine.diesel',
                'doc': 'A hierarchical taxonomy of rail car types.'}),

            ('transport:rail:car', ('guid', {}), {
                'interfaces': (
                    ('transport:container', {
                        'template': {'phys:object': 'train car'}}),
                ),
                'doc': 'An individual train car.'}),

            ('transport:rail:consist', ('guid', {}), {
                'interfaces': (
                    ('transport:vehicle', {
                        'template': {'phys:object': 'train'}}),
                ),
                'doc': 'A group of rail cars and locomotives connected together.'}),

            ('transport:shipping:container', ('guid', {}), {
                'interfaces': (
                    ('transport:container', {
                        'template': {'phys:object': 'shipping container'}}),
                ),
                'doc': 'An individual shipping container.'}),

        ),
        'interfaces': (

            ('transport:container', {
                'interfaces': (
                    ('phys:object', {}),
                ),
                'doc': 'Properties common to a container used to transport cargo or people.',
                'props': (

                    ('built', ('time', {}), {
                        'doc': 'The date when the {phys:object} was built.'}),

                    ('manufacturer', ('entity:actor', {}), {
                        'doc': 'The organization which manufactured the {phys:object}.'}),

                    ('manufacturer:name', ('meta:name', {}), {
                        'doc': 'The name of the organization which manufactured the {phys:object}.'}),

                    ('model', ('base:name', {}), {
                        'doc': 'The model of the {phys:object}.'}),

                    ('serial', ('base:id', {}), {
                        'doc': 'The manufacturer assigned serial number of the {phys:object}.'}),

                    ('max:occupants', ('int', {'min': 0}), {
                        'doc': 'The maximum number of occupants the {phys:object} can hold.'}),

                    ('max:cargo:mass', ('mass', {}), {
                        'doc': 'The maximum mass the {phys:object} can carry as cargo.'}),

                    ('max:cargo:volume', ('geo:dist', {}), {
                        'doc': 'The maximum volume the {phys:object} can carry as cargo.'}),

                    # FIXME ownership interface?
                    ('owner', ('entity:actor', {}), {
                        'doc': 'The contact information of the owner of the {phys:object}.'}),
                ),
            }),
            # most containers are vehicles, but some are not...
            ('transport:vehicle', {
                'interfaces': (
                    ('transport:container', {
                        'templates': {'phys:object': 'vehicle'}}),
                ),
                'doc': 'Properties common to a vehicle.',
                'props': (
                    ('operator', ('entity:actor', {}), {
                        'doc': 'The contact information of the operator of the {phys:object}.'}),
                ),
            }),

            ('transport:schedule', {
                'doc': 'Properties common to travel schedules.',
                'template': {
                    'place': 'place',       # airport, seaport, starport
                    'point': 'point',       # gate, slip, stargate...
                    'vehicle': 'vehicle',   # aircraft, vessel, space ship...
                    'trip': 'trip'},        # flight, voyage...

                'props': (

                    ('duration', ('duration', {}), {
                        'doc': 'The actual duration.'}),

                    ('departed', ('time', {}), {
                        'doc': 'The actual departure time.'}),

                    ('departed:place', ('geo:place', {}), {
                        'doc': 'The actual departure {place}.'}),

                    ('departed:point', ('transport:point', {}), {
                        'doc': 'The actual departure {point}.'}),

                    ('arrived', ('time', {}), {
                        'doc': 'The actual arrival time.'}),

                    ('arrived:place', ('geo:place', {}), {
                        'doc': 'The actual arrival {place}.'}),

                    ('arrived:point', ('transport:point', {}), {
                        'doc': 'The actual arrival {point}.'}),

                    ('scheduled:duration', ('duration', {}), {
                        'doc': 'The scheduled duration.'}),

                    ('scheduled:departure', ('time', {}), {
                        'doc': 'The scheduled departure time.'}),

                    ('scheduled:departure:place', ('geo:place', {}), {
                        'doc': 'The scheduled departure {place}.'}),

                    ('scheduled:departure:point', ('transport:point', {}), {
                        'doc': 'The scheduled departure {point}.'}),

                    ('scheduled:arrival', ('time', {}), {
                        'doc': 'The scheduled arrival time.'}),

                    ('scheduled:arrival:place', ('geo:place', {}), {
                        'doc': 'The scheduled arrival {place}.'}),

                    ('scheduled:arrival:point', ('transport:point', {}), {
                        'doc': 'The scheduled arrival {point}.'}),
                ),
            }),

            ('transport:trip', {
                # train, flight, drive, launch...
                'doc': 'Properties common to a specific trip taken by a vehicle.',
                'interfaces': (
                    ('transport:schedule', {}),
                ),
                'props': (

                    ('status', ('str', {'enums': 'scheduled,cancelled,in-progress,completed,aborted,failed,unknown'}), {
                        'doc': 'The status of the {trip}.'}),

                    ('occupants', ('int', {'min': 0}), {
                        'doc': 'The number of occupants of the {vehicle} on this {trip}.'}),

                    ('cargo:mass', ('mass', {}), {
                        'doc': 'The cargo mass carried by the {vehicle} on this {trip}.'}),

                    ('cargo:volume', ('geo:dist', {}), {
                        'doc': 'The cargo volume carried by the {vehicle} on this {trip}.'}),

                    ('operator', ('entity:actor', {}), {
                        'doc': 'The contact information of the operator of the {trip}.'}),

                    ('vehicle', ('transport:vehicle', {}), {
                        'doc': 'The {vehicle} which traveled the {trip}.'}),
                ),
            }),
        ),
        'edges': (
        ),
        'forms': (

            ('transport:stop', {}, (

                ('trip', ('transport:trip', {}), {
                    'doc': 'The trip which contains the stop.'}),
            )),

            ('transport:land:drive', {}, ()),

            ('transport:land:license', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The license ID.'}),

                # TODO type ( drivers license, commercial trucking, etc? )
                ('contact', ('entity:actor', {}), {
                    'doc': 'The contact info of the licensee.'}),

                ('issued', ('time', {}), {
                    'doc': 'The time the license was issued.'}),

                ('expires', ('time', {}), {
                    'doc': 'The time the license expires.'}),

                ('issuer', ('ou:org', {}), {
                    'doc': 'The org which issued the license.'}),

                ('issuer:name', ('meta:name', {}), {
                    'doc': 'The name of the org which issued the license.'}),
            )),
            ('transport:land:registration', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The vehicle registration ID or license plate.'}),

                ('contact', ('entity:actor', {}), {
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

                ('issuer:name', ('meta:name', {}), {
                    'doc': 'The name of the org which issued the registration.'}),
            )),

            ('transport:land:vehicle:type:taxonomy', {}, ()),

            ('transport:land:vehicle', {}, (

                ('type', ('transport:land:vehicle:type:taxonomy', {}), {
                    'doc': 'The type of land vehicle.'}),

                ('desc', ('str', {}), {
                    'doc': 'A description of the vehicle.'}),

                ('serial', ('str', {'strip': True}), {
                    'doc': 'The serial number or VIN of the vehicle.'}),

                ('registration', ('transport:land:registration', {}), {
                    'doc': 'The current vehicle registration information.'}),
            )),
            ('transport:air:craft:type:taxonomy', {}, ()),
            ('transport:air:craft', {}, (

                ('tailnum', ('transport:air:tailnum', {}), {
                    'doc': 'The aircraft tail number.'}),

                ('type', ('transport:air:craft:type:taxonomy', {}), {
                    'doc': 'The type of aircraft.'}),
            )),
            ('transport:air:port', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the airport.'}),

                ('place', ('geo:place', {}), {
                    'doc': 'The place where the IATA airport code is assigned.'}),
            )),
            ('transport:air:tailnum:type:taxonomy', {}, ()),
            ('transport:air:tailnum', {}, (

                ('loc', ('loc', {}), {
                    'doc': 'The geopolitical location that the tailnumber is allocated to.'}),

                ('type', ('transport:air:tailnum:type:taxonomy', {}), {
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

                ('tailnum', ('transport:air:tailnum', {}), {
                    'doc': 'The tail/registration number at the time the aircraft flew this flight.'}),
            )),
            ('transport:air:telem', {}, (

                ('flight', ('transport:air:flight', {}), {
                    'doc': 'The flight being measured.'}),

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

                ('time', ('time', {}), {
                    'doc': 'The time the telemetry sample was taken.'})
            )),
            # TODO ais numbers
            ('transport:sea:vessel:type:taxonomy', {}, ()),
            ('transport:sea:vessel', {}, (

                ('imo', ('transport:sea:imo', {}), {
                    'doc': 'The International Maritime Organization number for the vessel.'}),

                ('type', ('transport:sea:vessel:type:taxonomy', {}), {
                    'doc': 'The type of vessel.'}),

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the vessel.'}),

                ('flag', ('iso:3166:alpha2', {}), {
                    'doc': 'The country the vessel is flagged to.'}),

                ('mmsi', ('transport:sea:mmsi', {}), {
                    'doc': 'The Maritime Mobile Service Identifier assigned to the vessel.'}),

                ('operator', ('entity:actor', {}), {
                    'doc': 'The contact information of the operator.'}),
                # TODO tonnage / gross tonnage?
            )),

            ('transport:sea:telem', {}, (

                ('vessel', ('transport:sea:vessel', {}), {
                    'doc': 'The vessel being measured.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the telemetry was sampled.'}),

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

                ('destination:name', ('meta:name', {}), {
                    'doc': 'The name of the destination that the vessel has declared.'}),

                ('destination:eta', ('time', {}), {
                    'doc': 'The estimated time of arrival that the vessel has declared.'}),
            )),

            ('transport:rail:consist', {}, (

                ('cars', ('array', {'type': 'transport:rail:car', 'uniq': True}), {
                    'doc': 'The rail cars, including locomotives, which compose the consist.'}),
            )),

            ('transport:rail:train', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'The ID assigned to the train.'}),
            )),

            ('transport:rail:car:type:taxonomy', {}, ()),
            ('transport:rail:car', {}, (
                ('type', ('transport:rail:car:type:taxonomy', {}), {
                    'doc': 'The type of rail car.'}),
            )),

            ('transport:occupant:role:taxonomy', {}, ()),
            ('transport:occupant', {}, (

                ('role', ('transport:occupant:role:taxonomy', {}), {
                    'doc': 'The role of the occupant such as captain, crew, passenger.'}),

                ('contact', ('entity:individual', {}), {
                    'doc': 'Contact information of the occupant.'}),

                ('trip', ('transport:trip', {}), {
                    'doc': 'The trip, such as a flight or train ride, being taken by the occupant.'}),

                ('vehicle', ('transport:vehicle', {}), {
                    'doc': 'The vehicle that transported the occupant.'}),

                ('seat', ('str', {'strip': True}), {
                    'doc': 'The seat which the occupant sat in. Likely in a vehicle specific format.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('boarded', 'disembarked'),
                    'doc': 'The period when the occupant was aboard the vehicle.'}),

                ('boarded:place', ('geo:place', {}), {
                    'doc': 'The place where the occupant boarded the vehicle.'}),

                ('boarded:point', ('transport:point', {}), {
                    'doc': 'The boarding point such as an airport gate or train platform.'}),

                ('disembarked:place', ('geo:place', {}), {
                    'doc': 'The place where the occupant disembarked the vehicle.'}),

                ('disembarked:point', ('transport:point', {}), {
                    'doc': 'The disembarkation point such as an airport gate or train platform.'}),
            )),

            ('transport:cargo', {}, (

                ('object', ('phys:object', {}), {
                    'doc': 'The physical object being transported.'}),

                ('trip', ('transport:trip', {}), {
                    'doc': 'The trip being taken by the cargo.'}),

                ('vehicle', ('transport:vehicle', {}), {
                    'doc': 'The vehicle used to transport the cargo.'}),

                ('container', ('transport:container', {}), {
                    'doc': 'The container in which the cargo was shipped.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('loaded', 'unloaded'),
                    'doc': 'The period when the cargo was loaded in the vehicle.'}),

                ('loaded:place', ('geo:place', {}), {
                    'doc': 'The place where the cargo was loaded.'}),

                ('loaded:point', ('transport:point', {}), {
                    'doc': 'The point where the cargo was loaded such as an airport gate or train platform.'}),

                ('unloaded:place', ('geo:place', {}), {
                    'doc': 'The place where the cargo was unloaded.'}),

                ('unloaded:point', ('transport:point', {}), {
                    'doc': 'The point where the cargo was unloaded such as an airport gate or train platform.'}),
            )),

            ('transport:shipping:container', {}, ()),
        ),
    }),
)
