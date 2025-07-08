# CN province abbreviations taken from https://www.cottongen.org/data/nomenclatures/China_provinces
icpregex = '^(皖|京|渝|闽|粤|甘|桂|黔|豫|鄂|冀|琼|港|黑|湘|吉|苏|赣|辽|澳|蒙|宁|青|川|鲁|沪|陕|晋|津|台|新|藏|滇|浙)ICP(备|证)[0-9]{8}号$'

modeldefs = (
    ('gov:cn', {
        'types': (

            # FIXME update type. not just an int.
            ('gov:cn:icp', ('str', {'regex': icpregex}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'A Chinese Internet Content Provider ID.'}),

            ('gov:cn:mucd', ('str', {'regex': '[0-9]{5}'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'A Chinese PLA MUCD.'}),
        ),
        'forms': (
            ('gov:cn:icp', {}, ()),
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
            ('iso:oid', {}, (

                ('desc', ('str', {}), {
                    'doc': 'A description of the value or meaning of the OID.'}),

                ('identifier', ('str', {}), {
                    'doc': 'The string identifier for the deepest tree element.'}),
            )),
        ),
    }),
    ('gov:us', {
        'types': (

            ('gov:us:ssn', ('str', {'regex': '^[0-9]{3}-[0-9]{2}-[0-9]{4}'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'A US Social Security Number (SSN).'}),

            ('gov:us:zip', ('int', {'regex': '^[0-9]{5}'}), {
                'doc': 'A US Postal Zip Code.'}),

            ('gov:us:cage', ('str', {'lower': True}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'A Commercial and Government Entity (CAGE) code.'}),
        ),

        'forms': (
            ('gov:us:cage', {}, (
                ('org', ('ou:org', {}), {'doc': 'The organization which was issued the CAGE code.'}),
                ('name0', ('meta:name', {}), {'doc': 'The name of the organization.'}),
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
