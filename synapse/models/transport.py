modeldefs = (
    {
        'types': (


            # TODO is transport:journey a thing?

            ('transport:cargo', ('guid', {}), {
                'props': (

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
                ),
                'doc': 'Cargo being carried by a vehicle on a trip.'}),

            ('transport:point', ('title', {}), {
                'doc': 'A departure/arrival point such as an airport gate or train platform.'}),

            ('transport:stop', ('guid', {}), {
                'template': {'title': 'stop'},
                'interfaces': (
                    ('transport:schedule', {}),
                ),
                'props': (

                    ('trip', ('transport:trip', {}), {
                        'doc': 'The trip which contains the stop.'}),
                ),
                'doc': 'A stop made by a vehicle on a trip.'}),

            ('transport:occupant', ('guid', {}), {
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('role', ('transport:occupant:role:taxonomy', {}), {
                        'doc': 'The role of the occupant such as captain, crew, passenger.'}),

                    ('contact', ('entity:individual', {}), {
                        'doc': 'Contact information of the occupant.'}),

                    ('trip', ('transport:trip', {}), {
                        'doc': 'The trip, such as a flight or train ride, being taken by the occupant.'}),

                    ('vehicle', ('transport:vehicle', {}), {
                        'doc': 'The vehicle that transported the occupant.'}),

                    ('seat', ('base:id', {}), {
                        'doc': 'The seat which the occupant sat in. Likely in a vehicle specific format.'}),

                    ('period', None, {
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
                ),
                'doc': 'An occupant of a vehicle on a trip.'}),

            ('transport:occupant:role:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of transportation occupant roles.'}),

            ('transport:direction', ('hugenum', {'modulo': 360}), {
                'doc': 'A direction measured in degrees with 0.0 being true North.'}),

            ('transport:land:vehicle:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A type taxonomy for land vehicles.'}),

            ('transport:land:vehicle', ('guid', {}), {
                'template': {'title': 'vehicle'},
                'interfaces': (
                    ('transport:vehicle', {}),
                ),
                'props': (

                    ('type', ('transport:land:vehicle:type:taxonomy', {}), {
                        'doc': 'The type of land vehicle.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the vehicle.'}),

                    ('serial', ('base:id', {}), {
                        'doc': 'The serial number or VIN of the vehicle.'}),

                    ('registration', ('transport:land:registration', {}), {
                        'doc': 'The current vehicle registration information.'}),
                ),
                'doc': 'An individual land based vehicle.'}),

            ('transport:land:registration', ('guid', {}), {
                'props': (

                    ('id', ('base:id', {}), {
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

                    ('issuer:name', ('entity:name', {}), {
                        'doc': 'The name of the org which issued the registration.'}),
                ),
                'doc': 'Registration issued to a contact for a land vehicle.'}),

            ('transport:land:license', ('guid', {}), {
                'props': (

                    ('id', ('base:id', {}), {
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

                    ('issuer:name', ('entity:name', {}), {
                        'doc': 'The name of the org which issued the license.'}),
                ),
                'doc': 'A license to operate a land vehicle issued to a contact.'}),

            ('transport:air:craft:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of aircraft types.'}),

            ('transport:land:drive', ('guid', {}), {
                'template': {
                    'title': 'drive',
                    'gate': 'docking bay',
                    'place': 'place',
                    'vehicle': 'vehicle'},
                'interfaces': (
                    ('transport:trip', {}),
                ),
                'props': (),
                'doc': 'A drive taken by a land vehicle.'}),

            ('transport:air:craft', ('guid', {}), {
                'template': {'title': 'aircraft'},
                'interfaces': (
                    ('transport:vehicle', {}),
                ),
                'props': (

                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The aircraft tail number.'}),

                    ('type', ('transport:air:craft:type:taxonomy', {}), {
                        'doc': 'The type of aircraft.'}),
                ),
                'doc': 'An individual aircraft.'}),

            ('transport:air:tailnum:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of aircraft registration number types.'}),

            ('transport:air:tailnum', ('str', {'lower': True, 'regex': '^[a-z0-9-]{2,}$'}), {
                'props': (

                    ('type', ('transport:air:tailnum:type:taxonomy', {}), {
                        'doc': 'A type which may be specific to the country prefix.'}),
                ),
                'doc': 'An aircraft registration number or military aircraft serial number.',
                'ex': 'ff023'}),

            ('transport:air:flightnum', ('str', {'lower': True, 'replace': ((' ', ''),), 'regex': '^[a-z0-9]{3,6}$'}), {
                'props': (

                    ('carrier', ('ou:org', {}), {
                        'doc': 'The org which operates the given flight number.'}),

                    ('to:port', ('transport:air:port', {}), {
                        'doc': 'The most recently registered destination for the flight number.'}),

                    ('from:port', ('transport:air:port', {}), {
                        'doc': 'The most recently registered origin for the flight number.'}),

                    ('stops', ('transport:air:port', {}), {
                        'array': {'uniq': False, 'sorted': False},
                        'doc': 'An ordered list of aiport codes for the flight segments.'}),
                ),
                'doc': 'A commercial flight designator including airline and serial.',
                'ex': 'ua2437'}),

            ('transport:air:telem', ('guid', {}), {
                'template': {'title': 'telemetry sample'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

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

                    ('verticalspeed', ('velocity:relative', {}), {
                        'doc': 'The relative vertical speed of the aircraft at the time.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the telemetry sample was taken.'})
                ),
                'doc': 'A telemetry sample from an aircraft in transit.'}),

            ('transport:air:flight', ('guid', {}), {
                'template': {
                    'title': 'flight',
                    'point': 'gate',
                    'place': 'airport',
                    'vehicle': 'aircraft'},
                'interfaces': (
                    ('transport:trip', {}),
                ),
                'props': (

                    ('num', ('transport:air:flightnum', {}), {
                        'doc': 'The flight number of this flight.'}),

                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The tail/registration number at the time the aircraft flew this flight.'}),
                ),
                'doc': 'An individual instance of a flight.'}),

            ('transport:air:port', ('str', {'lower': True}), {
                'props': (

                    ('name', ('geo:name', {}), {
                        'doc': 'The name of the airport.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the IATA airport code is assigned.'}),
                ),
                'doc': 'An IATA assigned airport code.'}),

            ('transport:sea:vessel:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of sea vessel types.'}),

            ('transport:sea:vessel', ('guid', {}), {
                'template': {'title': 'vessel'},
                'interfaces': (
                    ('transport:vehicle', {}),
                ),
                'props': (

                    ('imo', ('transport:sea:imo', {}), {
                        'doc': 'The International Maritime Organization number for the vessel.'}),

                    ('type', ('transport:sea:vessel:type:taxonomy', {}), {
                        'doc': 'The type of vessel.'}),

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the vessel.'}),

                    ('callsign', ('base:id', {}), {
                        'doc': 'The callsign of the vessel.'}),

                    ('mmsi', ('transport:sea:mmsi', {}), {
                        'doc': 'The Maritime Mobile Service Identifier assigned to the vessel.'}),

                    ('operator', ('entity:actor', {}), {
                        'doc': 'The contact information of the operator.'}),
                    # TODO tonnage / gross tonnage?
                ),
                'doc': 'An individual sea vessel.'}),

            ('transport:sea:mmsi', ('str', {'regex': '^[0-9]{9}$'}), {
                'doc': 'A Maritime Mobile Service Identifier.'}),

            ('transport:sea:imo', ('str', {'lower': True, 'replace': ((' ', ''),), 'regex': '^imo[0-9]{7}$'}), {
                'doc': 'An International Maritime Organization registration number.'}),

            ('transport:sea:telem', ('guid', {}), {
                'template': {'title': 'telemetry sample'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

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

                    ('draft', ('phys:distance', {}), {
                        'doc': 'The keel depth at the time.'}),

                    ('airdraft', ('phys:distance', {}), {
                        'doc': 'The maximum height of the ship from the waterline.'}),

                    ('destination', ('geo:place', {}), {
                        'doc': 'The fully resolved destination that the vessel has declared.'}),

                    ('destination:name', ('geo:name', {}), {
                        'doc': 'The name of the destination that the vessel has declared.'}),

                    ('destination:eta', ('time', {}), {
                        'doc': 'The estimated time of arrival that the vessel has declared.'}),
                ),
                'doc': 'A telemetry sample from a vessel in transit.'}),

            ('transport:rail:train', ('guid', {}), {
                'template': {
                    'point': 'gate',
                    'place': 'station',
                    'title': 'train trip',
                    'vehicle': 'train'},
                'interfaces': (
                    ('transport:trip', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'The ID assigned to the train.'}),
                ),
                'doc': 'An individual instance of a consist of train cars running a route.'}),

            ('transport:rail:car:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'ex': 'engine.diesel',
                'doc': 'A hierarchical taxonomy of rail car types.'}),

            ('transport:rail:car', ('guid', {}), {
                'template': {'title': 'train car'},
                'interfaces': (
                    ('transport:container', {}),
                ),
                'props': (
                    ('type', ('transport:rail:car:type:taxonomy', {}), {
                        'doc': 'The type of rail car.'}),
                ),
                'doc': 'An individual train car.'}),

            ('transport:rail:consist', ('guid', {}), {
                'template': {'title': 'train'},
                'interfaces': (
                    ('transport:vehicle', {}),
                ),
                'props': (

                    ('cars', ('transport:rail:car', {}), {
                        'array': {'sorted': False},
                        'doc': 'The rail cars, including locomotives, which compose the consist.'}),
                ),
                'doc': 'A group of rail cars and locomotives connected together.'}),

            ('transport:shipping:container', ('guid', {}), {
                'template': {'title': 'shipping container'},
                'interfaces': (
                    ('transport:container', {}),
                ),
                'props': (),
                'doc': 'An individual shipping container.'}),

        ),
        'interfaces': (

            ('transport:container', {
                'interfaces': (
                    ('phys:object', {}),
                    ('meta:havable', {}),
                    ('biz:manufactured', {}),
                    ('entity:creatable', {}),
                ),
                'doc': 'Properties common to a container used to transport cargo or people.',
                'props': (

                    ('model', ('biz:model', {}), {
                        'doc': 'The model of the {title}.'}),

                    ('serial', ('base:id', {}), {
                        'doc': 'The manufacturer assigned serial number of the {title}.'}),

                    ('max:occupants', ('size', {}), {
                        'doc': 'The maximum number of occupants the {title} can hold.'}),

                    ('max:cargo:mass', ('phys:mass', {}), {
                        'doc': 'The maximum mass the {title} can carry as cargo.'}),

                    ('max:cargo:volume', ('phys:volume', {}), {
                        'doc': 'The maximum volume the {title} can carry as cargo.'}),
                ),
            }),
            # most containers are vehicles, but some are not...
            ('transport:vehicle', {
                'interfaces': (
                    ('transport:container', {}),
                ),
                'doc': 'Properties common to a vehicle.',
                'props': (
                    ('operator', ('entity:actor', {}), {
                        'doc': 'The contact information of the operator of the {title}.'}),
                ),
            }),

            ('transport:schedule', {
                'doc': 'Properties common to travel schedules.',
                'template': {
                    'title': 'trip',        # flight, voyage...
                    'place': 'place',       # airport, seaport, starport
                    'point': 'point',       # gate, slip, stargate...
                    'vehicle': 'vehicle'},  # aircraft, vessel, space ship...

                'interfaces': (
                    ('meta:schedulable', {}),
                ),

                'props': (

                    ('departed:place', ('geo:place', {}), {
                        'doc': 'The actual departure {place}.'}),

                    ('departed:point', ('transport:point', {}), {
                        'doc': 'The actual departure {point}.'}),

                    ('arrived:place', ('geo:place', {}), {
                        'doc': 'The actual arrival {place}.'}),

                    ('arrived:point', ('transport:point', {}), {
                        'doc': 'The actual arrival {point}.'}),

                    ('scheduled:departure:place', ('geo:place', {}), {
                        'doc': 'The scheduled departure {place}.'}),

                    ('scheduled:departure:point', ('transport:point', {}), {
                        'doc': 'The scheduled departure {point}.'}),

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
                    ('meta:usable', {}),
                    ('transport:schedule', {}),
                ),
                'props': (

                    ('status', ('title', {}), {
                        'doc': 'The status of the {title}.'}),

                    ('occupants', ('size', {}), {
                        'doc': 'The number of occupants of the {vehicle} on this {title}.'}),

                    ('cargo:mass', ('phys:mass', {}), {
                        'doc': 'The cargo mass carried by the {vehicle} on this {title}.'}),

                    ('cargo:volume', ('phys:volume', {}), {
                        'doc': 'The cargo volume carried by the {vehicle} on this {title}.'}),

                    ('operator', ('entity:actor', {}), {
                        'doc': 'The contact information of the operator of the {title}.'}),

                    ('vehicle', ('transport:vehicle', {}), {
                        'doc': 'The {vehicle} which traveled the {title}.'}),
                ),
            }),
        ),
        'edges': (
        ),
    },
)
