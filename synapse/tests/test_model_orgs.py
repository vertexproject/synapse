import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class OuModelTest(s_t_utils.SynTest):

    async def test_ou_simple(self):

        async with self.getTestCore() as core:

            # ou:naics
            t = core.model.type('ou:naics')
            norm, subs = await t.norm(541715)
            self.eq(norm, '541715')
            await self.asyncraises(s_exc.BadTypeValu, t.norm('newp'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(1000000))
            self.eq('10', (await t.norm('10'))[0])
            self.eq('100', (await t.norm('  100  '))[0])
            self.eq('1000', (await t.norm('1000'))[0])
            self.eq('10000', (await t.norm('10000'))[0])

            # ou:sic
            t = core.model.type('ou:sic')
            norm, subs = await t.norm('7999')
            self.eq(norm, '7999')
            norm, subs = await t.norm(9999)
            self.eq(norm, '9999')
            norm, subs = await t.norm('0111')
            self.eq(norm, '0111')

            await self.asyncraises(s_exc.BadTypeValu, t.norm(-1))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(0))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(111))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(10000))

            # ou:isic
            t = core.model.type('ou:isic')
            self.eq('C', (await t.norm('C'))[0])
            self.eq('C13', (await t.norm('C13'))[0])
            self.eq('C139', (await t.norm('C139'))[0])
            self.eq('C1393', (await t.norm('C1393'))[0])
            await self.asyncraises(s_exc.BadTypeValu, t.norm('C1'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('C12345'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm('newp'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(1000000))

            # ou:position / ou:org:subs
            orgiden = s_common.guid()
            contact = s_common.guid()
            position = s_common.guid()
            subpos = s_common.guid()

            opts = {'vars': {
                'orgiden': orgiden,
                'position': position,
                'subpos': subpos,
            }}

            nodes = await core.nodes('''
                [ ou:org=$orgiden :orgchart=$position ]
                -> ou:position
                [
                    :contact={[ entity:contact=39f8d9599cd663b00013bfedf69dcf53 ]}
                    :title=ceo :org=$orgiden
                ]
            ''', opts=opts)
            self.propeq(nodes[0], 'title', 'ceo')
            self.propeq(nodes[0], 'org', orgiden)
            self.eq(('entity:contact', '39f8d9599cd663b00013bfedf69dcf53'), nodes[0].get('contact'))

            nodes = await core.nodes('''
                ou:org=$orgiden
                -> ou:position
                [ :reports+=$subpos ]
                -> ou:position
            ''', opts=opts)
            self.eq(('ou:position', subpos), nodes[0].ndef)

            nodes = await core.nodes('''[
                ou:org=*
                    :id=VTX-0000
                    :name="The Vertex Project, LLC."
                    :names+="vertex"
                    :type=corp.llc
                    :logo=*
                    :phone="+15555555555"
                    :url=https://vertex.link
                    :lifespan=(2016, *)
                    :motto="Synapse or it didn't happen!"
                    :parent=*
                    :place={[ geo:place=* ]}
                    :place:loc=US.DE
                    :place:country={[ pol:country=* ]}
                    :place:country:code=us
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'ou:org')
            self.propeq(nodes[0], 'id', 'VTX-0000')
            self.propeq(nodes[0], 'name', 'the vertex project, llc.')
            self.propeq(nodes[0], 'names', ('vertex',))
            self.propeq(nodes[0], 'type', 'corp.llc.')
            self.propeq(nodes[0], 'phone', '15555555555')
            self.propeq(nodes[0], 'url', 'https://vertex.link')
            self.propeq(nodes[0], 'lifespan', (1451606400000000, 9223372036854775806, 18446744073709551614))
            self.nn(nodes[0].get('logo'))
            self.nn(nodes[0].get('parent'))
            self.propeq(nodes[0], 'motto', "Synapse or it didn't happen!")

            self.nn(nodes[0].get('place'))
            self.nn(nodes[0].get('place:country'))
            self.propeq(nodes[0], 'place:loc', 'us.de')

            self.len(1, await core.nodes('pol:country -> ou:org'))
            self.len(1, await core.nodes('ou:org -> ou:org:type:taxonomy'))
            self.len(1, await core.nodes('ou:org :motto -> lang:phrase'))
            # confirm ou:org is meta:havable...
            self.len(1, await core.nodes('[ entity:had=* :item={ou:org:id=VTX-0000} ]'))

            nodes = await core.nodes('ou:org:names*[=vertex]')
            self.len(1, nodes)

            nodes = await core.nodes('''[
                ou:orgnet=({"org": {"id": "VTX-0000"},
                            "net": ["192.168.1.1", "192.168.1.127"]})
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('org'))
            self.propeq(nodes[0], 'net', ((4, 3232235777), (4, 3232235903)))

            nodes = await core.nodes('''[
                ou:orgnet=({"org": {"id": "VTX-0000"},
                            "net": ["fd00::1", "fd00::127"]})
            ]''')
            self.len(1, nodes)
            minv = (6, 0xfd000000000000000000000000000001)
            maxv = (6, 0xfd000000000000000000000000000127)
            self.nn(nodes[0].get('org'))
            self.propeq(nodes[0], 'net', (minv, maxv))

            # ou:meeting
            nodes = await core.nodes('''[
                ou:meeting=39f8d9599cd663b00013bfedf69dcf53
                    :name="Working Lunch"
                    :period=(201604011200, 201604011300)
                    :place={[ geo:place=39f8d9599cd663b00013bfedf69dcf53 ]}
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:meeting', '39f8d9599cd663b00013bfedf69dcf53'))
            self.propeq(nodes[0], 'name', 'working lunch')
            self.propeq(nodes[0], 'period', (1459512000000000, 1459515600000000, 3600000000))
            self.propeq(nodes[0], 'place', '39f8d9599cd663b00013bfedf69dcf53')

            # ou:conference
            nodes = await core.nodes('''[
                ou:conference=39f8d9599cd663b00013bfedf69dcf53
                    :name="arrowcon 2018"
                    :name:base=arrowcon
                    :names=("arrow conference 2018", "arrcon18", "arrcon18")
                    :period=(20180301, 20180303)
                    :website=http://arrowcon.org/2018
                    :place=39f8d9599cd663b00013bfedf69dcf53
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:conference', '39f8d9599cd663b00013bfedf69dcf53'))
            self.propeq(nodes[0], 'name', 'arrowcon 2018')
            self.propeq(nodes[0], 'names', ('arrcon18', 'arrow conference 2018',))
            self.propeq(nodes[0], 'name:base', 'arrowcon')
            self.propeq(nodes[0], 'period', (1519862400000000, 1520035200000000, 172800000000))
            self.propeq(nodes[0], 'place', '39f8d9599cd663b00013bfedf69dcf53')
            self.propeq(nodes[0], 'website', 'http://arrowcon.org/2018')

            # confirm that multi-inheritance resolves template values correctly
            self.eq(core.model.prop('ou:conference:place:address').info['doc'],
                    'The postal address where the conference was located.')

            gutors = await core.nodes('[ ou:conference=({"name": "arrcon18"}) ]')
            self.eq(nodes[0].ndef, gutors[0].ndef)

            # ou:event
            nodes = await core.nodes('''[
                ou:event=39f8d9599cd663b00013bfedf69dcf53
                    :name='arrowcon 2018 dinner'
                    :desc='arrowcon dinner'
                    :period=(201803011900, 201803012200)
                    :parent=(ou:conference, 39f8d9599cd663b00013bfedf69dcf53)
                    :place=39f8d9599cd663b00013bfedf69dcf53
                    :website=http://arrowcon.org/2018/dinner
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:event', '39f8d9599cd663b00013bfedf69dcf53'))
            self.propeq(nodes[0], 'name', 'arrowcon 2018 dinner')
            self.propeq(nodes[0], 'desc', 'arrowcon dinner')
            self.propeq(nodes[0], 'parent', ('ou:conference', '39f8d9599cd663b00013bfedf69dcf53'))
            self.propeq(nodes[0], 'period', (1519930800000000, 1519941600000000, 10800000000))
            self.propeq(nodes[0], 'place', '39f8d9599cd663b00013bfedf69dcf53')
            self.propeq(nodes[0], 'website', 'http://arrowcon.org/2018/dinner')

            nodes = await core.nodes('''[
                ou:id=*
                    :value=(meta:id, Woot99)
                    :issuer={[ ou:org=* :name="ny dmv" ]}
                    :issuer:name="ny dmv"
                    :recipient={[ entity:contact=* :name=visi ]}
                    :type=us.state.dmv.driverslicense
                    :issued=20250525
                    :updated=20250525
                    :status=valid
            ]''')

            self.len(1, nodes)
            self.propeq(nodes[0], 'value', ('meta:id', 'Woot99'))
            self.propeq(nodes[0], 'issuer:name', 'ny dmv')
            self.propeq(nodes[0], 'status', 'valid.')
            self.propeq(nodes[0], 'type', 'us.state.dmv.driverslicense.')
            self.propeq(nodes[0], 'issued', 1748131200000000)
            self.propeq(nodes[0], 'updated', 1748131200000000)

            nodes = await core.nodes('''[
                ou:id:history=*
                    :id={ ou:id }
                    :updated=20250525
                    :status=suspended
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'updated', 1748131200000000)
            self.propeq(nodes[0], 'status', 'suspended.')
            self.len(1, await core.nodes('ou:id:history -> ou:id'))

            nodes = await core.nodes('[ ou:org=* :desc=hehe :dns:mx=(hehe.com, haha.com)]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'desc', 'hehe')

            opts = {'vars': {'iden': nodes[0].ndef[1]}}
            self.len(2, await core.nodes('ou:org=$iden :dns:mx -> inet:fqdn', opts=opts))

            nodes = await core.nodes('''[
                ou:preso=*
                    :name=syn101
                    :desc=squeee
                    :period=(202008081200, 202008081400)

                    :place=*
                    :place:loc=us.nv.lasvegas

                    :parent={ ou:conference }
                    :sponsors={[ entity:contact=* ]}
                    :organizers={[ entity:contact=* ]}
                    :presenters={[ entity:contact=* entity:contact=* ]}

                    :deck:file=*
                    :recording:file=*

                    :deck:url=http://vertex.link/syn101deck
                    :attendee:url=http://vertex.link/syn101live
                    :recording:url=http://vertex.link/syn101recording
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'syn101')
            self.propeq(nodes[0], 'desc', 'squeee')

            self.propeq(nodes[0], 'period', (1596888000000000, 1596895200000000, 7200000000))

            self.propeq(nodes[0], 'deck:url', 'http://vertex.link/syn101deck')
            self.propeq(nodes[0], 'attendee:url', 'http://vertex.link/syn101live')
            self.propeq(nodes[0], 'recording:url', 'http://vertex.link/syn101recording')

            self.nn(nodes[0].get('place'))
            self.nn(nodes[0].get('deck:file'))
            self.nn(nodes[0].get('recording:file'))

            self.propeq(nodes[0], 'place:loc', 'us.nv.lasvegas')

            self.len(1, await core.nodes(f'ou:preso -> ou:conference'))
            self.len(1, await core.nodes(f'ou:preso :sponsors -> entity:contact'))
            self.len(1, await core.nodes(f'ou:preso :organizers -> entity:contact'))
            self.len(2, await core.nodes(f'ou:preso :presenters -> entity:contact'))

            nodes = await core.nodes('''[
                ou:contest=*
                    :name="defcon ctf 2020"
                    :type=cyber.ctf
                    :name:base="defcon ctf"
                    :period=(20200808, 20200811)
                    :website=http://vertex.link/contest

                    :place=*
                    :place:latlong=(20, 30)
                    :place:loc=us.nv.lasvegas

                    :parent={ ou:conference }
                    :organizers={[ entity:contact=* ]}
                    :sponsors={[ entity:contact=* ]}

            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'defcon ctf 2020')
            self.propeq(nodes[0], 'type', 'cyber.ctf.')
            self.propeq(nodes[0], 'name:base', 'defcon ctf')

            self.propeq(nodes[0], 'period', (1596844800000000, 1597104000000000, 259200000000))

            self.propeq(nodes[0], 'website', 'http://vertex.link/contest')

            self.eq((20, 30), nodes[0].get('place:latlong'))
            self.propeq(nodes[0], 'place:loc', 'us.nv.lasvegas')

            self.len(1, await core.nodes(f'ou:contest -> ou:conference'))
            self.len(1, await core.nodes(f'ou:contest :parent -> ou:conference'))
            self.len(1, await core.nodes(f'ou:contest :sponsors -> entity:contact'))
            self.len(1, await core.nodes(f'ou:contest :organizers -> entity:contact'))

            nodes = await core.nodes('''[
                ou:contest:result=(*, *)
                    :rank=1
                    :score=20
                    :url=https://vertex.link/woot
                    :period=(20250101, 20250102)
                    :contest={ou:contest}
                    :participant={[ entity:contact=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('contest'))
            self.nn(nodes[0].get('participant'))
            self.propeq(nodes[0], 'url', 'https://vertex.link/woot')
            self.propeq(nodes[0], 'rank', 1)
            self.propeq(nodes[0], 'score', 20)
            self.eq((1735689600000000, 1735776000000000, 86400000000), nodes[0].get('period'))
            self.len(1, await core.nodes('ou:contest:result -> ou:contest'))
            self.len(1, await core.nodes('ou:contest:result -> entity:contact'))

            opts = {'vars': {'ind': s_common.guid()}}
            nodes = await core.nodes('[ ou:org=* :industries=($ind, $ind) ]', opts=opts)
            self.len(1, nodes)
            self.len(1, nodes[0].get('industries'))

            nodes = await core.nodes('''
                [ ou:asset=*
                    :id=V-31337
                    :name="visi laptop"
                    :type=host.laptop
                    :priority=highest
                    :priority:confidentiality=highest
                    :priority:integrity=highest
                    :priority:availability=highest
                    :node = (it:host, *)
                    :period=(2016, ?)
                    :status=deployed
                    :org={[ ou:org=* :name=vertex ]}
                    :owner={[ entity:contact=* :name=foo ]}
                    :operator={[ entity:contact=* :name=bar ]}
                ]''')
            self.len(1, nodes)
            self.eq((1451606400000000, 9223372036854775807, 0xffffffffffffffff), nodes[0].get('period'))
            self.propeq(nodes[0], 'name', 'visi laptop')
            self.propeq(nodes[0], 'type', 'host.laptop.')
            self.propeq(nodes[0], 'status', 'deployed.')
            self.propeq(nodes[0], 'priority', 50)
            self.propeq(nodes[0], 'priority:confidentiality', 50)
            self.propeq(nodes[0], 'priority:integrity', 50)
            self.propeq(nodes[0], 'priority:availability', 50)

            self.len(1, await core.nodes('ou:asset -> ou:asset:type:taxonomy'))
            self.len(1, await core.nodes('ou:asset :node -> it:host'))
            self.len(1, await core.nodes('ou:asset :org -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('ou:asset :owner -> entity:contact +:name=foo '))
            self.len(1, await core.nodes('ou:asset :operator -> entity:contact +:name=bar '))

            visi = await core.auth.addUser('visi')

            nodes = await core.nodes('''
                [ ou:enacted=*
                    :id=V-99
                    :project={[ proj:project=* ]}
                    :status=10
                    :priority=highest
                    :created=20241018
                    :updated=20241018
                    :due=20241018
                    :completed=20241018
                    :creator={[ syn:user=root ]}
                    :assignee={[ syn:user=visi ]}
                    :scope=(ou:team, *)

                    <(shows)+ {[ meta:rule=* ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'V-99')
            self.propeq(nodes[0], 'status', 10)
            self.propeq(nodes[0], 'priority', 50)

            self.propeq(nodes[0], 'due', 1729209600000000)
            self.propeq(nodes[0], 'created', 1729209600000000)
            self.propeq(nodes[0], 'updated', 1729209600000000)
            self.propeq(nodes[0], 'completed', 1729209600000000)

            self.propeq(nodes[0], 'creator', ('syn:user', core.auth.rootuser.iden))
            self.propeq(nodes[0], 'assignee', ('syn:user', visi.iden))

            self.nn(nodes[0].get('scope'))

            self.len(1, await core.nodes('ou:enacted -> proj:project'))
            self.len(1, await core.nodes('ou:enacted :scope -> ou:team'))
            self.len(1, await core.nodes('ou:enacted <(shows)- meta:rule'))

            nodes = await core.nodes('''
                [ ou:candidate=*
                    :org={ ou:org:name=vertex | limit 1 }
                    :contact={ entity:contact:name=visi | limit 1 }
                    :intro="    Hi there!"
                    :submitted=20241104
                    :method=referral.employee
                    :resume=*
                    :opening=*
                    :agent={[ entity:contact=* :name=agent ]}
                    :recruiter={[ entity:contact=* :name=recruiter ]}
                    :attachments={[ file:attachment=* :path=questions.pdf ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'intro', 'Hi there!')
            self.propeq(nodes[0], 'submitted', 1730678400000000)
            self.propeq(nodes[0], 'method', 'referral.employee.')
            self.len(1, await core.nodes('ou:candidate :org -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('ou:candidate :agent -> entity:contact +:name=agent'))
            self.len(1, await core.nodes('ou:candidate :contact -> entity:contact +:name=visi'))
            self.len(1, await core.nodes('ou:candidate :recruiter -> entity:contact +:name=recruiter'))

            self.len(1, await core.nodes('ou:candidate :method -> ou:candidate:method:taxonomy'))
            self.len(1, await core.nodes('ou:candidate :attachments -> file:attachment'))

            nodes = await core.nodes('''
                [ ou:candidate:referral=*
                    :referrer={ entity:contact:name=visi | limit 1 }
                    :candidate={ ou:candidate }
                    :text="def a great candidate"
                    :submitted=20241104
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('referrer'))
            self.nn(nodes[0].get('candidate'))
            self.propeq(nodes[0], 'text', 'def a great candidate')
            self.propeq(nodes[0], 'submitted', 1730678400000000)

    async def test_ou_code_prefixes(self):
        guid0 = s_common.guid()
        guid1 = s_common.guid()
        guid2 = s_common.guid()
        guid3 = s_common.guid()
        omap = {
            guid0: {'naics': '221121',
                    'sic': '0111'},
            guid1: {'naics': '221122',
                    'sic': '0112'},
            guid2: {'naics': '221113',
                    'sic': '2833'},
            guid3: {'naics': '221320',
                    'sic': '0134'}
        }
        async with self.getTestCore() as core:
            for g, props in omap.items():
                nodes = await core.nodes('[ou:industry=* :naics+=$p.naics :sic+=$p.sic]',
                                         opts={'vars': {'valu': g, 'p': props}})
                self.len(1, nodes)
            self.len(3, await core.nodes('ou:industry:sic*[^=01]'))
            self.len(2, await core.nodes('ou:industry:sic*[^=011]'))
            self.len(4, await core.nodes('ou:industry:naics*[^=22]'))
            self.len(4, await core.nodes('ou:industry:naics*[^=221]'))
            self.len(3, await core.nodes('ou:industry:naics*[^=2211]'))
            self.len(2, await core.nodes('ou:industry:naics*[^=22112]'))

    async def test_ou_industry(self):

        async with self.getTestCore() as core:
            q = '''
            [ ou:industry=*
                :name=" Foo Bar "
                :names=(baz, faz)
                :naics=(11111,22222)
                :sic="1234,5678"
                :isic=C1393
                :desc="Moldy cheese"
                :reporter={[ ou:org=* :name=vertex ]}
                :reporter:name=vertex
            ] '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            self.nn(nodes[0].get('reporter'))
            self.propeq(nodes[0], 'name', 'foo bar')
            self.propeq(nodes[0], 'reporter:name', 'vertex')
            self.sorteq(('1234', '5678'), nodes[0].get('sic'))
            self.sorteq(('11111', '22222'), nodes[0].get('naics'))
            self.sorteq(('C1393', ), nodes[0].get('isic'))
            self.propeq(nodes[0], 'desc', 'Moldy cheese')

            self.len(1, await core.nodes('ou:industry :reporter -> ou:org'))

            self.len(1, nodes := await core.nodes('[ ou:industry=({"name": "faz"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

    async def test_ou_opening(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:opening=*
                    :org = {[ ou:org=* :name=vertex ]}
                    :org:name = vertex
                    :org:fqdn = vertex.link
                    :period = (20210807, 2022)
                    :postings = {[ inet:url=https://vertex.link ]}
                    :contact = {[ entity:contact=* :email=visi@vertex.link ]}
                    :loc = us.va
                    :job:type = it.dev
                    :employment:type = fulltime.salary
                    :title = PyDev
                    :remote = (1)
                    :pay:min=20
                    :pay:max=22
                    :pay:currency=BTC
                    :pay:pertime=1:00:00
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'org:name', 'vertex')
            self.propeq(nodes[0], 'org:fqdn', 'vertex.link')
            self.propeq(nodes[0], 'title', 'pydev')
            self.propeq(nodes[0], 'remote', 1)
            self.propeq(nodes[0], 'employment:type', 'fulltime.salary.')
            self.propeq(nodes[0], 'period', (1628294400000000, 1640995200000000, 12700800000000))
            self.propeq(nodes[0], 'postings', ('https://vertex.link',))

            self.propeq(nodes[0], 'pay:min', '20')
            self.propeq(nodes[0], 'pay:max', '22')
            self.propeq(nodes[0], 'pay:currency', 'btc')
            self.propeq(nodes[0], 'pay:pertime', 3600000000)

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ou:opening -> ou:org'))
            self.len(1, await core.nodes('ou:opening -> entity:name'))
            self.len(1, await core.nodes('ou:opening -> inet:url'))
            self.len(1, await core.nodes('ou:opening -> inet:fqdn'))
            self.len(1, await core.nodes('ou:opening -> entity:title'))
            self.len(1, await core.nodes('ou:opening -> ou:employment:type:taxonomy'))
            self.len(1, await core.nodes('ou:opening :contact -> entity:contact'))

    async def test_ou_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:vitals=*
                    :time = 20210731
                    :org = *
                    :org:name = WootCorp
                    :org:fqdn = wootwoot.com
                    :currency = USD
                    :costs = 200
                    :budget = 300
                    :revenue = 500
                    :profit = 300
                    :valuation = 1000000000
                    :shares = 10
                    :population = 13
                    :delta:costs = "-30"
                    :delta:revenue = 100
                    :delta:profit = 200
                    :delta:valuation = 999999999999
                    :delta:population = 3
                ]
            ''')
            self.nn(nodes[0].get('org'))
            self.propeq(nodes[0], 'time', 1627689600000000)
            self.propeq(nodes[0], 'org:name', 'wootcorp')
            self.propeq(nodes[0], 'org:fqdn', 'wootwoot.com')
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'costs', '200')
            self.propeq(nodes[0], 'budget', '300')
            self.propeq(nodes[0], 'revenue', '500')
            self.propeq(nodes[0], 'profit', '300')
            self.propeq(nodes[0], 'valuation', '1000000000')
            self.propeq(nodes[0], 'shares', 10)
            self.propeq(nodes[0], 'population', 13)
            self.propeq(nodes[0], 'delta:costs', '-30')
            self.propeq(nodes[0], 'delta:revenue', '100')
            self.propeq(nodes[0], 'delta:profit', '200')
            self.propeq(nodes[0], 'delta:valuation', '999999999999')
            self.propeq(nodes[0], 'delta:population', 3)

            self.len(1, await core.nodes('ou:vitals -> ou:org'))
            self.len(1, await core.nodes('ou:vitals -> inet:fqdn'))
            self.len(1, await core.nodes('ou:vitals -> entity:name'))

            self.len(1, await core.nodes('ou:org [ :vitals=* ] :vitals -> ou:vitals'))
