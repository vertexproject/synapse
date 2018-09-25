import synapse.tests.utils as s_t_utils

class SynModelTest(s_t_utils.SynTest):

    def test_model_syn_tag(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('syn:tag', 'foo.bar.baz')

                self.eq(node.get('up'), 'foo.bar')
                self.eq(node.get('depth'), 2)
                self.eq(node.get('base'), 'baz')

                node = snap.getNodeByNdef(('syn:tag', 'foo.bar'))
                self.nn(node)

                node = snap.getNodeByNdef(('syn:tag', 'foo'))
                self.nn(node)
