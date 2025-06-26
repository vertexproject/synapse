modeldefs = (
    ('media', {

        'forms': (

            ('media:topic', {}, (
                ('desc', ('str', {}), {
                    'doc': 'A brief description of the topic.'}),
            )),

            ('media:hashtag', {}, ()),

        ),

        'types': (

            ('media:topic', ('str', {'lower': True, 'onespace': True}), {
                'doc': 'A topic string.'}),

            ('media:hashtag', ('str', {'lower': True, 'strip': True, 'regex': r'^#[^\p{Z}#]+$'}), {
                # regex explanation:
                # - starts with pound
                # - one or more non-whitespace/non-pound character
                # The minimum hashtag is a pound with a single non-whitespace character
                'doc': 'A hashtag used in a web post.'}),

        )
    }),
)
