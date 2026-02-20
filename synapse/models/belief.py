modeldefs = (
    ('belief', {
        'types': (

            ('belief:system', ('guid', {}), {
                'interfaces': (
                    ('meta:believable', {}),
                ),
                'doc': 'A belief system such as an ideology, philosophy, or religion.'}),

            ('belief:system:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of belief system types.'}),

            ('belief:tenet', ('guid', {}), {
                'interfaces': (
                    ('meta:believable', {}),
                ),
                'doc': 'A concrete tenet potentially shared by multiple belief systems.'}),
        ),
        'forms': (

            ('belief:system', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the belief system.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the belief system.'}),

                ('type', ('belief:system:type:taxonomy', {}), {
                    'doc': 'A taxonometric type for the belief system.'}),

                ('began', ('time', {}), {
                    'doc': 'The time that the belief system was first observed.'}),
            )),

            ('belief:system:type:taxonomy', {}, ()),

            ('belief:tenet', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the tenet.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the tenet.'}),
            )),

        ),
        'edges': (

            (('belief:system', 'has', 'belief:tenet'), {
                'doc': 'The belief system includes the tenet.'}),
        ),
    }),
)
