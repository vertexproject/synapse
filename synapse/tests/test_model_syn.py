import synapse.tests.common as s_test

class SynModelTest(s_test.SynTest):

    def test_model_syn_tag(self):

        with self.getTestCore() as core:

            with core.xact(write=True) as xact:

                node = xact.addNode('syn:tag', 'foo.bar.baz')

                self.eq(node.get('up'), 'foo.bar')
                self.eq(node.get('depth'), 3)
                self.eq(node.get('base'), 'baz')

                node = xact.getNodeByNdef(('syn:tag', 'foo.bar'))
                self.nn(node)

                node = xact.getNodeByNdef(('syn:tag', 'foo'))
                self.nn(node)
