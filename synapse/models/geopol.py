import synapse.lib.module as s_module

class PolModule(s_module.CoreModule):

    def getModelDefs(self):
        return (
            ('pol', {

                'types': (

                    ('pol:country',
                        ('guid', {}),
                        {'doc': 'A GUID for a country.'}
                    ),

                    ('pol:iso2',
                        ('str', {'lower': True, 'regex': '^[a-z0-9]{2}$'}),
                        {'doc': 'The 2 digit ISO country code.', 'ex': 'us'}
                    ),

                    ('pol:iso3',
                        ('str', {'lower': True, 'regex': '^[a-z0-9]{3}$'}),
                        {'doc': 'The 3 digit ISO country code.', 'ex': 'usa'}
                    ),

                    ('pol:isonum',
                        ('int', {}),
                        {'doc': 'The ISO integer country code.', 'ex': '840'}
                    ),
                    ('pol:citizen', ('guid', {}), {
                        'doc': 'A citizenship record.'}),

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
                    ('pol:citizen', {}, (
                        ('country:org', ('ou:org', {}), {
                            'doc': 'The country which the contact is a citizen of.'}),
                        ('issuer:orgname', ('ou:name', {}), {
                            'doc': 'The country name. Used for entity resolution.'}),
                        ('country:orgfqdn', ('ou:org', {}), {
                            'doc': 'The country FQDN. Used for entity resolution.'}),
                        ('contact', ('ps:contact', {}), {
                            'doc': 'The contact information of the citizen.'}),
                        ('type', ('pol:citizentype', {}), {
                            'ex': 'birth',
                            'doc': 'A taxonomy of types of citizenship.'}),
                        ('granted', ('time', {}), {
                            'doc': 'The date on which citizenship was granted.'}),
                        ('revoked', ('time', {}), {
                            'doc': 'The date on which citizenship was revoked.'}),
                    )),

                ),

            }),
        )
