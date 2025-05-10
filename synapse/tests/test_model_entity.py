import synapse.tests.utils as s_test

class EntityModelTest(s_test.SynTest):

    async def test_entity_relationship(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:relationship=*
                    :type=tasks
                    :period=(2022, ?)
                    :source={[ ou:org=({"name": "China Ministry of State Security (MSS)"}) ]}
                    :target={[ risk:threat=({"org:name": "APT34", "reporter:name": "vertex"}) ]}
            ]''')

            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 'tasks.')
            self.eq(nodes[0].get('period'), (1640995200000, 9223372036854775807))
            self.eq(nodes[0].get('source'), ('ou:org', '3332a704ed21dc3274d5731acc54a0ee'))
            self.eq(nodes[0].get('target'), ('risk:threat', 'e15738ebae52273300b51c08eaad3a36'))
