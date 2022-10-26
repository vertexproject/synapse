import synapse.lib.module as s_module


class MediaModule(s_module.CoreModule):

    def getModelDefs(self):
        name = 'media'

        ctors = ()

        forms = (
            ('media:news:taxonomy', {}, ()),
            ('media:news', {}, (
                ('url', ('inet:url', {}), {
                    'ex': 'http://cnn.com/news/mars-lander.html',
                    'doc': 'The (optional) URL where the news was published.'}),

                ('url:fqdn', ('inet:fqdn', {}), {
                    'ex': 'cnn.com',
                    'doc': 'The FQDN within the news URL.'}),

                ('type', ('media:news:taxonomy', {}), {
                    'doc': 'A taxonomy for the type of reporting or news.'}),

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


                ('publisher:name', ('ou:name', {}), {
                    'doc': 'The name of the publishing org used to publish the news.'}),

                ('published', ('time', {}), {
                    'ex': '20161201180433',
                    'doc': 'The date the news item was published.'}),

                ('org', ('ou:alias', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use :publisher:name.'}),

                ('author', ('ps:name', {}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use :authors array of ps:contact nodes.'}),

                ('authors', ('array', {'type': 'ps:contact', 'split': ',', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of authors of the news item.'}),

                ('rss:feed', ('inet:url', {}), {
                    'doc': 'The RSS feed that published the news.'}),

                ('ext:id', ('str', {}), {
                    'doc': 'An external identifier specified by the publisher.'}),

                ('topics', ('array', {'type': 'media:topic', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of relevant topics discussed in the report.'}),
            )),

            ('media:topic', {}, (
                ('desc', ('str', {}), {
                    'doc': 'A brief description of the topic.'}),
            )),
        )

        types = (
            ('media:news', ('guid', {}), {
                'doc': 'A GUID for a news article or report.'}),

            ('media:news:taxonomy', ('taxonomy', {}), {
                'doc': 'A taxonomy of types or sources of news.'}),

            ('media:topic', ('str', {'lower': True, 'onespace': True}), {
                'doc': 'A topic string.'}),
        )

        modldef = (name, {
            'ctors': ctors,
            'forms': forms,
            'types': types,
        })
        return (modldef, )
