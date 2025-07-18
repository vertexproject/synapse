modeldefs = (
    ('belief', {
        'types': (

            ('belief:system', ('guid', {}), {
                'doc': 'A belief system such as an ideology, philosophy, or religion.'}),

            ('belief:system:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of belief system types.'}),

            ('belief:tenet', ('guid', {}), {
                'doc': 'A concrete tenet potentially shared by multiple belief systems.'}),

            ('belief:subscriber', ('guid', {}), {
                'doc': 'A contact which subscribes to a belief system.'}),
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

            ('belief:subscriber', {}, (

                # FIXME entity:individual?
                ('contact', ('entity:actor', {}), {
                    'doc': 'The contact which subscribes to the belief system.'}),

                ('system', ('belief:system', {}), {
                    'doc': 'The belief system to which the contact subscribes.'}),

                ('period', ('ival', {}), {
                    'prevnames': ('began', 'ended'),
                    'doc': 'The time period when the contact subscribed to the belief system.'}),
            )),
        ),
        'edges': (

            (('belief:system', 'has', 'belief:tenet'), {
                'doc': 'The belief system includes the tenet.'}),

            (('belief:subscriber', 'follows', 'belief:tenet'), {
                'doc': 'The subscriber is assessed to generally adhere to the specific tenet.'}),
        ),
    }),
)
