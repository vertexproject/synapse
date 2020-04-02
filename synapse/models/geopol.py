import synapse.lib.module as s_module

class PolModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('pol', {

                'types': (

                    ('pol:country',
                        ('guid', {}),
                        {'doc': 'A GUID for a country'}
                    ),

                    ('pol:iso2',
                        ('str', {'lower': True, 'regex': '^[a-z0-9]{2}$', 'nullval': '??'}),
                        {'doc': 'The 2 digit ISO country code', 'ex': 'us'}
                    ),

                    ('pol:iso3',
                        ('str', {'lower': True, 'regex': '^[a-z0-9]{3}$', 'nullval': '??'}),
                        {'doc': 'The 3 digit ISO country code', 'ex': 'usa'}
                    ),

                    ('pol:isonum',
                        ('int', {}),
                        {'doc': 'The ISO integer country code', 'ex': '840'}
                    ),

                ),

                'forms': (

                    ('pol:country', {}, (
                        ('flag', ('file:bytes', {}), {}),
                        ('founded', ('time', {}), {}),
                        ('iso2', ('pol:iso2', {}), {}),
                        ('iso3', ('pol:iso3', {}), {}),
                        ('isonum', ('pol:isonum', {}), {}),
                        ('name', ('str', {'lower': True}), {}),
                        ('pop', ('int', {}), {}),
                        ('tld', ('inet:fqdn', {}), {}),
                    )),

                ),

            }),
        )
