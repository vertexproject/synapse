modeldefs = (
    ('media', {
        'forms': (
            ('media:news:type:taxonomy', {'prevnames': ('media:news:taxonomy',)}, ()),
            ('media:news', {}, (
                ('url', ('inet:url', {}), {
                    'ex': 'http://cnn.com/news/mars-lander.html',
                    'doc': 'The (optional) URL where the news was published.'}),

                ('url:fqdn', ('inet:fqdn', {}), {
                    'ex': 'cnn.com',
                    'doc': 'The FQDN within the news URL.'}),

                ('type', ('media:news:type:taxonomy', {}), {
                    'doc': 'A taxonomy for the type of article or report.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The (optional) file blob containing or published as the news.'}),

                ('title', ('str', {'lower': True}), {
                    'ex': 'mars lander reaches mars',
                    'disp': {'hint': 'text'},
                    'doc': 'Title/Headline for the news.'}),

                ('summary', ('str', {}), {
                    'ex': 'lorum ipsum',
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the news item.'}),

                ('publisher', ('ou:org', {}), {
                    'doc': 'The organization which published the news.'}),

                ('publisher:name', ('meta:name', {}), {
                    'doc': 'The name of the publishing org used to publish the news.'}),

                ('published', ('time', {}), {
                    'ex': '20161201180433',
                    'doc': 'The date the news item was published.'}),

                ('updated', ('time', {'ismax': True}), {
                    'ex': '20161201180433',
                    'doc': 'The last time the news item was updated.'}),

                ('authors', ('array', {'type': 'entity:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of authors of the news item.'}),

                ('rss:feed', ('inet:url', {}), {
                    'doc': 'The RSS feed that published the news.'}),

                ('id', ('str', {}), {
                    'doc': 'An external identifier specified by the publisher.'}),

                ('topics', ('array', {'type': 'media:topic', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of relevant topics discussed in the report.'}),
            )),

            ('media:topic', {}, (
                ('desc', ('str', {}), {
                    'doc': 'A brief description of the topic.'}),
            )),

            ('media:hashtag', {}, ()),
        ),

        'types': (
            ('media:news', ('guid', {}), {
                'doc': 'A GUID for a news article or report.'}),

            ('media:news:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of news types.',
            }),

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
