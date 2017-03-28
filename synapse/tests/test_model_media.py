from synapse.tests.common import *

class MediaTest(SynTest):

    def test_models_media_news(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('media:news', guid(), title='Synapse is Awesome!', url='http://www.VERTEX.link/synapse')
            self.nn(node)
            self.eq( node[1].get('media:news:org'), '??' )
            self.eq( node[1].get('media:news:author'), '?,?' )
            self.eq( node[1].get('media:news:title'), 'synapse is awesome!')

            self.eq( node[1].get('media:news:url'), 'http://www.vertex.link/synapse' )
