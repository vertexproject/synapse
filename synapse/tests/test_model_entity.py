import synapse.tests.utils as s_t_utils

class EntityModelTest(s_t_utils.SynTest):

    async def test_model_entity(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:contact=*
                    :type=person.employee
                    :name=visi
                    :names=('visi stark', 'visi k')
                    :lifespan=(19761217, ?)
                    :desc="a cool entity"
                    :bio="a short bio"
                    :lang={[ lang:language=* :name=english ]}
                    :langs={[ lang:language=* :name=spanish ]}
                    :email=visi@vertex.link
                    :emails=(visi@gmail.com, visi@yahoo.com)
                    :phone="+15555555555"
                    :phones=("+15555555556",)
                    :user=invisig0th
                    :users=(visi0th, invisig0th2)
                    :photo={[ file:bytes=* ]}
                    :banner={[ file:bytes=* ]}
                    :id=VTX-0001
                    :creds={[ auth:passwd=cool ]}
                    :websites+=https://vertex.link
                    :social:accounts={[ inet:service:account=({"name": "invisig0th"}) ]}
                    :org={[ ou:org=({"name": "vertex"}) ]}
                    :org:name=vertex
                    :title="lead developer"
                    :titles=("senior dev", "team lead")
                    :resolved={[ ps:person=* ]}
                    :birth:place:country:code=us
                    :death:place:country:code=zz
                    :place:address:city="  new York  city "
            ]''')
            self.len(1, nodes)
            node = nodes[0]

            # entity:contact own props
            self.propeq(node, 'type', 'person.employee.')

            # entity:contactable interface props
            self.propeq(node, 'id', 'VTX-0001')
            self.propeq(node, 'name', 'visi')
            self.propeq(node, 'names', ('visi k', 'visi stark'))
            self.propeq(node, 'desc', 'a cool entity')
            self.propeq(node, 'bio', 'a short bio')
            self.propeq(node, 'email', 'visi@vertex.link')
            self.propeq(node, 'emails', ('visi@gmail.com', 'visi@yahoo.com'))
            self.propeq(node, 'phone', '15555555555')
            self.propeq(node, 'phones', ('15555555556',))
            self.propeq(node, 'user', 'invisig0th')
            self.propeq(node, 'users', ('invisig0th2', 'visi0th'))
            self.nn(node.get('photo'))
            self.nn(node.get('banner'))
            self.propeq(node, 'creds', ('cool',))
            self.propeq(node, 'websites', ('https://vertex.link',))
            self.len(1, node.get('social:accounts'))

            # entity:contactable :lang / :langs
            self.nn(node.get('lang'))
            self.len(1, node.get('langs'))
            self.len(1, await core.nodes('entity:contact :lang -> lang:language +:name=english'))
            self.len(1, await core.nodes('entity:contact :langs -> lang:language +:name=spanish'))

            # entity:contactable :desc text type preserves case
            self.propeq(node, 'desc', 'a cool entity')

            # entity:contactable :url is removed (use :websites)
            self.none(core.model.prop('entity:contact:url'))

            # entity:contactable :lifespan
            self.propeq(node, 'lifespan', (219628800000000, 9223372036854775807, 0xffffffffffffffff))

            # entity:singular interface props
            self.nn(node.get('org'))
            self.propeq(node, 'org:name', 'vertex')
            self.propeq(node, 'title', 'lead developer')
            self.propeq(node, 'titles', ('senior dev', 'team lead'))

            # entity:abstract interface props
            self.nn(node.get('resolved'))

            # geo:locatable interface props
            self.propeq(node, 'birth:place:country:code', 'us')
            self.propeq(node, 'death:place:country:code', 'zz')
            self.propeq(node, 'place:address:city', 'new york city')

            # pivots
            self.len(1, await core.nodes('entity:contact -> inet:service:account'))
            self.len(1, await core.nodes('entity:contact :photo -> file:bytes'))
            self.len(1, await core.nodes('entity:contact :banner -> file:bytes'))
            self.len(1, await core.nodes('entity:contact :org -> ou:org'))
            self.len(1, await core.nodes('entity:contact :resolved -> ps:person'))
            self.len(1, await core.nodes('entity:contact -> entity:contact:type:taxonomy'))

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
            self.propeq(nodes[0], 'type', 'owner.')
            self.propeq(nodes[0], 'percent', '50')
            self.propeq(nodes[0], 'period', (1451606400000000, 9223372036854775807, 0xffffffffffffffff))
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
            self.propeq(nodes[0], 'name', 'mygoal')
            self.propeq(nodes[0], 'names', ('bar goal', 'foo goal'))
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'desc', 'MyDesc')

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
            self.propeq(nodes[0], 'period', (1328054400000000, 1330560000000000, 2505600000000))

            self.len(1, await core.nodes('entity:attendee -> ps:person'))

            self.len(1, await core.nodes('entity:attendee -> ou:event'))
            self.len(1, await core.nodes('entity:attendee :event -> ou:event'))

            nodes = await core.nodes('''
                [ entity:campaign=*
                    :id=Foo
                    :ids=(Bar,)
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
                    :seen=2022
                    +(had)> {[ entity:goal=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'Foo')
            self.propeq(nodes[0], 'ids', ('Bar',))
            self.propeq(nodes[0], 'tag', 'cno.camp.31337')
            self.propeq(nodes[0], 'name', 'myname')
            self.propeq(nodes[0], 'names', ('bar', 'foo'))
            self.propeq(nodes[0], 'type', 'mytype.')
            self.propeq(nodes[0], 'desc', 'MyDesc')
            self.propeq(nodes[0], 'success', 1)
            self.propeq(nodes[0], 'sophistication', 40)
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'slogan', 'For The People')
            self.nn(nodes[0].get('seen'))

            self.eq(nodes[0].ndef[1], await core.callStorm('return({entity:campaign=({"id": "Bar"})})'))

            # FIXME this seems like it should work...
            # self.len(1, await core.nodes('entity:campaign --> entity:goal'))
            self.len(1, await core.nodes('entity:campaign -(had)> entity:goal'))
            self.len(1, await core.nodes(f'entity:campaign:id=Foo :slogan -> lang:phrase'))

            nodes = await core.nodes('''
                [ meta:technique=*
                    :id=Foo
                    :name=Woot
                    :names=(Foo, Bar)
                    :type=lol.woot
                    :desc=Hehe
                    :tag=woot.woot
                    :sophistication=high
                    :reporter={[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name=vertex
                    :parent={[ meta:technique=* :name=metawoot ]}
                    :used=(2025, 20260124)
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'name', 'woot')
            self.propeq(nodes[0], 'names', ('bar', 'foo'))
            self.propeq(nodes[0], 'desc', 'Hehe')
            self.propeq(nodes[0], 'type', 'lol.woot.')
            self.propeq(nodes[0], 'tag', 'woot.woot')
            self.propeq(nodes[0], 'id', 'Foo')
            self.propeq(nodes[0], 'sophistication', 40)
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.propeq(nodes[0], 'used', (1735689600000000, 1769212800000000, 33523200000000))
            self.nn(nodes[0].get('parent'))
            self.len(1, await core.nodes('meta:technique -> syn:tag'))
            self.len(1, await core.nodes('meta:technique -> meta:technique:type:taxonomy'))
            self.len(1, await core.nodes('meta:technique :reporter -> ou:org'))

            nodes = await core.nodes('meta:technique :parent -> *')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'metawoot')

            nodes = await core.nodes('''
                [ entity:contribution=*
                    :actor={[ ou:org=* :name=vertex ]}
                    :time=20220718
                    :value=10
                    :currency=usd
                    :campaign={[ entity:campaign=({"name": "good guys"}) ]}
                ]
            ''')
            self.propeq(nodes[0], 'time', 1658102400000000)
            self.propeq(nodes[0], 'value', '10')
            self.propeq(nodes[0], 'currency', 'usd')
            self.len(1, await core.nodes('entity:contribution -> entity:campaign'))
            self.len(1, await core.nodes('entity:contribution -> ou:org +:name=vertex'))

            nodes = await core.nodes('''
                [ entity:conflict=*
                    :name="World War III"
                    :period=2049*
                ]
            ''')
            self.propeq(nodes[0], 'name', 'world war iii')
            self.propeq(nodes[0], 'period', (2493072000000000, 2493072000000001, 1))

            nodes = await core.nodes('[ entity:campaign=* :name="good guys" :names=("pacific campaign",) :conflict={entity:conflict} ]')
            self.len(1, await core.nodes('entity:campaign -> entity:conflict'))
            self.len(1, await core.nodes('entity:campaign:names*[="pacific campaign"]'))

            nodes = await core.nodes('''[
                entity:contactlist=*
                    :name="Foo  Bar"
                    :source={[ it:host=* ]}
                    +(has)> {[ entity:contact=* entity:contact=* ]}
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'foo bar')
            self.eq(nodes[0].get('source')[0], 'it:host')
            self.len(1, await core.nodes('entity:contactlist :source -> it:host'))
            self.len(2, await core.nodes('entity:contactlist -(has)> entity:contact'))

            # entity:history inherits entity:contactable
            nodes = await core.nodes('''[
                entity:history=*
                    :current={[ entity:contact=({"name": "histcontact"}) ]}
                    :name="old name"
                    :desc="historical description"
                    :lang={[ lang:language=* :name=french ]}
                    :langs={[ lang:language=* :name=german ]}
                    :email=old@vertex.link
                    :phone="+15551234567"
                    :user=olduser
                    :websites+=https://old.vertex.link
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('current'))
            self.propeq(nodes[0], 'name', 'old name')
            self.propeq(nodes[0], 'desc', 'historical description')
            self.nn(nodes[0].get('lang'))
            self.len(1, nodes[0].get('langs'))
            self.propeq(nodes[0], 'email', 'old@vertex.link')
            self.propeq(nodes[0], 'phone', '15551234567')
            self.propeq(nodes[0], 'user', 'olduser')
            self.propeq(nodes[0], 'websites', ('https://old.vertex.link',))
            self.len(1, await core.nodes('entity:history :current -> entity:contact'))
            self.len(1, await core.nodes('entity:history :lang -> lang:language +:name=french'))
            self.len(1, await core.nodes('entity:history :langs -> lang:language +:name=german'))
            self.none(core.model.prop('entity:history:url'))

            # entity:discovery
            nodes = await core.nodes('''[
                entity:discovery=*
                    :actor={[ entity:contact=({"name": "discoverer"}) ]}
                    :time=20230601
                    :item={[ risk:vuln=({"name": "log4shell"}) ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.propeq(nodes[0], 'time', 1685577600000000)
            self.nn(nodes[0].get('item'))
            self.len(1, await core.nodes('entity:discovery :actor -> entity:contact'))
            self.len(1, await core.nodes('entity:discovery :item -> risk:vuln'))

    async def test_entity_title(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                $actor = {[ entity:contact=({"name": "apt28"}) ]}

                [ entity:title="software developer" ]

                { [ <(targeted)+ $actor ] }
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('entity:title', 'software developer'))

            self.isin('risk:targetable', core.model.form('entity:title').ifaces)

            self.len(1, await core.nodes('entity:title="software developer" <(targeted)- entity:contact'))

    async def test_entity_relationship(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:relationship=*
                    :type=tasks
                    :period=(2022, ?)
                    :reporter={[ ou:org=({"name": "vertex"}) ]}
                    :reporter:name=vertex
                    :source={[ ou:org=({"name": "China Ministry of State Security (MSS)"}) ]}
                    :target={[ risk:threat=({"name": "APT34", "reporter:name": "vertex"}) ]}
            ]''')

            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'tasks.')
            self.propeq(nodes[0], 'period', (1640995200000000, 9223372036854775807, 0xffffffffffffffff))
            self.propeq(nodes[0], 'source', '3d2634acf2cb0831fcd0a2dc85649960', form='ou:org')
            self.propeq(nodes[0], 'target', '882093ebe67617552b332bcdf0cff5b7', form='risk:threat')

            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.len(1, await core.nodes('entity:relationship :reporter -> ou:org'))
