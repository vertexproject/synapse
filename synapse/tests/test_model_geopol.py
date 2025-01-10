import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils

class GeoPolModelTest(s_t_utils.SynTest):

    async def test_geopol_country(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ pol:country=*
                    :founded=2022
                    :dissolved=2023
                    :name=visiland
                    :names=(visitopia,)
                    :iso2=vi
                    :iso3=vis
                    :isonum=31337
                    :currencies=(usd, vcoins, PESOS, USD)
                ]
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq('visiland', nodes[0].get('name'))
            self.eq(('visitopia',), nodes[0].get('names'))
            self.eq(1640995200000, nodes[0].get('founded'))
            self.eq(1672531200000, nodes[0].get('dissolved'))
            self.eq('vi', nodes[0].get('iso2'))
            self.eq('vis', nodes[0].get('iso3'))
            self.eq(31337, nodes[0].get('isonum'))
            self.eq(('pesos', 'usd', 'vcoins'), nodes[0].get('currencies'))
            self.len(2, await core.nodes('pol:country -> geo:name'))
            self.len(3, await core.nodes('pol:country -> econ:currency'))

            self.len(1, nodes := await core.nodes('[ pol:country=({"name": "visitopia"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''
                    [ pol:vitals=*
                        :country={pol:country:name=visiland}
                        :area=1sq.km
                        :population=1
                        :currency=usd
                        :econ:currency=usd
                        :econ:gdp = 100
                    ]
                    { -> pol:country [ :vitals={pol:vitals} ] }
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('country'))
            self.eq(1, nodes[0].get('population'))
            self.eq(1000000, nodes[0].get('area'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('100', nodes[0].get('econ:gdp'))
            self.eq('usd', nodes[0].get('econ:currency'))
            self.len(1, await core.nodes('pol:country:vitals :vitals -> pol:vitals'))

    async def test_types_iso2(self):
        async with self.getTestCore() as core:
            t = core.model.type('pol:iso2')

            self.eq(t.norm('Fo'), ('fo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'A')
            self.raises(s_exc.BadTypeValu, t.norm, 'asD')

    async def test_types_iso3(self):
        async with self.getTestCore() as core:
            t = core.model.type('pol:iso3')

            self.eq(t.norm('Foo'), ('foo', {}))
            self.raises(s_exc.BadTypeValu, t.norm, 'As')
            self.raises(s_exc.BadTypeValu, t.norm, 'asdF')

    async def test_types_unextended(self):
        # The following types are subtypes that do not extend their base type
        async with self.getTestCore() as core:
            self.nn(core.model.type('pol:country'))  # guid
            self.nn(core.model.type('pol:isonum'))  # int

    async def test_model_geopol_election(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ pol:election=* :name="2024 US Presidential Election" :time=2024-11-03 ]
            ''')
            self.eq(1730592000000, nodes[0].get('time'))
            self.eq('2024 us presidential election', nodes[0].get('name'))

            nodes = await core.nodes('''
                [ pol:office=*
                    :title=POTUS
                    :position={[ou:position=*]}
                    :govbody={[ou:org=* :name="Office of the President"]}
                    :termlimit=2
                ]
            ''')
            self.eq('potus', nodes[0].get('title'))
            self.eq(2, nodes[0].get('termlimit'))
            self.len(1, await core.nodes('pol:office:title=potus -> ou:org'))
            self.len(1, await core.nodes('pol:office:title=potus -> ou:jobtitle'))
            self.len(1, await core.nodes('pol:office:title=potus -> ou:position'))

            nodes = await core.nodes('''
                [ pol:race=*
                    :election={pol:election}
                    :office={pol:office:title=potus}
                    :voters=500
                    :turnout=499
                ]
            ''')
            self.eq(500, nodes[0].get('voters'))
            self.eq(499, nodes[0].get('turnout'))
            self.len(1, await core.nodes('pol:race -> pol:office +:title=potus'))
            self.len(1, await core.nodes('pol:race -> pol:election +:time=20241103'))

            nodes = await core.nodes('''
                [ pol:candidate=*
                    :id=" P00009423"
                    :race={pol:race}
                    :contact={[ps:contact=* :name=whippit]}
                    :winner=$lib.true
                    :campaign={[ou:campaign=* :name=whippit4prez ]}
                    :party={[ou:org=* :name=vertex]}
                ]
            ''')
            self.eq(1, nodes[0].get('winner'))
            self.eq('P00009423', nodes[0].get('id'))
            self.len(1, await core.nodes('pol:candidate -> pol:race'))
            self.len(1, await core.nodes('pol:candidate -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('pol:candidate -> ps:contact +:name=whippit'))
            self.len(1, await core.nodes('pol:candidate -> ou:campaign +:name=whippit4prez'))

            nodes = await core.nodes('''
                [ pol:term=*
                    :office={pol:office:title=potus}
                    :contact={ps:contact:name=whippit}
                    :race={pol:race}
                    :party={ou:org:name=vertex}
                    :start=20250120
                    :end=20290120
                ]
            ''')
            self.eq(1737331200000, nodes[0].get('start'))
            self.eq(1863561600000, nodes[0].get('end'))
            self.len(1, await core.nodes('pol:term -> pol:race'))
            self.len(1, await core.nodes('pol:term -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('pol:term -> pol:office +:title=potus'))
            self.len(1, await core.nodes('pol:term -> ps:contact +:name=whippit'))

            nodes = await core.nodes('''
                [ pol:pollingplace=*
                    :place={[ geo:place=* :name=library ]}
                    :election={pol:election}
                    :name=pollingplace00
                    :opens=202411030800-05:00
                    :closes=202411032000-05:00
                    :opened=202411030800-05:00
                    :closed=202411032000-05:00
                ]
            ''')
            self.eq(1730638800000, nodes[0].get('opens'))
            self.eq(1730682000000, nodes[0].get('closes'))
            self.eq(1730638800000, nodes[0].get('opened'))
            self.eq(1730682000000, nodes[0].get('closed'))
            self.len(1, await core.nodes('pol:pollingplace -> pol:election'))
            self.len(1, await core.nodes('pol:pollingplace -> geo:place +:name=library'))
            self.len(1, await core.nodes('pol:pollingplace -> geo:name +geo:name=pollingplace00'))

    async def test_model_geopol_immigration(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ pol:immigration:status=*
                    :country = {[ pol:country=* :name=woot ]}
                    :contact = {[ ps:contact=* :name=visi ]}
                    :type = citizen.naturalized
                    :state = requested
                    :began = 20230328
                    :ended = 2024
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('country'))
            self.nn(nodes[0].get('contact'))
            self.eq('requested', nodes[0].get('state'))
            self.eq('citizen.naturalized.', nodes[0].get('type'))
            self.eq(1679961600000, nodes[0].get('began'))
            self.eq(1704067200000, nodes[0].get('ended'))
