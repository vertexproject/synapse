import synapse.lib.module as s_module


class MediaModule(s_module.CoreModule):

    def getModelDefs(self):
        name = 'media'

        ctors = ()

        forms = (
            ('media:news', {}, (
                ('url', ('inet:url', {}), {
                    'doc': 'The (optional) URL where the news was published.',
                    'ex': 'http://cnn.com/news/mars-lander.html',
                }),
                ('url:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN within the news URL.',
                    'ex': 'cnn.com',
                }),
                ('file', ('file:bytes', {}), {
                    'doc': 'The (optional) file blob containing or published as the news.',
                }),
                ('title', ('str', {'lower': True}), {
                    'doc': 'Title/Headline for the news.',
                    'ex': 'mars lander reaches mars',
                    'disp': {'hint': 'text'},
                }),
                ('summary', ('str', {}), {
                    'doc': 'A brief summary of the news item.',
                    'ex': 'lorum ipsum',
                    'disp': {'hint': 'text'},
                }),
                ('published', ('time', {}), {
                    'doc': 'The date the news item was published.',
                    'ex': '20161201180433',
                }),
                ('org', ('ou:alias', {}), {
                    'doc': 'The org alias which published the news.',
                    'ex': 'microsoft',
                }),
                ('author', ('ps:name', {}), {
                    'doc': 'The free-form author of the news.',
                    'deprecated': True,
                    'ex': 'stark,anthony'
                }),
                ('authors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of authors of the news item.',
                }),
                ('rss:feed', ('inet:url', {}), {
                    'doc': 'The RSS feed that published the news.',
                }),
            )),
        )

        types = (
            ('media:news', ('guid', {}), {
                'doc': 'A GUID for a news article or report.'
            }),
        )

        modldef = (name, {
            'ctors': ctors,
            'forms': forms,
            'types': types,
        })
        return (modldef, )
