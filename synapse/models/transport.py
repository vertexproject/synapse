import synapse.lib.module as s_module

class TransportModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (

                ('transport:journey', ('guid', {}), {
                    'doc': 'A journey taken to ship cargo or personel.'}),

                ('transport:segement', ('ndef', {'interface': 'transport:segment'}), {
                    'doc': 'A segment of a journey such as a flight or train ride.'}),

                ('transport:vehicle', ('ndef', {'interface': 'transport:vehicle'}), {
                    'doc': 'A vehicle such as an air craft or sea vessel.'}),

                ('transport:direction', ('hugenum', {'modulo': 360}), {
                    'doc': 'A direction measured in degrees with 0.0 being true North.'}),

                ('transport:land:vehicle:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy', {}),
                    'doc': 'A type taxonomy for land vehicles.'}),

                ('transport:land:vehicle', ('guid', {}), {
                    'template': {'phys:object': 'vehicle'},
                    'interfaces': ('transport:container', {}),
                    'doc': 'An individual vehicle.'}),

                ('transport:land:registration', ('guid', {}), {
                    'doc': 'Registration issued to a contact for a land vehicle.'}),

                ('transport:land:license', ('guid', {}), {
                    'doc': 'A license to operate a land vehicle issued to a contact.'}),

                ('transport:land:segment', ('guid', {}), {
                    'interfaces': ('transport:segment',),
                    'template': {'phys:object': 'vehicle'},
                    'doc': 'A specific segment of a journey via a land vehicle.'}),

                ('transport:air:craft', ('guid', {}), {
                    'interfaces': ('transport:container',),
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
                    'interfaces': ('transport:segment',),
                    'template': {
                        'point': 'gate',
                        'place': 'airport',
                        'segment': 'flight',
                        'vehicle': 'air craft'},
                    'doc': 'An individual instance of a flight.'}),

                ('transport:air:occupant', ('guid', {}), {
                    'doc': 'An occupant of a specific flight.'}),

                ('transport:air:port', ('str', {'lower': True}), {
                    'doc': 'An IATA assigned airport code.'}),

                ('transport:sea:vessel', ('guid', {}), {
                    'interfaces': ('transport:vehicle',),
                    'doc': 'An individual sea vessel.'}),

                ('transport:sea:mmsi', ('str', {'regex': '[0-9]{9}'}), {
                    'doc': 'A Maritime Mobile Service Identifier'}),

                ('transport:sea:imo', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^imo[0-9]{7}$'}), {
                    'doc': 'An International Maritime Organization registration number.'}),

                ('transport:sea:telem', ('guid', {}), {
                    'doc': 'A telemetry sample from a vessel in transit.'}),

                ('transport:rail:segment', ('guid', {}), {
                    'interfaces': ('transport:segment',),
                    'template': {
                        'point': 'gate',
                        'place': 'station',
                        'vehicle': 'train'},
                    'doc': 'A segment of a route taken by a train.'}),

                ('transport:rail:train', ('guid', {}), {
                    'interfaces': ('transport:segment',),
                    'template': {
                        'point': 'gate',
                        'place': 'station',
                        'vehicle': 'train'},
                    'doc': 'An individual instance of a train running a route.'}),

                ('transport:rail:car', ('guid', {}), {
                    'interfaces': ('transport:container',),
                    'template': {'phys:object': 'train car'},
                    'doc': 'An individual train car.'}),

                ('transport:rail:consist', ('guid', {}), {
                    'interfaces': ('transport:vehicle',),
                    'template': {'vehicle': 'train'},
                    'doc': 'A group of rail cars and locomotives connected together.'}),

                # TODO transport:shipping:parcel <transport:container>

                ('transport:shipping:container', ('guid', {}), {
                    'interfaces': ('transport:container',),
                    'template': {'phys:object': 'shipping container'},
                    'doc': 'An individual shipping container.'}),

            ),
            'interfaces': (

                ('transport:container', {
                    'interfaces': ('phys:object',),
                    'doc': 'Properties common to a container used to transport cargo or people.',
                    'props': (

                        ('built', ('time', {}), {
                            'doc': 'The date when the {phys:object} was built.'}),

                        ('manufacturer', ('ou:org', {}), {
                            'doc': 'The organization which manufactured the {phys:object}.'}),

                        ('manufacturer:name', ('ou:name', {}), {
                            'doc': 'The name of the organization which manufactured the {phys:object}.'}),

                        ('model', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The model of the {phys:object}.'}),

                        ('serial', ('str', {'strip': True}), {
                            'doc': 'The manufacturer assigned serial number of the {phys:object}.'}),

                        ('max:occupants', ('int', {'min': 0}), {
                            'doc': 'The maximum number of occupants the {phys:object} can hold.'}),

                        ('max:cargo:mass', ('mass', {}), {
                            'doc': 'The maximum mass the {phys:object} can carry as cargo.'}),

                        ('max:cargo:volume', ('geo:dist', {}), {
                            'doc': 'The maxiumum volume the {phys:object} can carry as cargo.'}),

                        # TODO ownership interface
                        ('owner', ('ps:contact', {}), {
                            'doc': 'The contact information of the owner of the {phys:object}.'}),
                    ),
                }),
                # most containers are vehicles, but some are not...
                ('transport:vehicle', {
                    'interfaces': ('transport:container',),
                    'doc': 'Properties common to a vehicle.',
                    'props': (
                        ('operator', ('ps:contact', {}), {
                            'doc': 'The contact information of operator of the {phys:object}.'}),
                    ),
                }),

                ('transport:segment', {
                    # train, flight, drive, launch...
                    'doc': 'Properties common to a specific segment of a journey made by a vehicle.',
                    'template': {
                        'place': 'place',       # airport, seaport, starport
                        'point': 'point',       # gate, slip, stargate...
                        'vehicle': 'vehicle',   # air craft, vessel, space ship...
                        'segment': 'segment'},  # flight, voyage...

                    'props': (

                        ('status', ('str', {'enums': 'scheduled,cancelled,in-progress,completed,aborted,failed,unknown'}), {
                            'doc': 'The status of the {segment}.'}),

                        ('duration', ('duration', {}), {
                            'doc': 'The actual duration.'}),

                        ('departed', ('time', {}), {
                            'doc': 'The actual departure time.'}),

                        ('departed:place', ('geo:place', {}), {
                            'doc': 'The actual departure {place}.'}),

                        ('departed:point', (
                            'doc': 'The actual departure {point}.'}),

                        ('arrived', ('time', {}), {
                            'doc': 'The actual arrival time.'}),

                        ('arrived:place', ('geo:place', {}), {
                            'doc': 'The actual departure {place}.'}),

                        ('arrived:point', ('str', {'strip': True}), {
                            'doc': 'The actual arrival {point}.'}),

                        ('scheduled:duration', ('duration', {}), {
                            'doc': 'The scheduled duration.'}),

                        ('scheduled:departure', ('time', {}), {
                            'doc': 'The scheduled departure time.'}),

                        ('scheduled:departure:place', ('geo:place', {}), {
                            'doc': 'The scheduled departure {place}.'}),

                        ('scheduled:departure:point', ('str', {'strip': True}), {
                            'doc': 'The scheduled departure {point}.'}),

                        ('scheduled:arrival', ('time', {}), {
                            'doc': 'The scheduled arrival time.'}),

                        ('scheduled:arrival:place', ('geo:place', {}), {
                            'doc': 'The scheduled departure {place}.'}),

                        ('scheduled:arrival:point', ('str', {'strip': True}), {
                            'doc': 'The scheduled arrival {point}.'}),

                        ('occupants', ('int', {'min': 0}), {
                            'doc': 'The number of occupants of the {vehicle} on this {segment}.'}),

                        ('cargo:mass', ('mass', {}), {
                            'doc': 'The cargo mass carried by the {vehicle} on this {segment}.'}),

                        ('cargo:volume', ('geo:dist', {}), {
                            'doc': 'The cargo volume carried by the {vehicle} on this {segment}.'}),

                        ('operator', ('ps:contact', {}), {
                            'doc': 'The contact information of the operator of the {segment}.'}),

                        ('personel', ('array', {'type': 'ps:contact', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of contacts who staffed the {segment}.'}),

                        ('vehicle', ('transport:vehicle', {}), {
                            'doc': 'The {vehicle} which traveled the {segment}.'}),
                    ),
                }),
            ),
            'edges': (
                # TODO declare edges with interfaces?
                # (('transport:journey', 'carried', 'phys:object'), {
                    # 'doc': 'The object was transported via the segments declared in the journey.'}),
            ),
            'forms': (

                ('transport:journey', {}, (
                    ('segments', ('array', {'type': 'transport:segment', 'sorted': True, 'uniq': True}), {
                        'doc': 'The segments of the journey.'}),
                )),

                ('transport:parcel', {}, (
                    ('segments', ('array', {'type': 'transport:segment', 'sorted': True, 'uniq': True}), {
                        'doc': 'The segments of the journey.'}),
                )),

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

                    ('make', ('ou:name', {}), {
                        'doc': 'Deprecated. Please use :manufacturer:name.'}),

                    ('registration', ('transport:land:registration', {}), {
                        'doc': 'The current vehicle registration information.'}),
                )),
                ('transport:air:craft', {}, (
                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The aircraft tail number.'}),
                    # TODO 3.x modify type to being a taxonomy.
                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The type of aircraft.'}),
                    ('make', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'Deprecated. Please use :manufacturer:name.'}),
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

                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The tail/registration number at the time the aircraft flew this flight.'}),

                    ('cancelled', ('bool', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :status.'}),

                    ('carrier', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :operator.'}),

                    ('craft', ('transport:air:craft', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :vehicle.'}),

                    ('to:port', ('transport:air:port', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :arrival:place.'}),

                    ('from:port', ('transport:air:port', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :departure:place.'}),

                    ('stops', ('array', {'type': 'transport:air:port'}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :segments.'}),

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
                    # TODO: convert this to an entity:name
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'The name of the vessel'}),
                    ('length', ('geo:dist', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :phys:length.'}),
                    ('beam', ('geo:dist', {}), {
                        'doc': 'The official overall vessel beam'}),
                    ('flag', ('iso:3166:cc', {}), {
                        'doc': 'The country the vessel is flagged to.'}),
                    ('mmsi', ('transport:sea:mmsi', {}), {
                        'doc': 'The Maritime Mobile Service Identifier assigned to the vessel.'}),
                    ('make', ('str', {'lower': True, 'strip': True}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :manufacturer:name.'}),
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

                ('transport:rail:consist', ('guid', {}), {

                    ('cars', ('array', {'type': 'transport:rail:car', 'uniq': True}), {
                        'doc': 'The rail cars, including locomotives, which compose the consist.'}),
                }),

                ('transport:rail:segment', {}, ()),
                ('transport:rail:train', {}, (

                    ('id', ('str', {'strip': True}), {
                        'doc': 'The ID assigned to the train.'}),

                    ('segments', ('array', {'type': 'transport:segment', 'sorted': True, 'uniq': True}), {
                        'doc': 'The segments traveled by the train on the route.'}),
                )),

                ('transport:rail:car', {}, ()),

                ('transport:occupant', {}, (

                    ('contact', ('ps:contact', {}), {
                        'doc': 'Contact information of the occupant.'}),

                    ('segment', ('transport:segment', {}), {
                        'doc': 'The segment traveled by the ocupant.'}),

                    ('seat', ('str', {'strip': True}), {
                        'doc': 'The seat which the occupant sat in. Likely in a vehicle specific format.'}),

                    ('boarded', ('time', {}), {
                        'doc': 'The time when the occupant boarded the vehicle.'}),

                    ('disembarked', ('time', {}), {
                        'doc': 'The time when the occupant disembarked from the vehicle.'}),
                )),

                ('transport:shipping:container', {}, ()),
            ),
        }
        return (('transport', modl), )
