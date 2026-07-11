modeldefs = (
    {

        'types': (

            ('ind:name', ('base:name', {}), {
                'props': (),
                'doc': 'A name of an industry.'}),

            ('ind:industry:id', (
                    ('ou:naics', {}),
                    ('ou:sic', {}),
                    ('ou:isic', {}),
                    ('base:id', {}),
                ), {
                'doc': 'An ID given to an industry.'}),

            ('ind:industry', ('guid', {}), {
                'template': {'title': 'industry'},
                'interfaces': (
                    ('meta:reported', {}),
                    ('risk:targetable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'names'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                    ),
                },
                'props': (
                    ('id', ('ind:industry:id', {}), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the industry.'}),

                    ('ids', ('ind:industry:id', {}), {
                        'array': {},
                        'doc': 'An array of alternate IDs given to the industry.'}),

                    ('name', ('ind:name', {}), {
                        'alts': ('names',),
                        'doc': 'The name of the industry.'}),

                    ('names', ('ind:name', {}), {
                        'array': {},
                        'doc': 'An array of alternative names for the industry.'}),

                    ('type', ('ind:industry:type:taxonomy', {}), {
                        'doc': 'A taxonomy entry for the industry.'}),
                ),
                'doc': 'An industry.'}),

            ('ind:industry:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of industry types.'}),

        ),

    },
)
