modeldefs = (
    {
        'types': (

            ('belief:system', ('guid', {}), {
                'template': {'title': 'belief system', 'activity': 'was active'},
                'interfaces': (
                    ('meta:believable', {}),
                    ('entity:participable', {}),
                ),
                'props': (

                    ('type', ('belief:system:type:taxonomy', {}), {
                        'doc': 'A taxonometric type for the belief system.'}),

                ),
                'doc': 'A belief system such as an ideology, philosophy, or religion.'}),

            ('belief:system:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of belief system types.'}),

            ('belief:tenet', ('guid', {}), {
                'template': {'title': 'tenet', 'activity': 'was active'},
                'interfaces': (
                    ('meta:believable', {}),
                    ('entity:participable', {}),
                ),
                'props': (),
                'doc': 'A concrete tenet potentially shared by multiple belief systems.'}),
        ),
        'edges': (

            (('belief:system', 'has', 'belief:tenet'), {
                'doc': 'The belief system includes the tenet.'}),

        ),
    },
)
