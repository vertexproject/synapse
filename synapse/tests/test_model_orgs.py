import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class OuModelTest(s_t_utils.SynTest):

    async def test_ou_simple(self):

        async with self.getTestCore() as core:

            goal = s_common.guid()
            org0 = s_common.guid()
            camp = s_common.guid()
            acto = s_common.guid()
            teqs = (s_common.guid(), s_common.guid())

            nodes = await core.nodes('''
                [ ou:technique=*
                    :id=Foo
                    :name=Woot
                    :type=lol.woot
                    :desc=Hehe
                    :tag=woot.woot
                    :sophistication=high
                    :source=$lib.gen.orgByName(vertex)
                    :source:name=vertex
                ]
            ''')
            self.len(1, nodes)
            self.nn('source')
            self.eq('woot', nodes[0].get('name'))
            self.eq('Hehe', nodes[0].get('desc'))
            self.eq('lol.woot.', nodes[0].get('type'))
            self.eq('woot.woot', nodes[0].get('tag'))
            self.eq('Foo', nodes[0].get('id'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('vertex', nodes[0].get('source:name'))
            self.len(1, await core.nodes('ou:technique -> syn:tag'))
            self.len(1, await core.nodes('ou:technique -> ou:technique:type:taxonomy'))
            self.len(1, await core.nodes('ou:technique :source -> ou:org'))

            props = {
                'name': 'MyGoal',
                'names': ['Foo Goal', 'Bar Goal', 'Bar Goal'],
                'type': 'foo.bar',
                'desc': 'MyDesc',
            }
            q = '[(ou:goal=$valu :name=$p.name :names=$p.names :type=$p.type :desc=$p.desc)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': goal, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ou:goal', goal))
            self.eq(node.get('name'), 'mygoal')
            self.eq(node.get('names'), ('bar goal', 'foo goal'))
            self.eq(node.get('type'), 'foo.bar.')
            self.eq(node.get('desc'), 'MyDesc')

            self.len(1, nodes := await core.nodes('[ ou:goal=({"name": "foo goal"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('''
                [ ou:campaign=*
                    :id=Foo
                    :type=MyType
                    :name=MyName
                    :names=(Foo, Bar)
                    :slogan="For The People"
                    :desc=MyDesc
                    :success=1
                    :sophistication=high
                    :tag=cno.camp.31337
                    :source={[ ou:org=({"name": "vertex"}) ]}
                    :source:name=vertex
                    :goal={[ ou:goal=({"name": "foo goal"}) ]}
                    :goals={[
                        ou:goal=({"name": "alt00 goal"})
                        ou:goal=({"name": "alt01 goal"})
                    ]}
                    :actor={[ entity:contact=* ]}
                    :actors={[ entity:contact=* ]}
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
            self.nn(nodes[0].get('source'))
            self.eq(nodes[0].get('source:name'), 'vertex')
            self.eq(nodes[0].get('slogan'), 'For The People')
            self.len(3, await core.nodes('ou:campaign -> ou:goal'))

            self.len(1, nodes01 := await core.nodes('''
                $goal = { ou:goal:name="alt00 goal" }
                [ ou:campaign=({"name": "foo", "goal": $goal}) ]
            '''))
            self.eq(nodes[0].ndef, nodes01[0].ndef)

            self.len(1, await core.nodes(f'ou:campaign:id=Foo :slogan -> lang:phrase'))

            # ou:naics
            t = core.model.type('ou:naics')
            norm, subs = t.norm(541715)
            self.eq(norm, '541715')
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')
            self.raises(s_exc.BadTypeValu, t.norm, '1')
            self.raises(s_exc.BadTypeValu, t.norm, 1000000)
            self.eq('10', t.norm('10')[0])
            self.eq('100', t.norm('  100  ')[0])
            self.eq('1000', t.norm('1000')[0])
            self.eq('10000', t.norm('10000')[0])

            # ou:sic
            t = core.model.type('ou:sic')
            norm, subs = t.norm('7999')
            self.eq(norm, '7999')
            norm, subs = t.norm(9999)
            self.eq(norm, '9999')
            norm, subs = t.norm('0111')
            self.eq(norm, '0111')

            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.raises(s_exc.BadTypeValu, t.norm, 0)
            self.raises(s_exc.BadTypeValu, t.norm, 111)
            self.raises(s_exc.BadTypeValu, t.norm, 10000)

            # ou:isic
            t = core.model.type('ou:isic')
            self.eq('C', t.norm('C')[0])
            self.eq('C13', t.norm('C13')[0])
            self.eq('C139', t.norm('C139')[0])
            self.eq('C1393', t.norm('C1393')[0])
            self.raises(s_exc.BadTypeValu, t.norm, 'C1')
            self.raises(s_exc.BadTypeValu, t.norm, 'C12345')
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')
            self.raises(s_exc.BadTypeValu, t.norm, 1000000)

            # ou:position / ou:org:subs
            orgiden = s_common.guid()
            contact = s_common.guid()
            position = s_common.guid()
            subpos = s_common.guid()
            suborg = s_common.guid()

            opts = {'vars': {
                'orgiden': orgiden,
                'position': position,
                'subpos': subpos,
                'suborg': suborg,
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

            # nodes = await core.nodes('''
            #     ou:org=$orgiden
            #     [ :subs+=$suborg ]
            #     -> ou:org
            # ''', opts=opts)
            # self.eq(('ou:org', suborg), nodes[0].ndef)

            guid0 = s_common.guid()
            name = '\u21f1\u21f2 Inc.'
            normname = '\u21f1\u21f2 inc.'
            altnames = ('altarrowname', 'otheraltarrow',)
            props = {
                'loc': 'US.CA',
                'name': name,
                'type': 'corp',
                'names': altnames,
                'logo': '*',
                'phone': '+15555555555',
                'url': 'http://arrowinc.link',
                'founded': '2015',
                'dissolved': '2019',
                'goals': (goal,),
            }
            q = '''[(ou:org=$valu :place:loc=$p.loc :name=$p.name :type=$p.type :names=$p.names
                :logo=$p.logo :phone=$p.phone :url=$p.url
                :lifespan=($p.founded, $p.dissolved)
                :goals=$p.goals
                :id=Foo :motto="DONT BE EVIL"
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid0, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ou:org', guid0))
            self.eq(node.get('place:loc'), 'us.ca')
            self.eq(node.get('type'), 'corp.')
            self.eq(node.get('name'), normname)
            self.eq(node.get('names'), altnames)
            self.eq(node.get('phone'), '15555555555')
            self.eq(node.get('url'), 'http://arrowinc.link')
            self.eq(node.get('lifespan'), (1420070400000000, 1546300800000000))
            self.eq(node.get('goals'), (goal,))
            self.eq(node.get('id'), 'Foo')
            self.nn(node.get('logo'))
            self.eq('DONT BE EVIL', node.get('motto'))

            await core.nodes('ou:org:url=http://arrowinc.link [ :place:country={ gen.pol.country ua } :place:country:code=ua ]')
            self.len(1, await core.nodes('ou:org:place:country:code=ua'))
            self.len(1, await core.nodes('pol:country:iso2=ua -> ou:org'))
            self.len(1, await core.nodes('ou:org -> ou:org:type:taxonomy'))
            self.len(1, await core.nodes('ou:org :motto -> lang:phrase'))

            nodes = await core.nodes('ou:org:names*[=otheraltarrow]')
            self.len(1, nodes)

            opts = {'vars': {'name': name}}
            nodes = await core.nodes('ou:org:names*[=$name]', opts=opts)
            self.len(0, nodes)  # primary ou:org:name is not in ou:org:names

            opts = {'vars': {'org': guid0, 'net': ('192.168.1.1', '192.168.1.127')}}
            nodes = await core.nodes('[ou:orgnet=({"org": $org, "net": $net})]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('org'), guid0)
            self.eq(node.get('net'), ((4, 3232235777), (4, 3232235903)))

            opts = {'vars': {'org': guid0, 'net': ('fd00::1', 'fd00::127')}}
            nodes = await core.nodes('[ou:orgnet=({"org": $org, "net": $net})]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            minv = (6, 0xfd000000000000000000000000000001)
            maxv = (6, 0xfd000000000000000000000000000127)
            self.eq(node.get('net'), (minv, maxv))
            self.eq(node.get('org'), guid0)

            # ou:meet
            nodes = await core.nodes('''[
                ou:meet=39f8d9599cd663b00013bfedf69dcf53
                    :name="Working Lunch"
                    :period=(201604011200, 201604011300)
                    :place={[ geo:place=39f8d9599cd663b00013bfedf69dcf53 ]}
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:meet', '39f8d9599cd663b00013bfedf69dcf53'))
            self.eq(nodes[0].get('name'), 'working lunch')
            self.eq(nodes[0].get('period'), (1459512000000000, 1459515600000000))
            self.eq(nodes[0].get('place'), '39f8d9599cd663b00013bfedf69dcf53')

            # ou:conference
            nodes = await core.nodes('''[
                ou:conference=39f8d9599cd663b00013bfedf69dcf53
                    :org=39f8d9599cd663b00013bfedf69dcf53
                    :name="arrowcon 2018"
                    :names=("arrow conference 2018", "arrcon18", "arrcon18")
                    :family=arrowcon
                    :period=(20180301, 20180303)
                    :website=http://arrowcon.org/2018
                    :place=39f8d9599cd663b00013bfedf69dcf53
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('ou:conference', '39f8d9599cd663b00013bfedf69dcf53'))
            self.eq(nodes[0].get('name'), 'arrowcon 2018')
            self.eq(nodes[0].get('names'), ('arrcon18', 'arrow conference 2018',))
            self.eq(nodes[0].get('family'), 'arrowcon')
            self.eq(nodes[0].get('org'), '39f8d9599cd663b00013bfedf69dcf53')
            self.eq(nodes[0].get('period'), (1519862400000000, 1520035200000000))
            self.eq(nodes[0].get('place'), '39f8d9599cd663b00013bfedf69dcf53')
            self.eq(nodes[0].get('website'), 'http://arrowcon.org/2018')

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
            self.eq(nodes[0].get('period'), (1519930800000000, 1519941600000000))
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
                ou:id:update=*
                    :id={ ou:id }
                    :updated=20250525
                    :status=suspended
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].get('updated'), 1748131200000000)
            self.eq(nodes[0].get('status'), 'suspended.')
            self.len(1, await core.nodes('ou:id:update -> ou:id'))

            nodes = await core.nodes('[ ou:org=* :desc=hehe :dns:mx=(hehe.com, haha.com)]')
            self.len(1, nodes)
            self.eq('hehe', nodes[0].get('desc'))

            opts = {'vars': {'iden': nodes[0].ndef[1]}}
            self.len(2, await core.nodes('ou:org=$iden :dns:mx -> inet:fqdn', opts=opts))

            nodes = await core.nodes('''[
                ou:attendee=*
                    :person={[ entity:contact=* ]}
                    :period=(201202,201203)
                    :event={ ou:event }
                    :roles+=staff
                    :roles+=STAFF
            ]''')
            self.len(1, nodes)
            self.eq(('staff',), nodes[0].get('roles'))
            self.eq(nodes[0].get('period'), (1328054400000000, 1330560000000000))

            self.len(1, await core.nodes('ou:attendee -> entity:contact'))

            self.len(1, await core.nodes('ou:attendee -> ou:event'))
            self.len(1, await core.nodes('ou:attendee :event -> ou:event'))

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

            self.eq(nodes[0].get('period'), (1596888000000000, 1596895200000000))

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
                    :family="defcon ctf"
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
            self.eq('defcon ctf', nodes[0].get('family'))

            self.eq(nodes[0].get('period'), (1596844800000000, 1597104000000000))

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
                    :period=(20250101, 20250102)
                    :contest={ou:contest}
                    :participant={[ entity:contact=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('contest'))
            self.nn(nodes[0].get('participant'))
            self.eq(1, nodes[0].get('rank'))
            self.eq(20, nodes[0].get('score'))
            self.eq((1735689600000000, 1735776000000000), nodes[0].get('period'))
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
            self.eq((1451606400000000, 9223372036854775807), nodes[0].get('period'))
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
                    :creator=root
                    :assignee=visi
                    :scope=(ou:team, *)
                    :ext:creator={[ entity:contact=* :name=root ]}
                    :ext:assignee={[ entity:contact=* :name=visi ]}
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

            self.eq(visi.iden, nodes[0].get('assignee'))
            self.eq(core.auth.rootuser.iden, nodes[0].get('creator'))

            self.nn(nodes[0].get('scope'))
            self.nn(nodes[0].get('ext:creator'))
            self.nn(nodes[0].get('ext:assignee'))

            self.len(1, await core.nodes('ou:enacted -> proj:project'))
            self.len(1, await core.nodes('ou:enacted :scope -> ou:team'))
            self.len(1, await core.nodes('ou:enacted :ext:creator -> entity:contact +:name=root'))
            self.len(1, await core.nodes('ou:enacted :ext:assignee -> entity:contact +:name=visi'))

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
                    :attachments={[ file:attachment=* :name=questions.pdf ]}
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

    async def test_ou_contract(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
            [ ou:contract=*
                :title="Fullbright Scholarship"
                :type=foo.bar
                :sponsor={[ ou:org=({"name": "vertex"}) ]}
                :currency=USD
                :award:price=20.00
                :budget:price=21.50
                :parties={[ entity:contact=* entity:contact=* ]}
                :document={[ file:bytes=* ]}
                :signed=202001
                :begins=202002
                :expires=202003
                :completed=202004
                :terminated=202005
                :requirements={
                    [( ou:goal=* :name="world peace" )]
                    [( ou:goal=* :name="whirled peas" )]
                }
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('sponsor'))
            self.eq('Fullbright Scholarship', nodes[0].get('title'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('20', nodes[0].get('award:price'))
            self.eq('21.5', nodes[0].get('budget:price'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq(1577836800000000, nodes[0].get('signed'))
            self.eq(1580515200000000, nodes[0].get('begins'))
            self.eq(1583020800000000, nodes[0].get('expires'))
            self.eq(1585699200000000, nodes[0].get('completed'))
            self.eq(1588291200000000, nodes[0].get('terminated'))
            self.len(2, nodes[0].get('parties'))
            self.len(2, nodes[0].get('requirements'))

            nodes = await core.nodes('ou:contract -> ou:contract:type:taxonomy')
            self.len(1, nodes)
            self.eq(1, nodes[0].get('depth'))
            self.eq('bar', nodes[0].get('base'))
            self.eq('foo.', nodes[0].get('parent'))

            nodes = await core.nodes('ou:contract:type:taxonomy')
            self.len(2, nodes)
            self.eq(0, nodes[0].get('depth'))
            self.eq('foo', nodes[0].get('base'))
            self.none(nodes[0].get('parent'))

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
                :source={[ ou:org=* :name=vertex ]}
                :source:name=vertex
            ] '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            self.nn(nodes[0].get('source'))
            self.eq('foo bar', nodes[0].get('name'))
            self.eq('vertex', nodes[0].get('source:name'))
            self.sorteq(('1234', '5678'), nodes[0].get('sic'))
            self.sorteq(('11111', '22222'), nodes[0].get('naics'))
            self.sorteq(('C1393', ), nodes[0].get('isic'))
            self.eq('Moldy cheese', nodes[0].get('desc'))

            self.len(1, await core.nodes('ou:industry :source -> ou:org'))

            self.len(1, nodes := await core.nodes('[ ou:industry=({"name": "faz"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

    async def test_ou_opening(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:opening=*
                    :org = {[ ou:org=* :name=vertex ]}
                    :org:name = vertex
                    :org:fqdn = vertex.link
                    :posted = 20210807
                    :removed = 2022
                    :postings = {[ inet:url=https://vertex.link ]}
                    :contact = {[ entity:contact=* :email=visi@vertex.link ]}
                    :loc = us.va
                    :job:type = it.dev
                    :employment:type = fulltime.salary
                    :title = PyDev
                    :remote = (1)
                    :yearlypay = 20
                    :paycurrency = BTC
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('org:name'), 'vertex')
            self.eq(nodes[0].get('org:fqdn'), 'vertex.link')
            self.eq(nodes[0].get('title'), 'pydev')
            self.eq(nodes[0].get('remote'), 1)
            self.eq(nodes[0].get('yearlypay'), '20')
            self.eq(nodes[0].get('paycurrency'), 'btc')
            self.eq(nodes[0].get('employment:type'), 'fulltime.salary.')
            self.eq(nodes[0].get('posted'), 1628294400000000)
            self.eq(nodes[0].get('removed'), 1640995200000000)
            self.eq(nodes[0].get('postings'), ('https://vertex.link',))

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ou:opening -> ou:org'))
            self.len(1, await core.nodes('ou:opening -> meta:name'))
            self.len(1, await core.nodes('ou:opening -> inet:url'))
            self.len(1, await core.nodes('ou:opening -> inet:fqdn'))
            self.len(1, await core.nodes('ou:opening -> entity:title'))
            self.len(1, await core.nodes('ou:opening -> ou:employment:type:taxonomy'))
            self.len(1, await core.nodes('ou:opening :contact -> entity:contact'))

    async def test_ou_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:vitals=*
                    :asof = 20210731
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
            self.eq(nodes[0].get('asof'), 1627689600000000)
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
            self.len(1, await core.nodes('ou:vitals -> meta:name'))

            self.len(1, await core.nodes('ou:org [ :vitals=* ] :vitals -> ou:vitals'))

    async def test_ou_conflict(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:conflict=*
                    :name="World War III"
                    :timeline=*
                    :period=2049*
                ]
            ''')

            # FIXME does wild card ival syntax not work yet?
            self.eq(nodes[0].get('period'), (2493072000000000, 2493072000000001))
            self.eq('world war iii', nodes[0].get('name'))
            self.len(1, await core.nodes('ou:conflict -> meta:timeline'))

            nodes = await core.nodes('[ ou:campaign=* :name="good guys" :names=("pacific campaign",) :conflict={ou:conflict} ]')
            self.len(1, await core.nodes('ou:campaign -> ou:conflict'))
            self.len(1, await core.nodes('ou:campaign:names*[="pacific campaign"]'))

            nodes = await core.nodes('''
                [ ou:contribution=*
                    :from={[ ou:org=* :name=vertex ]}
                    :time=20220718
                    :value=10
                    :currency=usd
                    :campaign={ou:campaign:name="good guys"}
                    :monetary:payment=*
                    :material:spec=*
                    :material:count=1
                    :personnel:title=analysts
                    :personnel:count=1
                ]
            ''')
            self.eq(1658102400000000, nodes[0].get('time'))
            self.eq('10', nodes[0].get('value'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq(1, nodes[0].get('material:count'))
            self.eq(1, nodes[0].get('personnel:count'))
            self.len(1, await core.nodes('ou:contribution -> ou:campaign'))
            self.len(1, await core.nodes('ou:contribution -> econ:payment'))
            self.len(1, await core.nodes('ou:contribution -> mat:spec'))
            self.len(1, await core.nodes('ou:contribution -> entity:title +entity:title=analysts'))

    async def test_ou_technique(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:technique=* :name=foo +(uses)> { [ risk:vuln=* :name=bar ] } ]
            ''')
            self.len(1, await core.nodes('ou:technique:name=foo -(uses)> risk:vuln:name=bar'))
