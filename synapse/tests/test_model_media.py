import logging

import synapse.tests.common as s_t_common

logger = logging.getLogger(__name__)


class MediaModelTest(s_t_common.SynTest):

    def test_news(self):
        formname = 'media:news'
        async with self.getTestCore() as core:
            with core.snap() as snap:

                valu = 32 * 'a'
                expected_ndef = (formname, valu)
                input_props = {
                    'url': 'https://vertex.link/synapse',
                    'file': 64 * 'f',
                    'title': 'Synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'org': 'verteX',
                }
                expected_props = {
                    'url': 'https://vertex.link/synapse',
                    'url:fqdn': 'vertex.link',
                    'file': 'sha256:' + 64 * 'f',
                    'title': 'synapse is awesome! ',
                    'summary': 'I forget ',
                    'published': 0,
                    'author': '?,?',
                    'org': 'vertex',
                }
                node = snap.addNode(formname, valu, props=input_props)
                self.checkNode(node, (expected_ndef, expected_props))
