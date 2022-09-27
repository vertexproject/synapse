import synapse.lib.module as s_module

class PolModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('pol', {

                'types': (

                    ('pol:country', ('guid', {}),
                        {'doc': 'A GUID for a country.'}
                    ),
                    ('pol:vitals', ('guid', {}),
                        {'doc': 'A set of vital statistics about a country.'}
                    ),
                    ('pol:iso2', ('str', {'lower': True, 'regex': '^[a-z0-9]{2}$'}),
                        {'doc': 'The 2 digit ISO country code.', 'ex': 'us'}),

                    ('pol:iso3', ('str', {'lower': True, 'regex': '^[a-z0-9]{3}$'}),
                        {'doc': 'The 3 digit ISO country code.', 'ex': 'usa'}),

                    ('pol:isonum', ('int', {}),
                        {'doc': 'The ISO integer country code.', 'ex': '840'}),

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
                        ('flag', ('file:bytes', {}), {}),
                        ('iso2', ('pol:iso2', {}), {}),
                        ('iso3', ('pol:iso3', {}), {}),
                        ('isonum', ('pol:isonum', {}), {}),
                        ('pop', ('int', {}), {
                            'deprecated': True,
                            'doc': 'Deprecated. Please use :vitals::population.'}),
                        ('tld', ('inet:fqdn', {}), {}),

                        ('name', ('geo:name', {}), {
                            'doc': 'The name of the country.'}),
                        ('names', ('array', {'type': 'geo:name', 'uniq': True, 'sorted': True}), {
                            'doc': 'An array of alternate or localized names for the country.'}),
                        ('place', ('geo:place', {}), {
                            'doc': 'A geo:place node representing the geospatial properties of the country.'}),
                        ('founded', ('time', {}), {
                            'doc': 'The date that the country was founded.'}),
                        ('dissolved', ('time', {}), {
                            'doc': 'The date that the country was dissolved.'}),
                        ('vitals', ('ps:vitals', {}), {
                            'doc': 'The most recent known vitals for the country.'}),
                    )),
                    ('pol:vitals', {}, (
                        ('country', ('pol:country', {}), {
                            'doc': 'The country that the statistics are about.'}),
                        ('asof', ('time', {}), {
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
                        ('name', ('str', {'onespace': True, 'lower': True}), {
                            'ex': '2022 united states congressional midterm election',
                            'doc': 'The name of the election.'}),
                        ('time', ('time', {}), {
                            'doc': 'The date of the election.'}),
                    )),
                    # TODO jurisdiction / districts
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
                        ('title', ('ou:jobtitle', {}), {
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
                        ('start', ('time', {}), {
                            'doc': 'The start of the term of office.'}),
                        ('end', ('time', {}), {
                            'doc': 'The end of the term of office.'}),
                        ('race', ('pol:race', {}), {
                            'doc': 'The race that determined who held office during the term.'}),
                        ('contact', ('ps:contact', {}), {
                            'doc': 'The contact information of the person who held office during the term.'}),
                        ('party', ('ou:org', {}), {
                            'doc': 'The political party of the person who held office during the term.'}),
                    )),
                    ('pol:candidate', {}, (
                        ('contact', ('ps:contact', {}), {
                            'doc': 'The contact information of the candidate.'}),
                        ('race', ('pol:race', {}), {
                            'doc': 'The race the candidate is participating in.'}),
                        ('campaign', ('ou:campaign', {}), {
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
                        ('name', ('geo:name', {}), {
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
