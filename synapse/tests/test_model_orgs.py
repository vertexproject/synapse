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
            self.eq('ceo', nodes[0].get('title'))
            self.eq(orgiden, nodes[0].get('org'))
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
            self.eq(nodes[0].get('id'), 'VTX-0000')
            self.eq(nodes[0].get('name'), 'the vertex project, llc.')
            self.eq(nodes[0].get('names'), ('vertex',))
            self.eq(nodes[0].get('type'), 'corp.llc.')
            self.eq(nodes[0].get('phone'), '15555555555')
            self.eq(nodes[0].get('url'), 'https://vertex.link')
            self.eq(nodes[0].get('lifespan'), (1451606400000000, 9223372036854775806, 18446744073709551614))
            self.nn(nodes[0].get('logo'))
            self.nn(nodes[0].get('parent'))
            self.eq(nodes[0].get('motto'), "Synapse or it didn't happen!")

            self.nn(nodes[0].get('place'))
            self.nn(nodes[0].get('place:country'))
            self.eq(nodes[0].get('place:loc'), 'us.de')

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
            self.eq(nodes[0].get('net'), ((4, 3232235777), (4, 3232235903)))

            nodes = await core.nodes('''[
                ou:orgnet=({"org": {"id": "VTX-0000"},
                            "net": ["fd00::1", "fd00::127"]})
            ]''')
            self.len(1, nodes)
            minv = (6, 0xfd000000000000000000000000000001)
            maxv = (6, 0xfd000000000000000000000000000127)
            self.nn(nodes[0].get('org'))
            self.eq(nodes[0].get('net'), (minv, maxv))

            # ou:meeting
            nodes = await core.nodes('''[
                ou:meeting=39f8d9599cd663b00013bfedf69dcf53
                    :name="Working Lunch"
                    :period=(201604011200, 201604011300)
                    :place={[ geo:place=39f8d9599cd663b00013bfedf69dcf53 ]}
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:meeting', '39f8d9599cd663b00013bfedf69dcf53'))
            self.eq(nodes[0].get('name'), 'working lunch')
            self.eq(nodes[0].get('period'), (1459512000000000, 1459515600000000, 3600000000))
            self.eq(nodes[0].get('place'), '39f8d9599cd663b00013bfedf69dcf53')

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
            self.eq(nodes[0].get('name'), 'arrowcon 2018')
            self.eq(nodes[0].get('names'), ('arrcon18', 'arrow conference 2018',))
            self.eq(nodes[0].get('name:base'), 'arrowcon')
            self.eq(nodes[0].get('period'), (1519862400000000, 1520035200000000, 172800000000))
            self.eq(nodes[0].get('place'), '39f8d9599cd663b00013bfedf69dcf53')
            self.eq(nodes[0].get('website'), 'http://arrowcon.org/2018')

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
            self.eq(nodes[0].get('name'), 'arrowcon 2018 dinner')
            self.eq(nodes[0].get('desc'), 'arrowcon dinner')
            self.eq(nodes[0].get('parent'), ('ou:conference', '39f8d9599cd663b00013bfedf69dcf53'))
            self.eq(nodes[0].get('period'), (1519930800000000, 1519941600000000, 10800000000))
            self.eq(nodes[0].get('place'), '39f8d9599cd663b00013bfedf69dcf53')
            self.eq(nodes[0].get('website'), 'http://arrowcon.org/2018/dinner')

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
            self.eq(nodes[0].get('value'), ('meta:id', 'Woot99'))
            self.eq(nodes[0].get('issuer:name'), 'ny dmv')
            self.eq(nodes[0].get('status'), 'valid.')
            self.eq(nodes[0].get('type'), 'us.state.dmv.driverslicense.')
            self.eq(nodes[0].get('issued'), 1748131200000000)
            self.eq(nodes[0].get('updated'), 1748131200000000)

            nodes = await core.nodes('''[
                ou:id:history=*
                    :id={ ou:id }
                    :updated=20250525
                    :status=suspended
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('updated'), 1748131200000000)
            self.eq(nodes[0].get('status'), 'suspended.')
            self.len(1, await core.nodes('ou:id:history -> ou:id'))

            nodes = await core.nodes('[ ou:org=* :desc=hehe :dns:mx=(hehe.com, haha.com)]')
            self.len(1, nodes)
            self.eq('hehe', nodes[0].get('desc'))

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
            self.eq('syn101', nodes[0].get('name'))
            self.eq('squeee', nodes[0].get('desc'))

            self.eq(nodes[0].get('period'), (1596888000000000, 1596895200000000, 7200000000))

            self.eq('http://vertex.link/syn101deck', nodes[0].get('deck:url'))
            self.eq('http://vertex.link/syn101live', nodes[0].get('attendee:url'))
            self.eq('http://vertex.link/syn101recording', nodes[0].get('recording:url'))

            self.nn(nodes[0].get('place'))
            self.nn(nodes[0].get('deck:file'))
            self.nn(nodes[0].get('recording:file'))

            self.eq(nodes[0].get('place:loc'), 'us.nv.lasvegas')

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
            self.eq('defcon ctf 2020', nodes[0].get('name'))
            self.eq('cyber.ctf.', nodes[0].get('type'))
            self.eq('defcon ctf', nodes[0].get('name:base'))

            self.eq(nodes[0].get('period'), (1596844800000000, 1597104000000000, 259200000000))

            self.eq('http://vertex.link/contest', nodes[0].get('website'))

            self.eq((20, 30), nodes[0].get('place:latlong'))
            self.eq('us.nv.lasvegas', nodes[0].get('place:loc'))

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
            self.eq(nodes[0].get('url'), 'https://vertex.link/woot')
            self.eq(1, nodes[0].get('rank'))
            self.eq(20, nodes[0].get('score'))
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
            self.eq('visi laptop', nodes[0].get('name'))
            self.eq('host.laptop.', nodes[0].get('type'))
            self.eq('deployed.', nodes[0].get('status'))
            self.eq(50, nodes[0].get('priority'))
            self.eq(50, nodes[0].get('priority:confidentiality'))
            self.eq(50, nodes[0].get('priority:integrity'))
            self.eq(50, nodes[0].get('priority:availability'))

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
            self.eq('V-99', nodes[0].get('id'))
            self.eq(10, nodes[0].get('status'))
            self.eq(50, nodes[0].get('priority'))

            self.eq(1729209600000000, nodes[0].get('due'))
            self.eq(1729209600000000, nodes[0].get('created'))
            self.eq(1729209600000000, nodes[0].get('updated'))
            self.eq(1729209600000000, nodes[0].get('completed'))

            self.eq(nodes[0].get('creator'), ('syn:user', core.auth.rootuser.iden))
            self.eq(nodes[0].get('assignee'), ('syn:user', visi.iden))

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
            self.eq('Hi there!', nodes[0].get('intro'))
            self.eq(1730678400000000, nodes[0].get('submitted'))
            self.eq('referral.employee.', nodes[0].get('method'))
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
            self.eq(nodes[0].get('text'), 'def a great candidate')
            self.eq(1730678400000000, nodes[0].get('submitted'))

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
            self.eq('foo bar', nodes[0].get('name'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.sorteq(('1234', '5678'), nodes[0].get('sic'))
            self.sorteq(('11111', '22222'), nodes[0].get('naics'))
            self.sorteq(('C1393', ), nodes[0].get('isic'))
            self.eq('Moldy cheese', nodes[0].get('desc'))

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
            self.eq(nodes[0].get('org:name'), 'vertex')
            self.eq(nodes[0].get('org:fqdn'), 'vertex.link')
            self.eq(nodes[0].get('title'), 'pydev')
            self.eq(nodes[0].get('remote'), 1)
            self.eq(nodes[0].get('employment:type'), 'fulltime.salary.')
            self.eq(nodes[0].get('period'), (1628294400000000, 1640995200000000, 12700800000000))
            self.eq(nodes[0].get('postings'), ('https://vertex.link',))

            self.eq(nodes[0].get('pay:min'), '20')
            self.eq(nodes[0].get('pay:max'), '22')
            self.eq(nodes[0].get('pay:currency'), 'btc')
            self.eq(nodes[0].get('pay:pertime'), 3600000000)

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
            self.eq(nodes[0].get('time'), 1627689600000000)
            self.eq(nodes[0].get('org:name'), 'wootcorp')
            self.eq(nodes[0].get('org:fqdn'), 'wootwoot.com')
            self.eq(nodes[0].get('currency'), 'usd')
            self.eq(nodes[0].get('costs'), '200')
            self.eq(nodes[0].get('budget'), '300')
            self.eq(nodes[0].get('revenue'), '500')
            self.eq(nodes[0].get('profit'), '300')
            self.eq(nodes[0].get('valuation'), '1000000000')
            self.eq(nodes[0].get('shares'), 10)
            self.eq(nodes[0].get('population'), 13)
            self.eq(nodes[0].get('delta:costs'), '-30')
            self.eq(nodes[0].get('delta:revenue'), '100')
            self.eq(nodes[0].get('delta:profit'), '200')
            self.eq(nodes[0].get('delta:valuation'), '999999999999')
            self.eq(nodes[0].get('delta:population'), 3)

            self.len(1, await core.nodes('ou:vitals -> ou:org'))
            self.len(1, await core.nodes('ou:vitals -> inet:fqdn'))
            self.len(1, await core.nodes('ou:vitals -> entity:name'))

            self.len(1, await core.nodes('ou:org [ :vitals=* ] :vitals -> ou:vitals'))
