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
                    :creds={[ auth:passwd=cool ]}
                    :websites+=https://vertex.link
                    :social:accounts={[ inet:service:account=({"name": "invisig0th"}) ]}
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'visi')
            self.eq(nodes[0].get('names'), ('visi k', 'visi stark'))
            self.eq(nodes[0].get('email'), 'visi@vertex.link')
            self.eq(nodes[0].get('creds'), (('auth:passwd', 'cool'),))
            self.eq(nodes[0].get('websites'), ('https://vertex.link',))
            self.len(1, nodes[0].get('social:accounts'))
            self.len(1, await core.nodes('entity:contact -> inet:service:account'))

            nodes = await core.nodes('''
                $item = {[ inet:fqdn=vertex.link ]}
                $actor = {[ entity:contact=({"name": "visi"}) ]}

                [ entity:possession=({"actor": $actor.ndef(), "item": $item.ndef()})
                    :type=owner
                    :period=(2016, ?)
                    :percent=50
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 'owner.')
            self.eq(nodes[0].get('percent'), '50')
            self.eq(nodes[0].get('period'), (1451606400000000, 9223372036854775807))
            self.len(1, await core.nodes('entity:possession :item -> inet:fqdn'))
            self.len(1, await core.nodes('entity:possession :actor -> * +:name=visi'))

            nodes = await core.nodes('''[
                entity:goal=*
                    :name=MyGoal
                    :names=(Foo Goal, Bar Goal, Bar Goal)
                    :type=foo.bar
                    :desc=MyDesc
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'entity:goal')
            self.eq(nodes[0].get('name'), 'mygoal')
            self.eq(nodes[0].get('names'), ('bar goal', 'foo goal'))
            self.eq(nodes[0].get('type'), 'foo.bar.')
            self.eq(nodes[0].get('desc'), 'MyDesc')

            ndef = nodes[0].ndef
            self.len(1, nodes := await core.nodes('[ entity:goal=({"name": "foo goal"}) ]'))
            self.eq(nodes[0].ndef, ndef)

            nodes = await core.nodes('''[
                entity:attendee=*
                    :person={[ ps:person=* ]}
                    :period=(201202,201203)
                    :event={[ ou:event=* ]}
                    :roles+=staff
                    :roles+=STAFF
            ]''')
            self.len(1, nodes)
            self.eq(('staff',), nodes[0].get('roles'))
            self.eq(nodes[0].get('period'), (1328054400000000, 1330560000000000))

            self.len(1, await core.nodes('entity:attendee -> ps:person'))

            self.len(1, await core.nodes('entity:attendee -> ou:event'))
            self.len(1, await core.nodes('entity:attendee :event -> ou:event'))

    async def test_entity_relationship(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:relationship=*
                    :type=tasks
                    :period=(2022, ?)
                    :reporter={[ ou:org=({"name": "China Ministry of State Security (MSS)"}) ]}
                    :target={[ risk:threat=({"name": "APT34", "reporter:name": "vertex"}) ]}
            ]''')

            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 'tasks.')
            self.eq(nodes[0].get('period'), (1640995200000000, 9223372036854775807))
            self.eq(nodes[0].get('reporter'), ('ou:org', '3332a704ed21dc3274d5731acc54a0ee'))
            self.eq(nodes[0].get('target'), ('risk:threat', 'c0b2aeb72e61e692bdee1554bf931819'))
