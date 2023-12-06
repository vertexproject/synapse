import logging

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class MediaModelTest(s_t_utils.SynTest):

    async def test_news(self):
        formname = 'media:news'
        async with self.getTestCore() as core:

            valu = 32 * 'a'
            file0 = 64 * 'f'
            publisher = 32 * 'b'
            cont = s_common.guid()
            props = {
                'url': 'https://vertex.link/synapse',
                'file': file0,
                'title': 'Synapse is awesome! ',
                'summary': 'I forget ',
                'published': 0,
                'updated': 0,
                'org': 'verteX',
                'authors': cont,
                'publisher': publisher,
                'publisher:name': 'The Vertex Project, LLC.',
                'rss:feed': 'http://vertex.link/rss',
                'topics': ('woot', 'Foo   Bar'),
            }

            q = '''[(media:news=$valu
                    :url=$p.url :file=$p.file :title=$p.title
                    :summary=$p.summary :published=$p.published :updated=$p.updated
                    :org=$p.org :authors=$p.authors
                    :publisher=$p.publisher :publisher:name=$p."publisher:name"
                    :rss:feed=$p."rss:feed" :topics=$p.topics
                    )]'''
            opts = {'vars': {'valu': valu, 'p': props}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.ndef, ('media:news', valu))
            self.eq(node.get('url'), 'https://vertex.link/synapse')
            self.eq(node.get('url:fqdn'), 'vertex.link')
            self.eq(node.get('file'), 'sha256:' + file0)
            self.eq(node.get('title'), 'synapse is awesome! ')
            self.eq(node.get('published'), 0)
            self.eq(node.get('updated'), 0)
            self.eq(node.get('publisher'), publisher)
            self.eq(node.get('publisher:name'), 'the vertex project, llc.')
            self.eq(node.get('org'), 'vertex')
            self.eq(node.get('rss:feed'), 'http://vertex.link/rss')
            self.eq(node.get('authors'), (cont,))
            self.eq(node.get('topics'), ('foo bar', 'woot'))

            self.len(2, await core.nodes('media:news -> media:topic'))

            nodes = await core.nodes('media:news [ :updated="2023-01-01" ]')
            self.eq(nodes[0].props.get('updated'), 1672531200000)

            nodes = await core.nodes('media:news [ :updated="2022-01-01" ]')
            self.eq(nodes[0].props.get('updated'), 1672531200000)
