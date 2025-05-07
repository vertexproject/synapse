import logging

import synapse.exc as s_exc
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
                'authors': cont,
                'publisher': publisher,
                'publisher:name': 'The Vertex Project, LLC.',
                'rss:feed': 'http://vertex.link/rss',
                'topics': ('woot', 'Foo   Bar'),
            }

            q = '''[(media:news=$valu
                    :url=$p.url :file=$p.file :title=$p.title
                    :summary=$p.summary :published=$p.published :updated=$p.updated
                    :authors=$p.authors
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
            self.eq(node.get('rss:feed'), 'http://vertex.link/rss')
            self.eq(node.get('authors'), (cont,))
            self.eq(node.get('topics'), ('foo bar', 'woot'))

            self.len(2, await core.nodes('media:news -> media:topic'))

            nodes = await core.nodes('media:news [ :updated="2023-01-01" ]')
            self.eq(nodes[0].get('updated'), 1672531200000000)

            nodes = await core.nodes('media:news [ :updated="2022-01-01" ]')
            self.eq(nodes[0].get('updated'), 1672531200000000)
    async def test_hashtag(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[ media:hashtag="#🫠" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#🫠🫠" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#·bar"]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo·"]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo〜"]'))
            self.len(1, await core.nodes('[ media:hashtag="#hehe" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo·bar"]'))  # note the interpunct
            self.len(1, await core.nodes('[ media:hashtag="#foo〜bar"]'))  # note the wave dash
            self.len(1, await core.nodes('[ media:hashtag="#fo·o·······b·ar"]'))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ media:hashtag="foo" ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ media:hashtag="#foo#bar" ]')

            # All unicode whitespace from:
            # https://www.compart.com/en/unicode/category/Zl
            # https://www.compart.com/en/unicode/category/Zp
            # https://www.compart.com/en/unicode/category/Zs
            whitespace = [
                '\u0020', '\u00a0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
                '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a', '\u202f', '\u205f',
                '\u3000', '\u2028', '\u2029',
            ]
            for char in whitespace:
                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ media:hashtag="#foo{char}bar" ]')

                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ media:hashtag="#{char}bar" ]')

                # These are allowed because strip=True
                await core.callStorm(f'[ media:hashtag="#foo{char}" ]')
                await core.callStorm(f'[ media:hashtag=" #foo{char}" ]')
