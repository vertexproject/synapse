import synapse.lib.module as s_module

class TransportModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (

                ('transport:air:craft', ('guid', {}), {
                    'doc': 'An individual aircraft.'}),

                ('transport:air:tailnum', ('str', {'lower': True, 'strip': True, 'regex': '^[a-z0-9-]{2,}$'}), {
                    'doc': 'An aircraft registration number or military aircraft serial number.',
                    'ex': 'ff023'}),

                ('transport:air:flightnum', ('str', {'lower': True, 'strip': True, 'replace': ((' ', ''),), 'regex': '^[a-z]{2}[0-9]{1,4}$'}), {
                    'doc': 'A commercial flight designator including airline and serial.',
                    'ex': 'ua2437'}),

                ('transport:air:telem', ('guid', {}), {
                    'doc': 'A telemtry sample from an aircraft in transit.'}),

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

                # TODO a few more items to plumb eventually
                # ('transport:sea:hin',
                # ('transport:sea:port',
            ),
            'forms': (
                ('transport:air:craft', {}, (
                    ('tailnum', ('transport:air:tailnum', {}), {
                        'doc': 'The aircraft tail number.'}),
                )),
                ('transport:air:port', {}, (
                    ('name', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
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
                        'doc': 'An ordered list of aiport codes for stops which occured during this flight.'}),
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
                    # TODO
                    # ('airspeed',
                    # ('groundspeed'
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
                    ('name', ('str', {'lower': True, 'onespace': True, 'strip': True}), {
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
                    ('draft', ('geo:dist', {}), {
                        'doc': 'The keel depth at the time.'}),
                    ('airdraft', ('geo:dist', {}), {
                        'doc': 'The maximum height of the ship from the waterline.'}),
                )),
            ),
        }
        return (('transport', modl), )
