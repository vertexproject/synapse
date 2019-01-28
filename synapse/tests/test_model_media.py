import logging

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class MediaModelTest(s_t_utils.SynTest):

    async def test_news(self):

        formname = 'media:news'
        fileguid = s_common.guid()
        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                valu = 32 * 'a'
                expected_ndef = (formname, valu)
                input_props = {
                    'url': 'https://vertex.link/synapse',
                    'file': fileguid,
                    'title': 'Synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'org': 'verteX',
                }
                expected_props = {
                    'url': 'https://vertex.link/synapse',
                    'url:fqdn': 'vertex.link',
                    'file': fileguid,
                    'title': 'synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'author': '?,?',
                    'org': 'vertex',
                }
                node = await snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))
