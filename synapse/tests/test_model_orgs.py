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
                    :name=Woot
                    :type=lol.woot
                    :desc=Hehe
                    :tag=woot.woot
                    :mitre:attack:technique=T0001
                    :sophistication=high
                    :reporter=$lib.gen.orgByName(vertex)
                    :reporter:name=vertex
                    :ext:id=Foo
                ]
            ''')
            self.len(1, nodes)
            self.nn('reporter')
            self.eq('woot', nodes[0].get('name'))
            self.eq('Hehe', nodes[0].get('desc'))
            self.eq('lol.woot.', nodes[0].get('type'))
            self.eq('woot.woot', nodes[0].get('tag'))
            self.eq('Foo', nodes[0].get('ext:id'))
            self.eq('T0001', nodes[0].get('mitre:attack:technique'))
            self.eq(40, nodes[0].get('sophistication'))
            self.eq('vertex', nodes[0].get('reporter:name'))
            self.len(1, await core.nodes('ou:technique -> syn:tag'))
            self.len(1, await core.nodes('ou:technique -> ou:technique:taxonomy'))
            self.len(1, await core.nodes('ou:technique -> it:mitre:attack:technique'))
            self.len(1, await core.nodes('ou:technique :reporter -> ou:org'))

            props = {
                'name': 'MyGoal',
                'names': ['Foo Goal', 'Bar Goal', 'Bar Goal'],
                'type': 'foo.bar',
                'desc': 'MyDesc',
                'prev': goal,
            }
            q = '[(ou:goal=$valu :name=$p.name :names=$p.names :type=$p.type :desc=$p.desc :prev=$p.prev)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': goal, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ou:goal', goal))
            self.eq(node.get('name'), 'mygoal')
            self.eq(node.get('names'), ('bar goal', 'foo goal'))
            self.eq(node.get('type'), 'foo.bar.')
            self.eq(node.get('desc'), 'MyDesc')
            self.eq(node.get('prev'), goal)

            self.len(1, nodes := await core.nodes('[ ou:goal=({"name": "foo goal"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            nodes = await core.nodes('[(ou:hasgoal=$valu :stated=$lib.true :window="2019,2020")]',
                                     opts={'vars': {'valu': (org0, goal)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('org'), org0)
            self.eq(node.get('goal'), goal)
            self.eq(node.get('stated'), True)
            self.eq(node.get('window'), (1546300800000, 1577836800000))

            altgoal = s_common.guid()
            timeline = s_common.guid()

            props = {
                'org': org0,
                'goal': goal,
                'goals': (goal, altgoal),
                'actors': (acto,),
                'camptype': 'get.pizza',
                'name': 'MyName',
                'names': ('foo', 'bar', 'Bar'),
                'type': 'MyType',
                'desc': 'MyDesc',
                'success': 1,
                'techniques': teqs,
                'sophistication': 'high',
                'tag': 'cno.camp.31337',
                'reporter': '*',
                'reporter:name': 'vertex',
                'timeline': timeline,
                'mitre:attack:campaign': 'C0011',
            }
            q = '''[(ou:campaign=$valu :org=$p.org :goal=$p.goal :goals=$p.goals :actors=$p.actors
            :camptype=$p.camptype :name=$p.name :names=$p.names :type=$p.type :desc=$p.desc :success=$p.success
            :techniques=$p.techniques :sophistication=$p.sophistication :tag=$p.tag
            :reporter=$p.reporter :reporter:name=$p."reporter:name" :timeline=$p.timeline
            :mitre:attack:campaign=$p."mitre:attack:campaign"
            :ext:id=Foo :slogan="For The People"
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': camp, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('tag'), 'cno.camp.31337')
            self.eq(node.get('org'), org0)
            self.eq(node.get('goal'), goal)
            self.eq(node.get('goals'), sorted((goal, altgoal)))
            self.eq(node.get('actors'), (acto,))
            self.eq(node.get('name'), 'myname')
            self.eq(node.get('names'), ('bar', 'foo'))
            self.eq(node.get('type'), 'MyType')
            self.eq(node.get('desc'), 'MyDesc')
            self.eq(node.get('ext:id'), 'Foo')
            self.eq(node.get('success'), 1)
            self.eq(node.get('sophistication'), 40)
            self.eq(node.get('camptype'), 'get.pizza.')
            self.eq(node.get('techniques'), tuple(sorted(teqs)))
            self.eq(node.get('timeline'), timeline)
            self.nn(node.get('reporter'))
            self.eq(node.get('reporter:name'), 'vertex')
            self.eq(node.get('mitre:attack:campaign'), 'C0011')
            self.eq(node.get('slogan'), 'for the people')

            opts = {'vars': {'altgoal': altgoal}}
            self.len(1, nodes := await core.nodes('[ ou:campaign=({"name": "foo", "goal": $altgoal}) ]', opts=opts))
            self.eq(node.ndef, nodes[0].ndef)

            self.len(1, await core.nodes(f'ou:campaign={camp} :slogan -> lang:phrase'))
            nodes = await core.nodes(f'ou:campaign={camp} -> it:mitre:attack:campaign')
            self.len(1, nodes)
            nodes = nodes[0]
            self.eq(nodes.ndef, ('it:mitre:attack:campaign', 'C0011'))

            # type norming first
            # ou:name
            t = core.model.type('ou:name')
            norm, subs = t.norm('Acme Corp ')
            self.eq(norm, 'acme corp')

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

            # ou:alias
            t = core.model.type('ou:alias')
            self.raises(s_exc.BadTypeValu, t.norm, 'asdf.asdf.asfd')
            self.eq(t.norm('HAHA1')[0], 'haha1')
            self.eq(t.norm('GOV_MFA')[0], 'gov_mfa')

            # ou:org:alias (unicode test)
            nodes = await core.nodes('''
                [ ou:org=* :alias="ÅÆØåæø" ]
            ''')
            self.len(1, nodes)
            self.eq(t.norm('ÅÆØåæø')[0], 'åæøåæø')

            # ou:position / ou:org:subs
            orgiden = s_common.guid()
            contact = s_common.guid()
            position = s_common.guid()
            subpos = s_common.guid()
            suborg = s_common.guid()

            opts = {'vars': {
                'orgiden': orgiden,
                'contact': contact,
                'position': position,
                'subpos': subpos,
                'suborg': suborg,
            }}

            nodes = await core.nodes('''
                [ ou:org=$orgiden :orgchart=$position ]
                -> ou:position
                [ :contact=$contact :title=ceo :org=$orgiden ]
            ''', opts=opts)
            self.eq('ceo', nodes[0].get('title'))
            self.eq(orgiden, nodes[0].get('org'))
            self.eq(contact, nodes[0].get('contact'))

            nodes = await core.nodes('''
                ou:org=$orgiden
                -> ou:position
                [ :reports+=$subpos ]
                -> ou:position
            ''', opts=opts)
            self.eq(('ou:position', subpos), nodes[0].ndef)

            nodes = await core.nodes('''
                ou:org=$orgiden
                [ :subs+=$suborg ]
                -> ou:org
            ''', opts=opts)
            self.eq(('ou:org', suborg), nodes[0].ndef)

            guid0 = s_common.guid()
            name = '\u21f1\u21f2 Inc.'
            normname = '\u21f1\u21f2 inc.'
            altnames = ('altarrowname', 'otheraltarrow',)
            props = {
                'loc': 'US.CA',
                'name': name,
                'type': 'corp',
                'orgtype': 'Corp.Lolz',
                'names': altnames,
                'logo': '*',
                'alias': 'arrow',
                'phone': '+15555555555',
                'sic': '0119',
                'naics': 541715,
                'url': 'http://www.arrowinc.link',
                'us:cage': '7qe71',
                'founded': '2015',
                'dissolved': '2019',
                'techniques': teqs,
                'goals': (goal,),
            }
            q = '''[(ou:org=$valu :loc=$p.loc :name=$p.name :type=$p.type :orgtype=$p.orgtype :names=$p.names
                :logo=$p.logo :alias=$p.alias :phone=$p.phone :sic=$p.sic :naics=$p.naics :url=$p.url
                :us:cage=$p."us:cage" :founded=$p.founded :dissolved=$p.dissolved
                :techniques=$p.techniques :goals=$p.goals
                :ext:id=Foo :motto="DONT BE EVIL"
            )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': guid0, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ou:org', guid0))
            self.eq(node.get('loc'), 'us.ca')
            self.eq(node.get('type'), 'corp')
            self.eq(node.get('orgtype'), 'corp.lolz.')
            self.eq(node.get('name'), normname)
            self.eq(node.get('names'), altnames)
            self.eq(node.get('alias'), 'arrow')
            self.eq(node.get('phone'), '15555555555')
            self.eq(node.get('sic'), '0119')
            self.eq(node.get('naics'), '541715')
            self.eq(node.get('url'), 'http://www.arrowinc.link')
            self.eq(node.get('us:cage'), '7qe71')
            self.eq(node.get('founded'), 1420070400000)
            self.eq(node.get('dissolved'), 1546300800000)
            self.eq(node.get('techniques'), tuple(sorted(teqs)))
            self.eq(node.get('goals'), (goal,))
            self.eq(node.get('ext:id'), 'Foo')
            self.nn(node.get('logo'))
            self.eq('dont be evil', node.get('motto'))

            await core.nodes('ou:org:us:cage=7qe71 [ :country={ gen.pol.country ua } :country:code=ua ]')
            self.len(1, await core.nodes('ou:org:country:code=ua'))
            self.len(1, await core.nodes('pol:country:iso2=ua -> ou:org'))
            self.len(1, await core.nodes('ou:org -> ou:orgtype'))
            self.len(1, await core.nodes('ou:org :motto -> lang:phrase'))

            nodes = await core.nodes('ou:name')
            self.sorteq([x.ndef[1] for x in nodes], (normname, 'vertex') + altnames)

            nodes = await core.nodes('ou:org:names*[=otheraltarrow]')
            self.len(1, nodes)

            opts = {'vars': {'name': name}}
            nodes = await core.nodes('ou:org:names*[=$name]', opts=opts)
            self.len(0, nodes)  # primary ou:org:name is not in ou:org:names

            person0 = s_common.guid()
            nodes = await core.nodes('[(ou:member=$valu :title="Dancing Clown" :start=2001 :end=2010)]',
                                     opts={'vars': {'valu': (guid0, person0)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ou:member', (guid0, person0)))
            self.eq(node.get('title'), 'dancing clown')
            self.eq(node.get('start'), 978307200000)
            self.eq(node.get('end'), 1262304000000)

            guid1 = s_common.guid()
            nodes = await core.nodes('[(ou:suborg=$valu :perc=50 :current=$lib.true)]',
                                     opts={'vars': {'valu': (guid0, guid1)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, guid1))
            self.eq(node.get('perc'), 50)
            self.eq(node.get('current'), 1)
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:suborg=$valu [:perc="-1"]', opts={'vars': {'valu': (guid0, guid1)}})
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('ou:suborg=$valu [:perc=101]', opts={'vars': {'valu': (guid0, guid1)}})

            nodes = await core.nodes('[ou:user=$valu]', opts={'vars': {'valu': (guid0, 'arrowman')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, 'arrowman'))
            self.eq(node.get('org'), guid0)
            self.eq(node.get('user'), 'arrowman')

            nodes = await core.nodes('[ou:hasalias=$valu]', opts={'vars': {'valu': (guid0, 'EVILCORP')}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, 'evilcorp'))
            self.eq(node.get('alias'), 'evilcorp')
            self.eq(node.get('org'), guid0)

            nodes = await core.nodes('[ou:orgnet4=$valu]',
                                     opts={'vars': {'valu': (guid0, ('192.168.1.1', '192.168.1.127'))}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, (3232235777, 3232235903)))
            self.eq(node.get('net'), (3232235777, 3232235903))
            self.eq(node.get('org'), guid0)

            nodes = await core.nodes('[ou:orgnet6=$valu]',
                                     opts={'vars': {'valu': (guid0, ('fd00::1', 'fd00::127'))}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, ('fd00::1', 'fd00::127')))
            self.eq(node.get('net'), ('fd00::1', 'fd00::127'))
            self.eq(node.get('org'), guid0)

            nodes = await core.nodes('[ou:org:has=$valu]',
                                     opts={'vars': {'valu': (guid0, ('test:str', 'pretty floral bonnet'))}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (guid0, ('test:str', 'pretty floral bonnet')))
            self.eq(node.get('org'), guid0)
            self.eq(node.get('node'), ('test:str', 'pretty floral bonnet'))
            self.eq(node.get('node:form'), 'test:str')

            # ou:meet
            place0 = s_common.guid()
            m0 = s_common.guid()
            props = {
                'name': 'Working Lunch',
                'start': '201604011200',
                'end': '201604011300',
                'place': place0,
            }
            q = '[(ou:meet=$valu :name=$p.name :start=$p.start :end=$p.end :place=$p.place)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': m0, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], m0)
            self.eq(node.get('name'), 'working lunch')
            self.eq(node.get('start'), 1459512000000)
            self.eq(node.get('end'), 1459515600000)
            self.eq(node.get('place'), place0)

            props = {
                'arrived': '201604011201',
                'departed': '201604011259',
            }
            q = '[(ou:meet:attendee=$valu :arrived=$p.arrived :departed=$p.departed)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': (m0, person0), 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (m0, person0))
            self.eq(node.get('arrived'), 1459512060000)
            self.eq(node.get('departed'), 1459515540000)

            # ou:conference
            c0 = s_common.guid()
            props = {
                'org': guid0,
                'name': 'arrowcon 2018',
                'names': ('Arrow Conference 2018', 'ArrCon18', 'ArrCon18'),
                'base': 'arrowcon',
                'start': '20180301',
                'end': '20180303',
                'place': place0,
                'url': 'http://arrowcon.org/2018',
            }
            q = '''[
                ou:conference=$valu
                    :org=$p.org :name=$p.name :names=$p.names
                    :base=$p.base :start=$p.start :end=$p.end
                    :place=$p.place :url=$p.url
            ]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': c0, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], c0)
            self.eq(node.get('name'), 'arrowcon 2018')
            self.eq(node.get('names'), ('arrcon18', 'arrow conference 2018',))
            self.eq(node.get('base'), 'arrowcon')
            self.eq(node.get('org'), guid0)
            self.eq(node.get('start'), 1519862400000)
            self.eq(node.get('end'), 1520035200000)
            self.eq(node.get('place'), place0)
            self.eq(node.get('url'), 'http://arrowcon.org/2018')

            self.len(1, nodes := await core.nodes('[ ou:conference=({"name": "arrcon18"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            props = {
                'arrived': '201803010800',
                'departed': '201803021500',
                'role:staff': False,
                'role:speaker': True,
                'roles': ['usher', 'coatcheck'],
            }
            q = '''[(ou:conference:attendee=$valu :arrived=$p.arrived :departed=$p.departed
                :role:staff=$p."role:staff" :role:speaker=$p."role:speaker" :roles=$p.roles)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': (c0, person0), 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (c0, person0))
            self.eq(node.get('arrived'), 1519891200000)
            self.eq(node.get('departed'), 1520002800000)
            self.eq(node.get('role:staff'), 0)
            self.eq(node.get('role:speaker'), 1)
            self.eq(node.get('roles'), ('coatcheck', 'usher'))
            # ou:conference:event
            confguid = c0
            con0 = s_common.guid()
            c0 = s_common.guid()
            props = {
                'conference': confguid,
                'name': 'arrowcon 2018 dinner',
                'desc': 'arrowcon dinner',
                'start': '201803011900',
                'end': '201803012200',
                'contact': con0,
                'place': place0,
                'url': 'http://arrowcon.org/2018/dinner',
            }
            q = '''[(ou:conference:event=$valu :name=$p.name :desc=$p.desc :start=$p.start :end=$p.end
                    :conference=$p.conference :contact=$p.contact :place=$p.place :url=$p.url)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': c0, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], c0)
            self.eq(node.get('name'), 'arrowcon 2018 dinner')
            self.eq(node.get('desc'), 'arrowcon dinner')
            self.eq(node.get('conference'), confguid)
            self.eq(node.get('start'), 1519930800000)
            self.eq(node.get('end'), 1519941600000)
            self.eq(node.get('contact'), con0)
            self.eq(node.get('place'), place0)
            self.eq(node.get('url'), 'http://arrowcon.org/2018/dinner')

            props = {
                'arrived': '201803011923',
                'departed': '201803012300',
                'roles': ['staff', 'speaker'],
            }
            q = '[(ou:conference:event:attendee=$valu :arrived=$p.arrived :departed=$p.departed :roles=$p.roles)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': (c0, person0), 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (c0, person0))
            self.eq(node.get('arrived'), 1519932180000)
            self.eq(node.get('departed'), 1519945200000)
            self.eq(node.get('roles'), ('speaker', 'staff'))

            nodes = await core.nodes('[ ou:id:type=* :org=* :name=foobar :names=(alt1,alt2) :url="http://foobar.com/ids"]')
            self.len(1, nodes)
            self.nn(nodes[0].get('org'))
            self.eq('foobar', nodes[0].get('name'))
            self.eq(('alt1', 'alt2'), nodes[0].get('names'))
            self.eq('http://foobar.com/ids', nodes[0].get('url'))

            iden = await core.callStorm('ou:id:type return($node.value())')

            self.len(1, alts := await core.nodes('[ ou:id:type=({"name": "foobar"}) ]'))
            self.eq(nodes[0].ndef, alts[0].ndef)

            self.len(1, alts := await core.nodes('[ ou:id:type=({"name": "alt1"}) ]'))
            self.eq(nodes[0].ndef, alts[0].ndef)

            opts = {'vars': {'type': iden}}
            nodes = await core.nodes('''
                [ ou:id:number=($type, visi)
                    :status=woot
                    :issued=202002
                    :expires=2021
                    :issuer={[ ps:contact=* :name=visi ]}
                ]
            ''', opts=opts)
            self.len(1, nodes)
            self.nn(nodes[0].get('issuer'))
            self.eq(('ou:id:number', (iden, 'visi')), nodes[0].ndef)
            self.eq(iden, nodes[0].get('type'))
            self.eq('visi', nodes[0].get('value'))
            self.eq('woot', nodes[0].get('status'))
            self.eq(1580515200000, nodes[0].get('issued'))
            self.eq(1609459200000, nodes[0].get('expires'))
            self.len(1, await core.nodes('ou:id:number -> ps:contact +:name=visi'))

            opts = {'vars': {'type': iden}}
            nodes = await core.nodes('[ ou:id:update=* :number=($type, visi) :status=revoked :time=202003]', opts=opts)
            self.len(1, nodes)
            self.eq((iden, 'visi'), nodes[0].get('number'))
            self.eq('revoked', nodes[0].get('status'))
            self.eq(1583020800000, nodes[0].get('time'))

            nodes = await core.nodes('[ ou:org=* :desc=hehe :hq=* :locations=(*, *) :dns:mx=(hehe.com, haha.com)]')
            self.len(1, nodes)
            self.eq('hehe', nodes[0].get('desc'))

            opts = {'vars': {'iden': nodes[0].ndef[1]}}
            self.len(3, await core.nodes('ou:org=$iden -> ps:contact', opts=opts))
            self.len(1, await core.nodes('ou:org=$iden :hq -> ps:contact', opts=opts))
            self.len(2, await core.nodes('ou:org=$iden :locations -> ps:contact', opts=opts))
            self.len(2, await core.nodes('ou:org=$iden :dns:mx -> inet:fqdn', opts=opts))

            nodes = await core.nodes('''[
                ou:attendee=*
                    :person=*
                    :arrived=201202
                    :departed=201203
                    :meet=*
                    :preso=*
                    :conference=*
                    :conference:event=*
                    :roles+=staff
                    :roles+=STAFF
            ]''')
            self.len(1, nodes)
            self.eq(('staff',), nodes[0].get('roles'))
            self.eq(1328054400000, nodes[0].get('arrived'))
            self.eq(1330560000000, nodes[0].get('departed'))

            self.len(1, await core.nodes('ou:attendee -> ps:contact'))

            self.len(1, await core.nodes('ou:attendee -> ou:meet'))
            self.len(1, await core.nodes('ou:attendee -> ou:preso'))
            self.len(1, await core.nodes('ou:attendee -> ou:conference'))
            self.len(1, await core.nodes('ou:attendee -> ou:conference:event'))

            pres = s_common.guid()
            nodes = await core.nodes(f'''[
                ou:preso={pres}
                    :title=syn101
                    :desc=squeee
                    :time=20200808
                    :duration=2:00:00

                    :place=*
                    :loc=us.nv.lasvegas

                    :conference=*
                    :organizer=*
                    :sponsors=(*,)
                    :presenters=(*,*)

                    :deck:file=*
                    :recording:file=*

                    :deck:url=http://vertex.link/syn101deck
                    :attendee:url=http://vertex.link/syn101live
                    :recording:url=http://vertex.link/syn101recording
            ]''')
            self.len(1, nodes)
            self.eq('syn101', nodes[0].get('title'))
            self.eq('squeee', nodes[0].get('desc'))

            self.eq(1596844800000, nodes[0].get('time'))
            self.eq(7200000, nodes[0].get('duration'))

            self.eq('http://vertex.link/syn101deck', nodes[0].get('deck:url'))
            self.eq('http://vertex.link/syn101live', nodes[0].get('attendee:url'))
            self.eq('http://vertex.link/syn101recording', nodes[0].get('recording:url'))

            self.nn(nodes[0].get('deck:file'))
            self.nn(nodes[0].get('recording:file'))

            self.eq('us.nv.lasvegas', nodes[0].get('loc'))

            self.len(1, await core.nodes(f'ou:preso={pres} -> ou:conference'))
            self.len(1, await core.nodes(f'ou:preso={pres} :sponsors -> ps:contact'))
            self.len(1, await core.nodes(f'ou:preso={pres} :organizer -> ps:contact'))
            self.len(2, await core.nodes(f'ou:preso={pres} :presenters -> ps:contact'))

            cont = s_common.guid()
            nodes = await core.nodes(f'''[
                ou:contest={cont}
                    :name="defcon ctf 2020"
                    :type="cyber ctf"
                    :family="defcon ctf"
                    :start=20200808
                    :end=20200811
                    :url=http://vertex.link/contest

                    :loc=us.nv.lasvegas
                    :place=*
                    :latlong=(20, 30)

                    :conference=*
                    :contests=(*,*)
                    :sponsors=(*,)
                    :organizers=(*,)
                    :participants=(*,)

            ]''')
            self.len(1, nodes)
            self.eq('defcon ctf 2020', nodes[0].get('name'))
            self.eq('cyber ctf', nodes[0].get('type'))
            self.eq('defcon ctf', nodes[0].get('family'))

            self.eq(1596844800000, nodes[0].get('start'))
            self.eq(1597104000000, nodes[0].get('end'))

            self.eq('http://vertex.link/contest', nodes[0].get('url'))

            self.eq((20, 30), nodes[0].get('latlong'))
            self.eq('us.nv.lasvegas', nodes[0].get('loc'))

            self.len(2, await core.nodes(f'ou:contest={cont} -> ou:contest'))
            self.len(1, await core.nodes(f'ou:contest={cont} -> ou:conference'))
            self.len(1, await core.nodes(f'ou:contest={cont} :sponsors -> ps:contact'))
            self.len(1, await core.nodes(f'ou:contest={cont} :organizers -> ps:contact'))
            self.len(1, await core.nodes(f'ou:contest={cont} :participants -> ps:contact'))

            nodes = await core.nodes('''[
                ou:contest:result=(*, *)
                    :rank=1
                    :score=20
                    :period=(20250101, 20250102)
                    :url=http://vertex.link/contest/result
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('contest'))
            self.nn(nodes[0].get('participant'))
            self.eq(1, nodes[0].get('rank'))
            self.eq(20, nodes[0].get('score'))
            self.eq((1735689600000, 1735776000000), nodes[0].get('period'))
            self.eq('http://vertex.link/contest/result', nodes[0].get('url'))
            self.len(1, await core.nodes('ou:contest:result -> ps:contact'))
            self.len(1, await core.nodes('ou:contest:result -> ou:contest'))

            opts = {'vars': {'ind': s_common.guid()}}
            nodes = await core.nodes('[ ou:org=* :industries=($ind, $ind) ]', opts=opts)
            self.len(1, nodes)
            self.len(1, nodes[0].get('industries'))

            nodes = await core.nodes('''[ ou:requirement=50b757fafe4a839ec499023ebcffe7c0
                :name="acquire pizza toppings"
                :type=foo.bar
                :text="The team must acquire ANSI standard pizza toppings."
                :goal={[ ou:goal=* :name=pizza ]}
                :issuer={[ ps:contact=* :name=visi ]}
                :assignee={ gen.ou.org.hq ledos }
                :optional=(true)
                :priority=highest
                :issued=20120202
                :period=(2023, ?)
                :active=(true)
                :deps=(*, *)
                :deps:min=1
            ]''')
            self.len(1, nodes)
            self.eq('acquire pizza toppings', nodes[0].get('name'))
            self.eq('The team must acquire ANSI standard pizza toppings.', nodes[0].get('text'))
            self.eq(1, nodes[0].get('deps:min'))
            self.eq(50, nodes[0].get('priority'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq(True, nodes[0].get('optional'))
            self.eq(1328140800000, nodes[0].get('issued'))
            self.eq((1672531200000, 9223372036854775807), nodes[0].get('period'))

            self.len(2, await core.nodes('ou:requirement=50b757fafe4a839ec499023ebcffe7c0 -> ou:requirement'))
            self.len(1, await core.nodes('ou:requirement=50b757fafe4a839ec499023ebcffe7c0 -> ou:goal +:name=pizza'))
            self.len(1, await core.nodes('ou:requirement=50b757fafe4a839ec499023ebcffe7c0 :issuer -> ps:contact +:name=visi'))
            self.len(1, await core.nodes('ou:requirement=50b757fafe4a839ec499023ebcffe7c0 :assignee -> ps:contact +:orgname=ledos'))
            self.len(1, await core.nodes('ou:requirement=50b757fafe4a839ec499023ebcffe7c0 -> ou:requirement:type:taxonomy'))

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
                    :owner={[ ps:contact=* :name=foo ]}
                    :operator={[ ps:contact=* :name=bar ]}
                ]''')
            self.len(1, nodes)
            self.eq((1451606400000, 9223372036854775807), nodes[0].get('period'))
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
            self.len(1, await core.nodes('ou:asset :owner -> ps:contact +:name=foo '))
            self.len(1, await core.nodes('ou:asset :operator -> ps:contact +:name=bar '))

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
                    :ext:creator={[ ps:contact=* :name=root ]}
                    :ext:assignee={[ ps:contact=* :name=visi ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq('V-99', nodes[0].get('id'))
            self.eq(10, nodes[0].get('status'))
            self.eq(50, nodes[0].get('priority'))

            self.eq(1729209600000, nodes[0].get('due'))
            self.eq(1729209600000, nodes[0].get('created'))
            self.eq(1729209600000, nodes[0].get('updated'))
            self.eq(1729209600000, nodes[0].get('completed'))

            self.eq(visi.iden, nodes[0].get('assignee'))
            self.eq(core.auth.rootuser.iden, nodes[0].get('creator'))

            self.nn(nodes[0].get('scope'))
            self.nn(nodes[0].get('ext:creator'))
            self.nn(nodes[0].get('ext:assignee'))

            self.len(1, await core.nodes('ou:enacted -> proj:project'))
            self.len(1, await core.nodes('ou:enacted :scope -> ou:team'))
            self.len(1, await core.nodes('ou:enacted :ext:creator -> ps:contact +:name=root'))
            self.len(1, await core.nodes('ou:enacted :ext:assignee -> ps:contact +:name=visi'))

            nodes = await core.nodes('''
                [ ou:candidate=*
                    :org={ ou:org:name=vertex | limit 1 }
                    :contact={ ps:contact:name=visi | limit 1 }
                    :intro="    Hi there!"
                    :submitted=20241104
                    :method=referral.employee
                    :resume=*
                    :opening=*
                    :agent={[ ps:contact=* :name=agent ]}
                    :recruiter={[ ps:contact=* :name=recruiter ]}
                    :attachments={[ file:attachment=* :name=questions.pdf ]}
                ]
            ''')
            self.len(1, nodes)
            self.eq('Hi there!', nodes[0].get('intro'))
            self.eq(1730678400000, nodes[0].get('submitted'))
            self.eq('referral.employee.', nodes[0].get('method'))
            self.len(1, await core.nodes('ou:candidate :org -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('ou:candidate :agent -> ps:contact +:name=agent'))
            self.len(1, await core.nodes('ou:candidate :contact -> ps:contact +:name=visi'))
            self.len(1, await core.nodes('ou:candidate :recruiter -> ps:contact +:name=recruiter'))

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
                nodes = await core.nodes('[ou:org=$valu :naics=$p.naics :sic=$p.sic]',
                                         opts={'vars': {'valu': g, 'p': props}})
                self.len(1, nodes)
            self.len(3, await core.nodes('ou:org:sic^=01'))
            self.len(2, await core.nodes('ou:org:sic^=011'))
            self.len(4, await core.nodes('ou:org:naics^=22'))
            self.len(4, await core.nodes('ou:org:naics^=221'))
            self.len(3, await core.nodes('ou:org:naics^=2211'))
            self.len(2, await core.nodes('ou:org:naics^=22112'))

    async def test_ou_contract(self):

        async with self.getTestCore() as core:
            iden0 = await core.callStorm('[ ps:contact=* ] return($node.value())')
            iden1 = await core.callStorm('[ ps:contact=* ] return($node.value())')
            iden2 = await core.callStorm('[ ps:contact=* ] return($node.value())')

            goal0 = await core.callStorm('[ ou:goal=* :name="world peace"] return($node.value())')
            goal1 = await core.callStorm('[ ou:goal=* :name="whirled peas"] return($node.value())')

            file0 = await core.callStorm('[ file:bytes=* ] return($node.value())')

            nodes = await core.nodes(f'''
            [ ou:contract=*
                :title="Fullbright Scholarship"
                :type=foo.bar
                :types="nda,grant"
                :sponsor={iden0}
                :currency=USD
                :award:price=20.00
                :budget:price=21.50
                :parties=({iden1}, {iden2})
                :document={file0}
                :signed=202001
                :begins=202002
                :expires=202003
                :completed=202004
                :terminated=202005
                :requirements=({goal0},{goal1})
            ]''')
            self.len(1, nodes)
            self.eq('Fullbright Scholarship', nodes[0].get('title'))
            self.eq(iden0, nodes[0].get('sponsor'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('20', nodes[0].get('award:price'))
            self.eq('21.5', nodes[0].get('budget:price'))
            self.eq('foo.bar.', nodes[0].get('type'))
            self.eq(1577836800000, nodes[0].get('signed'))
            self.eq(1580515200000, nodes[0].get('begins'))
            self.eq(1583020800000, nodes[0].get('expires'))
            self.eq(1585699200000, nodes[0].get('completed'))
            self.eq(1588291200000, nodes[0].get('terminated'))
            self.sorteq(('grant', 'nda'), nodes[0].get('types'))
            self.sorteq((iden1, iden2), nodes[0].get('parties'))
            self.sorteq((goal0, goal1), nodes[0].get('requirements'))

            nodes = await core.nodes('ou:contract -> ou:conttype')
            self.len(1, nodes)
            self.eq(1, nodes[0].get('depth'))
            self.eq('bar', nodes[0].get('base'))
            self.eq('foo.', nodes[0].get('parent'))

            nodes = await core.nodes('ou:conttype')
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
                :subs=(*, *)
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
            self.len(2, nodes[0].get('subs'))
            self.eq('Moldy cheese', nodes[0].get('desc'))

            self.len(1, await core.nodes('ou:industry :reporter -> ou:org'))
            nodes = await core.nodes('ou:industry:name="foo bar" | tree { :subs -> ou:industry } | uniq')
            self.len(3, nodes)
            self.len(3, await core.nodes('ou:industryname=baz -> ou:industry -> ou:industryname'))

            self.len(1, nodes := await core.nodes('[ ou:industry=({"name": "faz"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

    async def test_ou_opening(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:opening=*
                    :org = {[ ou:org=* :name=vertex ]}
                    :orgname = vertex
                    :orgfqdn = vertex.link
                    :posted = 20210807
                    :removed = 2022
                    :postings = {[ inet:url=https://vertex.link ]}
                    :contact = {[ ps:contact=* :email=visi@vertex.link ]}
                    :loc = us.va
                    :jobtype = it.dev
                    :employment = fulltime.salary
                    :jobtitle = PyDev
                    :remote = (1)
                    :yearlypay = 20
                    :paycurrency = BTC
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('orgname'), 'vertex')
            self.eq(nodes[0].get('orgfqdn'), 'vertex.link')
            self.eq(nodes[0].get('jobtitle'), 'pydev')
            self.eq(nodes[0].get('remote'), 1)
            self.eq(nodes[0].get('yearlypay'), '20')
            self.eq(nodes[0].get('paycurrency'), 'btc')
            self.eq(nodes[0].get('employment'), 'fulltime.salary.')
            self.eq(nodes[0].get('posted'), 1628294400000)
            self.eq(nodes[0].get('removed'), 1640995200000)
            self.eq(nodes[0].get('postings'), ('https://vertex.link',))

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ou:opening -> ou:org'))
            self.len(1, await core.nodes('ou:opening -> ou:name'))
            self.len(1, await core.nodes('ou:opening -> inet:url'))
            self.len(1, await core.nodes('ou:opening -> inet:fqdn'))
            self.len(1, await core.nodes('ou:opening -> ou:jobtitle'))
            self.len(1, await core.nodes('ou:opening -> ou:employment'))
            self.len(1, await core.nodes('ou:opening :contact -> ps:contact'))

    async def test_ou_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:vitals=*
                    :asof = 20210731
                    :org = *
                    :orgname = WootCorp
                    :orgfqdn = wootwoot.com
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
            self.eq(nodes[0].get('asof'), 1627689600000)
            self.eq(nodes[0].get('orgname'), 'wootcorp')
            self.eq(nodes[0].get('orgfqdn'), 'wootwoot.com')
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
            self.len(1, await core.nodes('ou:vitals -> ou:name'))
            self.len(1, await core.nodes('ou:vitals -> inet:fqdn'))

            self.len(1, await core.nodes('ou:org [ :vitals=* ] :vitals -> ou:vitals'))

    async def test_ou_conflict(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:conflict=*
                    :name="World War III"
                    :timeline=*
                    :started=2049
                    :ended=2050
                ]
            ''')

            self.eq(2493072000000, nodes[0].get('started'))
            self.eq(2524608000000, nodes[0].get('ended'))
            self.eq('World War III', nodes[0].get('name'))
            self.len(1, await core.nodes('ou:conflict -> meta:timeline'))

            nodes = await core.nodes('[ ou:campaign=* :name="good guys" :names=("pacific campaign",) :conflict={ou:conflict} ]')
            self.len(1, await core.nodes('ou:campaign -> ou:conflict'))
            self.len(1, await core.nodes('ou:campaign:names*[="pacific campaign"]'))

            nodes = await core.nodes('''
                [ ou:contribution=*
                    :from={[ps:contact=* :orgname=vertex ]}
                    :time=20220718
                    :value=10
                    :currency=usd
                    :campaign={ou:campaign:name="good guys"}
                    :monetary:payment=*
                    :material:spec=*
                    :material:count=1
                    :personnel:jobtitle=analysts
                    :personnel:count=1
                ]
            ''')
            self.eq(1658102400000, nodes[0].get('time'))
            self.eq('10', nodes[0].get('value'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq(1, nodes[0].get('material:count'))
            self.eq(1, nodes[0].get('personnel:count'))
            self.len(1, await core.nodes('ou:contribution -> ou:campaign'))
            self.len(1, await core.nodes('ou:contribution -> econ:acct:payment'))
            self.len(1, await core.nodes('ou:contribution -> mat:spec'))
            self.len(1, await core.nodes('ou:contribution -> ou:jobtitle +ou:jobtitle=analysts'))

    async def test_ou_technique(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ou:technique=* :name=foo +(uses)> { [ risk:vuln=* :name=bar ] } ]
            ''')
            self.len(1, await core.nodes('ou:technique:name=foo -(uses)> risk:vuln:name=bar'))
