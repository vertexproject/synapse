import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class EntityModelTest(s_t_utils.SynTest):

    async def test_model_entity(self):

        # FIXME fully test entity:contact
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                entity:contact=*
                    :name=visi
                    :names=('visi stark', 'visi k')
                    :lifespan=(19761217, ?)
                    :email=visi@vertex.link
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'visi')
            self.eq(nodes[0].get('names'), ('visi k', 'visi stark'))
            self.eq(nodes[0].get('email'), 'visi@vertex.link')
