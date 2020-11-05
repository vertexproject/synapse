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
                    'rss:feed': 'http://vertex.link/rss',
                }
                expected_props = {
                    'url': 'https://vertex.link/synapse',
                    'url:fqdn': 'vertex.link',
                    'file': 'sha256:' + 64 * 'f',
                    'title': 'synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'org': 'vertex',
                    'rss:feed': 'http://vertex.link/rss',
                    'authors': (cont,),
                }
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))
