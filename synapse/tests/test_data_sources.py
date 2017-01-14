from synapse.tests.common import *

import synapse.data.sources as s_sources

class SourcesTest(SynTest):

    def test_data_source_iana_tlds(self):
        self.assertTrue( 'link' in s_sources.load('iana.tlds')[0] )
