# CN province abbreviations taken from https://www.cottongen.org/data/nomenclatures/China_provinces
icpregex = '^(皖|京|渝|闽|粤|甘|桂|黔|豫|鄂|冀|琼|港|黑|湘|吉|苏|赣|辽|澳|蒙|宁|青|川|鲁|沪|陕|晋|津|台|新|藏|滇|浙)ICP(备|证)[0-9]{8}号$'

modeldefs = (
    {
        'types': (

            ('gov:cn:icp', ('base:id', {'regex': icpregex}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (),
                'doc': 'A Chinese Internet Content Provider ID.'}),

            ('gov:cn:mucd', ('base:id', {'regex': '^[0-9]{5}部队$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (),
                'doc': 'A Chinese PLA MUCD.'}),

            ('iso:oid', ('str', {'regex': '^([0-2])((\\.0)|(\\.[1-9][0-9]*))*$'}), {
                'props': (

                    ('desc', ('text', {}), {
                        'doc': 'A description of the value or meaning of the OID.'}),

                    ('name', ('title', {}), {
                        'doc': 'The name for the deepest tree element.'}),
                ),
                'doc': 'An ISO Object Identifier string.'}),

            ('iso:3166:alpha2', ('str', {'lower': True, 'regex': '^[a-z0-9]{2}$'}), {
                'prevnames': ('pol:iso2', 'iso:3166:cc'),
                'ex': 'us',
                'props': (),
                'doc': 'An ISO 3166 Alpha-2 country code.'}),

            ('iso:3166:alpha3', ('str', {'lower': True, 'regex': '^[a-z0-9]{3}$'}), {
                'prevnames': ('pol:iso3',),
                'ex': 'usa',
                'props': (),
                'doc': 'An ISO 3166 Alpha-3 country code.'}),

            ('iso:3166:numeric3', ('str', {'regex': '^[0-9]{3}$'}), {
                'prevnames': ('pol:isonum',),
                'ex': '840',
                'props': (),
                'doc': 'An ISO 3166 Numeric-3 country code.'}),

            ('gov:intl:un:m49', ('int', {'min': 1, 'max': 999}), {
                'doc': 'UN M49 Numeric Country Code.'}),

            ('gov:us:ssn', ('base:id', {'regex': '^[0-9]{3}-[0-9]{2}-[0-9]{4}$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (),
                'doc': 'A US Social Security Number (SSN).'}),

            ('gov:us:zip', ('int', {'min': 0, 'max': 99999}), {
                'props': (),
                'doc': 'A US Postal Zip Code.'}),

            ('gov:us:cage', ('base:id', {}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (),
                'doc': 'A Commercial and Government Entity (CAGE) code.'}),
        ),
    },
)
