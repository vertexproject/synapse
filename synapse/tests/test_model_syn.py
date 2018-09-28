import synapse.tests.utils as s_t_utils

class SynModelTest(s_t_utils.SynTest):

    async def test_model_syn_tag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('syn:tag', 'foo.bar.baz')

                self.eq(node.get('up'), 'foo.bar')
                self.eq(node.get('depth'), 2)
                self.eq(node.get('base'), 'baz')

                node = await snap.getNodeByNdef(('syn:tag', 'foo.bar'))
                self.nn(node)

                node = await snap.getNodeByNdef(('syn:tag', 'foo'))
                self.nn(node)
