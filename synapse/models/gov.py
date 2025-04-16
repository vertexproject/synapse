modeldefs = (
    ('gov:cn', {
        'types': (
            ('gov:cn:icp',
                ('int', {}),
                {'doc': 'A Chinese Internet Content Provider ID.'},
             ),
            ('gov:cn:mucd',
                ('int', {}),
                {'doc': 'A Chinese PLA MUCD.'},
             ),
        ),
        'forms': (
            ('gov:cn:icp', {}, (
                ('org', ('ou:org', {}), {
                    'doc': 'The org with the Internet Content Provider ID.',
                }),
            )),
            # TODO - Add 'org' as a secondary property to mcud?
            ('gov:cn:mucd', {}, ()),
        )
    }),
    ('gov:intl', {
        'types': (
            ('iso:oid', ('str', {'regex': '^([0-2])((\\.0)|(\\.[1-9][0-9]*))*$'}), {
                'doc': 'An ISO Object Identifier string.'}),

            ('iso:3166:cc', ('str', {'lower': True, 'regex': '^[a-z]{2}$'}), {
                'doc': 'An ISO 3166 2 digit country code.'}),

            ('gov:intl:un:m49', ('int', {'min': 1, 'max': 999}), {
                'doc': 'UN M49 Numeric Country Code.'}),
        ),

        'forms': (
            # FIXME ?
            ('iso:oid', {}, (
                ('descr', ('str', {}), {
                    'doc': 'A description of the value or meaning of the OID.'}),
                ('identifier', ('str', {}), {
                    'doc': 'The string identifier for the deepest tree element.'}),
            )),
        ),
    }),
    ('gov:us', {
        'types': (
            # FIXME
            ('gov:us:ssn', ('int', {}), {'doc': 'A US Social Security Number (SSN).'}),
            ('gov:us:zip', ('int', {}), {'doc': 'A US Postal Zip Code.'}),
            ('gov:us:cage', ('str', {'lower': True}), {'doc': 'A Commercial and Government Entity (CAGE) code.'}),
        ),

        'forms': (
            ('gov:us:cage', {}, (
                ('org', ('ou:org', {}), {'doc': 'The organization which was issued the CAGE code.'}),
                ('name0', ('entity:name', {}), {'doc': 'The name of the organization.'}),
                ('name1', ('str', {'lower': True}), {'doc': 'Name Part 1.'}),
                ('street', ('str', {'lower': True}), {}),
                ('city', ('str', {'lower': True}), {}),
                ('state', ('str', {'lower': True}), {}),
                ('zip', ('gov:us:zip', {}), {}),
                ('cc', ('pol:iso2', {}), {}),
                ('country', ('str', {'lower': True}), {}),
                ('phone0', ('tel:phone', {}), {}),
                ('phone1', ('tel:phone', {}), {}),
            )),

            ('gov:us:ssn', {}, []),
            ('gov:us:zip', {}, []),
        ),
    }),
)
