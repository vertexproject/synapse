import synapse.tests.common as s_test

class SynModelTest(s_test.SynTest):

    def test_model_syn_tag(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                node = snap.addNode('syn:tag', 'foo.bar.baz')

                self.eq(node.get('up'), 'foo.bar')
                self.eq(node.get('depth'), 3)
                self.eq(node.get('base'), 'baz')

                node = snap.getNodeByNdef(('syn:tag', 'foo.bar'))
                self.nn(node)

                node = snap.getNodeByNdef(('syn:tag', 'foo'))
                self.nn(node)
