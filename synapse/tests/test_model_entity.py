import synapse.exc as s_exc
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
                    :username=invisig0th
                    :usernames=(visi0th, invisig0th2)
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
            self.propeq(node, 'username', 'invisig0th')
            self.propeq(node, 'usernames', ('invisig0th2', 'visi0th'))
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

            # entity:contactable :lifespan uses an entity:lifespan ( began / ended ) ival
            self.propeq(node, 'lifespan', (219628800000000, 9223372036854775807, 0xffffffffffffffff))
            self.eq(219628800000000, node.get('lifespan.began'))
            self.nn(node.get('lifespan.ended'))
            with self.raises(s_exc.NoSuchVirt):
                node.get('lifespan.min')

            props = node.getProps(virts=True)
            self.eq(props.get('lifespan.began'), 219628800000000)
            self.eq(props.get('lifespan.ended'), 9223372036854775807)
            self.eq(props.get('lifespan.duration'), 0xffffffffffffffff)
            self.eq(props.get('lifespan.precision'), 30)

            # entity:singular interface props
            self.nn(node.get('org'))
            self.propeq(node, 'org:name', 'vertex')
            self.propeq(node, 'title', 'lead developer')
            self.propeq(node, 'titles', ('senior dev', 'team lead'))

            # entity:resolvable interface props
            self.nn(node.get('resolved'))

            # geo:locatable interface props
            self.propeq(node, 'birth:place:country:code', 'us')
            self.propeq(node, 'death:place:country:code', 'zz')
            self.propeq(node, 'place:address:city', 'new York city')

            # pivots
            self.len(1, await core.nodes('entity:contact -> inet:service:account'))
            self.len(1, await core.nodes('entity:contact :photo -> file:bytes'))
            self.len(1, await core.nodes('entity:contact :banner -> file:bytes'))
            self.len(1, await core.nodes('entity:contact :org -> ou:org'))
            self.len(1, await core.nodes('entity:contact :resolved -> ps:person'))
            self.len(1, await core.nodes('entity:contact -> entity:contact:type:taxonomy'))

            # entity:contact implements the risk:targetable interface
            self.isin('risk:targetable', core.model.form('entity:contact').ifaces)
            self.len(1, await core.nodes('''
                $victim = {[ entity:contact=({"name": "vertex"}) ]}
                [ entity:contact=({"name": "apt1"}) ] { [ +(targeted)> $victim ] }
            '''))
            self.len(1, await core.nodes('entity:contact:name=vertex <(targeted)- entity:contact:name=apt1'))

            nodes = await core.nodes('''
                $item = {[ transport:air:craft=* ]}
                $actor = {[ entity:contact=({"name": "visi"}) ]}

                [ entity:had=({"actor": $actor, "item": $item})
                    :type=owner
                    :period=(2016, ?)
                    :actor:name=visi
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'owner.')
            self.propeq(nodes[0], 'period', (1451606400000000, 9223372036854775807, 0xffffffffffffffff))
            self.len(1, await core.nodes('entity:had :actor -> * +:name=visi'))
            self.len(1, await core.nodes('entity:had :item -> transport:air:craft'))

            # entity:had implements the entity:activity interface which provides
            # the actor, actor:name, and period props.
            self.true(core.model.form('entity:had').implements('entity:activity'))
            self.propeq(nodes[0], 'actor:name', 'visi')

            # entity:owned extends entity:had and provides the :percent prop.
            nodes = await core.nodes('''
                $item = {[ transport:air:craft=* ]}
                $actor = {[ entity:contact=({"name": "visi"}) ]}

                [ entity:owned=({"actor": $actor, "item": $item})
                    :type=owner
                    :period=(2016, ?)
                    :percent=50
                    :actor:name=visi
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'type', 'owner.')
            self.propeq(nodes[0], 'percent', '50')
            self.propeq(nodes[0], 'period', (1451606400000000, 9223372036854775807, 0xffffffffffffffff))
            self.propeq(nodes[0], 'actor:name', 'visi')
            self.len(1, await core.nodes('entity:owned :actor -> * +:name=visi'))
            self.len(1, await core.nodes('entity:owned :item -> transport:air:craft'))

            # entity:owned extends entity:had and inherits the entity:activity interface.
            self.eq(core.model.form('entity:owned').type.subof, 'entity:had')
            self.true(core.model.form('entity:owned').implements('entity:activity'))
            self.none(core.model.form('entity:had').prop('percent'))
            self.nn(core.model.form('entity:owned').prop('percent'))

            nodes = await core.nodes('''[
                entity:goal=*
                    :name=MyGoal
                    :names=(Foo Goal, Bar Goal, Bar Goal)
                    :type=foo.bar
                    :desc=MyDesc
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'entity:goal')
            self.propeq(nodes[0], 'name', 'MyGoal')
            self.propeq(nodes[0], 'names', ('Bar Goal', 'Foo Goal'))
            self.propeq(nodes[0], 'type', 'foo.bar.')
            self.propeq(nodes[0], 'desc', 'MyDesc')

            ndef = nodes[0].ndef
            self.len(1, nodes := await core.nodes('[ entity:goal=({"name": "foo goal"}) ]'))
            self.eq(nodes[0].ndef, ndef)

            nodes = await core.nodes('''[
                entity:attended=*
                    :actor={[ ps:person=* ]}
                    :period=(201202,201203)
                    :activity={[ ou:event=* ]}
                    :role=staff
                    :inperson=1
            ]''')
            self.len(1, nodes)
            self.true(core.model.form('entity:attended').implements('entity:activity'))
            self.true(core.model.form('ou:event').implements('entity:attendable'))
            self.propeq(nodes[0], 'role', 'staff')
            self.propeq(nodes[0], 'inperson', True)
            self.propeq(nodes[0], 'period', (1328054400000000, 1330560000000000, 2505600000000))

            self.len(1, await core.nodes('entity:attended -> ps:person'))

            self.len(1, await core.nodes('entity:attended -> ou:event'))
            self.len(1, await core.nodes('entity:attended :activity -> ou:event'))

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
                    :seen=2022
                    +(supported)> {[ entity:goal=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'Foo')
            self.propeq(nodes[0], 'ids', ('Bar',))
            self.propeq(nodes[0], 'tag', 'cno.camp.31337')
            self.propeq(nodes[0], 'name', 'MyName')
            self.propeq(nodes[0], 'names', ('Bar', 'Foo'))
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
            self.len(1, await core.nodes('entity:campaign -(supported)> entity:goal'))
            self.len(1, await core.nodes('entity:campaign:id=Foo :slogan -> lang:phrase'))

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
                    :seen=(20210101, 20210201)
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'name', 'Woot')
            self.propeq(nodes[0], 'names', ('Bar', 'Foo'))
            self.propeq(nodes[0], 'desc', 'Hehe')
            self.propeq(nodes[0], 'type', 'lol.woot.')
            self.propeq(nodes[0], 'tag', 'woot.woot')
            self.propeq(nodes[0], 'id', 'Foo')
            self.propeq(nodes[0], 'sophistication', 40)
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.nn(nodes[0].get('parent'))
            self.nn(nodes[0].get('seen'))
            self.len(1, await core.nodes('meta:technique -> syn:tag'))
            self.len(1, await core.nodes('meta:technique -> meta:technique:type:taxonomy'))
            self.len(1, await core.nodes('meta:technique :reporter -> ou:org'))

            nodes = await core.nodes('meta:technique :parent -> *')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'metawoot')

            # entity:contributed implements entity:event
            self.true(core.model.form('entity:contributed').implements('entity:event'))
            nodes = await core.nodes('''
                [ entity:contributed=*
                    :actor={[ ou:org=* :name=vertex ]}
                    :time=20220718
                    :value=10
                    :campaign={[ entity:campaign=({"name": "good guys"}) ]}
                ]
            ''')
            self.propeq(nodes[0], 'time', 1658102400000000)
            self.propeq(nodes[0], 'value', '10')
            self.nn(nodes[0].get('actor'))
            self.len(1, await core.nodes('entity:contributed -> entity:campaign'))
            self.len(1, await core.nodes('entity:contributed -> ou:org +:name=vertex'))

            nodes = await core.nodes('''
                [ entity:conflict=*
                    :name="World War III"
                    :period=2049*
                ]
            ''')
            self.propeq(nodes[0], 'name', 'World War III')
            self.propeq(nodes[0], 'period', (2493072000000000, 2493072000000001, 1))

            nodes = await core.nodes('[ entity:campaign=* :name="good guys" :names=("pacific campaign",) ]')
            self.len(1, await core.nodes('entity:campaign:names*[="pacific campaign"]'))

            nodes = await core.nodes('''[
                entity:contactlist=*
                    :name="Foo  Bar"
                    :desc="A list of foo bar contacts."
                    :source={[ it:host=* ]}
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'Foo Bar')
            self.propeq(nodes[0], 'desc', 'A list of foo bar contacts.')
            self.eq(nodes[0].get('source')[0], 'it:host')
            self.len(1, await core.nodes('entity:contactlist :source -> it:host'))

            nodes = await core.nodes('''[
                entity:contactlist:entry=*
                    :list={ entity:contactlist:name="foo bar" }
                    :contact={[ entity:contact=* ]}
                    :period=(2024, 2025)
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('list'))
            self.nn(nodes[0].get('contact'))
            self.propeq(nodes[0], 'period', (1704067200000000, 1735689600000000, 31622400000000))
            self.len(1, await core.nodes('entity:contactlist:entry :list -> entity:contactlist +:name="foo bar"'))
            self.len(1, await core.nodes('entity:contactlist:entry :contact -> entity:contact'))

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
                    :username=olduser
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
            self.propeq(nodes[0], 'username', 'olduser')
            self.propeq(nodes[0], 'websites', ('https://old.vertex.link',))
            self.len(1, await core.nodes('entity:history :current -> entity:contact'))
            self.len(1, await core.nodes('entity:history :lang -> lang:language +:name=french'))
            self.len(1, await core.nodes('entity:history :langs -> lang:language +:name=german'))
            self.none(core.model.prop('entity:history:url'))

            # entity:discovery was removed in favor of entity:discovered
            self.none(core.model.form('entity:discovery'))

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

            # entity:title is a text type: case preserving but case insensitive
            nodes = await core.nodes('[ entity:title="Chief Widget Officer" ]')
            self.eq(nodes[0].ndef, ('entity:title', 'Chief Widget Officer'))
            self.len(1, await core.nodes('entity:title="chief widget officer"'))

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
            self.propeq(nodes[0], 'source', 'd47841da254e1750ce5971aba031ef55', type='ou:org')
            self.propeq(nodes[0], 'target', '2a1a72be69ad522338639723d2cb718a', type='risk:threat')

            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.len(1, await core.nodes('entity:relationship :reporter -> ou:org'))

    async def test_entity_causal_events(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:discovered=*
                    :actor={[ entity:contact=* :name=discoverer ]}
                    :time=20230101
                    :item={[ risk:vuln=* :name=zerodayX ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('item'))
            self.propeq(nodes[0], 'time', 1672531200000000)
            self.len(1, await core.nodes('entity:discovered :actor -> entity:contact +:name=discoverer'))
            self.len(1, await core.nodes('entity:discovered :item -> risk:vuln +:name=zerodayx'))

            nodes = await core.nodes('''[
                entity:signed=*
                    :actor={[ entity:contact=* :name=signer ]}
                    :time=20230201
                    :doc={[ doc:contract=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('doc'))
            self.len(1, await core.nodes('entity:signed :actor -> entity:contact +:name=signer'))
            self.len(1, await core.nodes('entity:signed :doc -> doc:contract'))

            # entity:destroyable is a marker interface and entity:destroyed records a destruction event
            self.eq((), core.model.ifaces.get('entity:destroyable').get('props', ()))
            self.true(core.model.form('entity:destroyed').implements('entity:event'))
            nodes = await core.nodes('''[
                entity:destroyed=*
                    :actor={[ entity:contact=* :name=wrecker ]}
                    :time=20230301
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.len(1, await core.nodes('entity:destroyed :actor -> entity:contact +:name=wrecker'))

            # forms which do not implement entity:destroyable are rejected for :item
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ entity:destroyed=* :item={[ ou:org=* ]} ]')

            nodes = await core.nodes('''[
                entity:asked=*
                    :actor={[ entity:contact=* :name=buyer ]}
                    :time=20230101
                    :value=50.00
                    :expires=20230201
                    :activity={[ risk:extortion=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.propeq(nodes[0], 'value', '50')
            self.nn(nodes[0].get('expires'))
            self.nn(nodes[0].get('activity'))
            self.len(1, await core.nodes('entity:asked :actor -> entity:contact +:name=buyer'))
            self.len(1, await core.nodes('entity:asked :activity -> risk:extortion'))

            nodes = await core.nodes('''[
                entity:offered=*
                    :actor={[ entity:contact=* :name=seller ]}
                    :time=20230101
                    :value=75.00
                    :expires=20230201
                    :activity={[ risk:extortion=* :name="APT99 Extortion" ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.propeq(nodes[0], 'value', '75')
            self.len(1, await core.nodes('entity:offered :actor -> entity:contact +:name=seller'))
            self.len(1, await core.nodes('entity:offered :activity -> risk:extortion'))

            nodes = await core.nodes('''[
                entity:supported=*
                    :role=sponsor
                    :desc="Backed the campaign."
                    :activity={[ entity:campaign=({"name": "good guys"}) ]}
                    :value=1000
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'role', 'sponsor')
            self.propeq(nodes[0], 'desc', 'Backed the campaign.')
            self.propeq(nodes[0], 'value', '1000')
            self.len(1, await core.nodes('entity:supported :activity -> entity:campaign'))

    async def test_entity_believed(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                entity:believed=*
                    :actor={[ entity:contact=* :name=visi ]}
                    :belief={[ belief:system=* ]}
                    :period=(20230209, 20230210)
                    +(followed)> {[ belief:tenet=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.nn(nodes[0].get('belief'))

            self.propeq(nodes[0], 'period', (1675900800000000, 1675987200000000, 86400000000))

            self.len(1, await core.nodes('entity:believed -(followed)> belief:tenet'))
