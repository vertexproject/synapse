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
                $item = {[ transport:air:craft=* ]}
                $actor = {[ entity:contact=({"name": "visi"}) ]}

                [ entity:had=({"actor": $actor, "item": $item})
                    :type=owner
                    :period=(2016, ?)
                    :percent=50
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('type'), 'owner.')
            self.eq(nodes[0].get('percent'), '50')
            self.eq(nodes[0].get('period'), (1451606400000000, 9223372036854775807))
            self.len(1, await core.nodes('entity:had :actor -> * +:name=visi'))
            self.len(1, await core.nodes('entity:had :item -> transport:air:craft'))

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

            nodes = await core.nodes('''
                [ entity:campaign=*
                    :id=Foo
                    :type=MyType
                    :name=MyName
                    :names=(Foo, Bar)
                    :slogan="For The People"
                    :desc=MyDesc
                    :success=1
                    :sophistication=high
                    :tag=cno.camp.31337
                    :reporter={[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name=vertex
                    :actor={[ entity:contact=* ]}
                    :actors={[ entity:contact=* ]}
                    +(had)> {[ entity:goal=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'Foo')
            self.eq(nodes[0].get('tag'), 'cno.camp.31337')
            self.eq(nodes[0].get('name'), 'myname')
            self.eq(nodes[0].get('names'), ('bar', 'foo'))
            self.eq(nodes[0].get('type'), 'mytype.')
            self.eq(nodes[0].get('desc'), 'MyDesc')
            self.eq(nodes[0].get('success'), 1)
            self.eq(nodes[0].get('sophistication'), 40)
            self.nn(nodes[0].get('reporter'))
            self.eq(nodes[0].get('reporter:name'), 'vertex')
            self.eq(nodes[0].get('slogan'), 'For The People')

            # FIXME this seems like it should work...
            # self.len(1, await core.nodes('entity:campaign --> entity:goal'))
            self.len(1, await core.nodes('entity:campaign -(had)> entity:goal'))
            self.len(1, await core.nodes(f'entity:campaign:id=Foo :slogan -> lang:phrase'))

            nodes = await core.nodes('''
                [ meta:technique=*
                    :id=Foo
                    :name=Woot
                    :type=lol.woot
                    :desc=Hehe
                    :tag=woot.woot
                    :sophistication=high
                    :reporter=$lib.gen.orgByName(vertex)
                    :reporter:name=vertex
                ]
            ''')
            self.len(1, nodes)
            self.nn('reporter')
            self.eq('woot', nodes[0].get('name'))
            self.eq('Hehe', nodes[0].get('desc'))
            self.eq('lol.woot.', nodes[0].get('type'))
            self.eq('woot.woot', nodes[0].get('tag'))
            self.eq('Foo', nodes[0].get('id'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.len(1, await core.nodes('meta:technique -> syn:tag'))
            self.len(1, await core.nodes('meta:technique -> meta:technique:type:taxonomy'))
            self.len(1, await core.nodes('meta:technique :reporter -> ou:org'))

            nodes = await core.nodes('''
                [ entity:contribution=*
                    :actor={[ ou:org=* :name=vertex ]}
                    :time=20220718
                    :value=10
                    :currency=usd
                    :campaign={[ entity:campaign=({"name": "good guys"}) ]}
                ]
            ''')
            self.eq(1658102400000000, nodes[0].get('time'))
            self.eq('10', nodes[0].get('value'))
            self.eq('usd', nodes[0].get('currency'))
            self.len(1, await core.nodes('entity:contribution -> entity:campaign'))
            self.len(1, await core.nodes('entity:contribution -> ou:org +:name=vertex'))

            nodes = await core.nodes('''
                [ entity:conflict=*
                    :name="World War III"
                    :timeline=*
                    :period=2049*
                ]
            ''')
            self.eq(nodes[0].get('name'), 'world war iii')
            self.eq(nodes[0].get('period'), (2493072000000000, 2493072000000001))

            self.len(1, await core.nodes('entity:conflict -> meta:timeline'))

            nodes = await core.nodes('[ entity:campaign=* :name="good guys" :names=("pacific campaign",) :conflict={entity:conflict} ]')
            self.len(1, await core.nodes('entity:campaign -> entity:conflict'))
            self.len(1, await core.nodes('entity:campaign:names*[="pacific campaign"]'))

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
