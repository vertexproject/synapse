import synapse.lib.module as s_module


class MediaModule(s_module.CoreModule):

    def getModelDefs(self):
        name = 'media'

        ctors = ()

        forms = (
            ('media:news:taxonomy', {}, {}),
            ('media:news', {}, (
                ('url', ('inet:url', {}), {
                    'doc': 'The (optional) URL where the news was published.',
                    'ex': 'http://cnn.com/news/mars-lander.html',
                }),
                ('url:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The FQDN within the news URL.',
                    'ex': 'cnn.com',
                }),
                ('type', ('media:news:taxonomy', {}), {
                    'doc': 'A taxonomy for the type of reporting or news.'
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
                ('publisher', ('ou:org', {}), {
                    'doc': 'The organization which published the news.',
                }),
                ('publisher:name', ('ou:name', {}), {
                    'doc': 'The name the publishing org used to publish the news.',
                }),
                ('published', ('time', {}), {
                    'doc': 'The date the news item was published.',
                    'ex': '20161201180433',
                }),
                ('org', ('ou:alias', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use :publisher:name.',
                }),
                ('author', ('ps:name', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use :authors array of ps:contact nodes.',
                }),
                ('authors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of authors of the news item.',
                }),
                ('rss:feed', ('inet:url', {}), {
                    'doc': 'The RSS feed that published the news.',
                }),
                ('ext:id', ('str', {}), {
                    'doc': 'An external identifier specified by the publisher.',
                }),
            )),
        )

        types = (
            ('media:news', ('guid', {}), {
                'doc': 'A GUID for a news article or report.'
            }),
            ('media:news:taxonomy', ('taxonomy', {}), {
                'doc': 'A taxonomy of types or sources of news.',
            }),
        )

        modldef = (name, {
            'ctors': ctors,
            'forms': forms,
            'types': types,
        })
        return (modldef, )
