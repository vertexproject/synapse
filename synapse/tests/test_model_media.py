import logging

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class MediaModelTest(s_t_utils.SynTest):

    async def test_news(self):
        formname = 'media:news'
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                valu = 32 * 'a'
                publisher = 32 * 'b'
                expected_ndef = (formname, valu)
                cont = s_common.guid()
                input_props = {
                    'url': 'https://vertex.link/synapse',
                    'file': 64 * 'f',
                    'title': 'Synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'org': 'verteX',
                    'authors': cont,
                    'publisher': publisher,
                    'publisher:name': 'The Vertex Project, LLC.',
                    'rss:feed': 'http://vertex.link/rss',
                    'topics': ('woot', 'Foo   Bar'),
                }
                expected_props = {
                    'url': 'https://vertex.link/synapse',
                    'url:fqdn': 'vertex.link',
                    'file': 'sha256:' + 64 * 'f',
                    'title': 'synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'publisher': publisher,
                    'publisher:name': 'the vertex project, llc.',
                    'org': 'vertex',
                    'rss:feed': 'http://vertex.link/rss',
                    'authors': (cont,),
                    'topics': ('foo bar', 'woot'),
                }
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))
            self.len(2, await core.nodes('media:news -> media:topic'))
