modeldefs = (
    ('pol', {

        'types': (

            ('pol:country', ('guid', {}), {
                'interfaces': (
                    ('risk:targetable', {}),
                ),
                'doc': 'A GUID for a country.'}),

            ('pol:immigration:status', ('guid', {}), {
                'doc': 'A node which tracks the immigration status of a contact.'}),

            ('pol:immigration:status:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of immigration status types.'}),

            ('pol:vitals', ('guid', {}), {
                'doc': 'A set of vital statistics about a country.'}),

            ('pol:isonum', ('int', {}), {
                'doc': 'The ISO integer country code.', 'ex': '840'}),

            ('pol:election', ('guid', {}), {
                'doc': 'An election involving one or more races for office.'}),

            ('pol:race', ('guid', {}), {
                'doc': 'An individual race for office.'}),

            ('pol:office', ('guid', {}), {
                'doc': 'An elected or appointed office.'}),

            ('pol:term', ('guid', {}), {
                'doc': 'A term in office held by a specific individual.'}),

            ('pol:candidate', ('guid', {}), {
                'doc': 'A candidate for office in a specific race.'}),

            ('pol:pollingplace', ('guid', {}), {
                'doc': 'An official place where ballots may be cast for a specific election.'}),
            # TODO districts
            # TODO referendums
        ),
        'forms': (

            ('pol:country', {}, (
                ('flag', ('file:bytes', {}), {
                    'doc': 'A thumbnail image of the flag of the country.'}),

                ('code', ('iso:3166:alpha2', {}), {
                    'prevnames': ('iso2',),
                    'doc': 'The ISO 3166 Alpha-2 country code.'}),

                ('iso:3166:alpha3', ('iso:3166:alpha3', {}), {
                    'prevnames': ('iso3',),
                    'doc': 'The ISO 3166 Alpha-3 country code.'}),

                ('iso:3166:numeric3', ('iso:3166:numeric3', {}), {
                    'prevnames': ('isonum',),
                    'doc': 'The ISO 3166 Numeric-3 country code.'}),

                ('tld', ('inet:fqdn', {}), {
                    'doc': 'The top-level domain for the country.'}),

                ('name', ('meta:name', {}), {
                    'alts': ('names',),
                    'doc': 'The name of the country.'}),

                ('names', ('array', {'type': 'meta:name'}), {
                    'doc': 'An array of alternate or localized names for the country.'}),

                ('government', ('ou:org', {}), {
                    'doc': 'The government of the country.'}),

                ('place', ('geo:place', {}), {
                    'doc': 'The geospatial properties of the country.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('founded', 'dissolved'),
                    'doc': 'The period over which the country existed.'}),

                ('vitals', ('pol:vitals', {}), {
                    'doc': 'The most recent known vitals for the country.'}),

                ('currencies', ('array', {'type': 'econ:currency'}), {
                    'doc': 'The official currencies used in the country.'}),
            )),
            ('pol:immigration:status:type:taxonomy', {}, ()),
            ('pol:immigration:status', {}, (

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact information for the immigration status record.'}),

                ('country', ('pol:country', {}), {
                    'doc': 'The country that the contact is/has immigrated to.'}),

                ('type', ('pol:immigration:status:type:taxonomy', {}), {
                    'ex': 'citizen.naturalized',
                    'doc': 'A taxonomy entry for the immigration status type.'}),

                ('state', ('str', {'enums': 'requested,active,rejected,revoked,renounced'}), {
                    'doc': 'The state of the immigration status.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('began', 'ended'),
                    'doc': 'The time period when the contact was granted the status.'}),

            )),
            ('pol:vitals', {}, (

                ('country', ('pol:country', {}), {
                    'doc': 'The country that the statistics are about.'}),

                ('time', ('time', {}), {
                    'prevnames': ('asof',),
                    'doc': 'The time that the vitals were measured.'}),

                ('area', ('geo:area', {}), {
                    'doc': 'The area of the country.'}),

                ('population', ('int', {}), {
                    'doc': 'The total number of people living in the country.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The national currency.'}),

                ('econ:currency', ('econ:currency', {}), {
                    'doc': 'The currency used to record price properties.'}),

                ('econ:gdp', ('econ:price', {}), {
                    'doc': 'The gross domestic product of the country.'}),
            )),
            ('pol:election', {}, (

                ('name', ('meta:name', {}), {
                    'ex': '2022 united states congressional midterm election',
                    'doc': 'The name of the election.'}),

                ('time', ('time', {}), {
                    'doc': 'The date of the election.'}),
            )),
            # TODO jurisdiction / districts
            # TODO oversight authority
            ('pol:race', {}, (
                ('election', ('pol:election', {}), {
                    'doc': 'The election that includes the race.'}),
                ('office', ('pol:office', {}), {
                    'doc': 'The political office that the candidates in the race are running for.'}),
                ('voters', ('int', {}), {
                    'doc': 'The number of eligible voters for this race.'}),
                ('turnout', ('int', {}), {
                    'doc': 'The number of individuals who voted in this race.'}),
            )),
            ('pol:office', {}, (

                ('title', ('entity:title', {}), {
                    'ex': 'united states senator',
                    'doc': 'The title of the political office.'}),

                ('position', ('ou:position', {}), {
                    'doc': 'The position this office holds in the org chart for the governing body.'}),

                ('termlimit', ('int', {}), {
                    'doc': 'The maximum number of times a single person may hold the office.'}),

                ('govbody', ('ou:org', {}), {
                    'doc': 'The governmental body which contains the office.'}),
            )),
            ('pol:term', {}, (

                ('office', ('pol:office', {}), {
                    'doc': 'The office held for the term.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('start', 'end'),
                    'doc': 'The time period of the term of office.'}),

                ('race', ('pol:race', {}), {
                    'doc': 'The race that determined who held office during the term.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact information of the person who held office during the term.'}),

                ('party', ('ou:org', {}), {
                    'doc': 'The political party of the person who held office during the term.'}),
            )),
            ('pol:candidate', {}, (

                ('id', ('meta:id', {}), {
                    'alts': ('ids',),
                    'doc': 'A unique ID for the candidate issued by an election authority.'}),

                ('ids', ('array', {'type': 'meta:id'}), {
                    'doc': 'An array of unique IDs for the candidate issued by an election authority.'}),

                ('contact', ('entity:contact', {}), {
                    'doc': 'The contact information of the candidate.'}),

                ('race', ('pol:race', {}), {
                    'doc': 'The race the candidate is participating in.'}),

                ('campaign', ('entity:campaign', {}), {
                    'doc': 'The official campaign to elect the candidate.'}),

                ('winner', ('bool', {}), {
                    'doc': 'Records the outcome of the race.'}),

                ('party', ('ou:org', {}), {
                    'doc': 'The declared political party of the candidate.'}),

                ('incumbent', ('bool', {}), {
                    'doc': 'Set to true if the candidate is an incumbent in this race.'}),
            )),
            ('pol:pollingplace', {}, (

                ('election', ('pol:election', {}), {
                    'doc': 'The election that the polling place is designated for.'}),

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the polling place at the time of the election. This may differ from the official place name.'}),

                ('place', ('geo:place', {}), {
                    'doc': 'The place where votes were cast.'}),

                ('opens', ('time', {}), {
                    'doc': 'The time that the polling place is scheduled to open.'}),

                ('closes', ('time', {}), {
                    'doc': 'The time that the polling place is scheduled to close.'}),

                ('opened', ('time', {}), {
                    'doc': 'The time that the polling place opened.'}),

                ('closed', ('time', {}), {
                    'doc': 'The time that the polling place closed.'}),
            )),
        ),

    }),
)
